from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from mr_tracker.models import User, MerchantTask

class Command(BaseCommand):
    help = 'Send summary email to support users (10 AM and 4 PM)'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        support_users = User.objects.filter(role='support', user_status='active')
        print(f"Found {support_users.count()} support users")
        for user in support_users:
            merchants = user.assigned_merchants.exclude(m_status='completed')
            print(f"User: {user.user_email}, Merchants: {merchants.count()}")
            if not merchants.exists():
                continue
            tasks = MerchantTask.objects.filter(
                merchant__in=merchants
            ).select_related('merchant', 'category')
            print(f"User: {user.user_email}, Tasks: {tasks.count()}")
            if not tasks.exists():
                continue

            # Build merchant-task summary table
            merchant_tables = ""
            for merchant in merchants:
                merchant_tasks = tasks.filter(merchant=merchant)
                if not merchant_tasks.exists():
                    continue

                # Count tasks by status
                completed_count = merchant_tasks.filter(status='completed').count()
                pending_count = merchant_tasks.filter(status='pending').count()
                on_hold_count = merchant_tasks.filter(status='on_hold').count()
                in_progress_count = merchant_tasks.filter(status='in_progress').count()

                merchant_tables += f"""
                <h4>
                    Merchant: {merchant.m_name}
                    <span style="font-size: 13px; font-weight: normal;">
                        (Completed: {completed_count} | Pending: {pending_count} | On Hold: {on_hold_count} | In Progress: {in_progress_count})
                    </span>
                </h4>
                <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;">
                    <tr>
                        <th>Task</th>
                        <th>Status</th>
                        <th>Due Date</th>
                        <th>Ontime?</th>
                    </tr>
                """
                for task in merchant_tasks:
                    due_date = task.due_date.strftime('%Y-%m-%d') if task.due_date else ''
                    ontime = ""
                    if task.end_date and task.due_date:
                        ontime = "Yes" if task.end_date <= task.due_date else "No"
                    elif task.status == 'completed':
                        ontime = "N/A"
                    merchant_tables += f"""
                    <tr>
                        <td>
                            {task.custom_task_name}
                            <br>
                            <small>{task.category.cat_name if task.category else ''}</small>
                        </td>
                        <td>{task.status.replace('_', ' ').title()}</td>
                        <td>{due_date}</td>
                        <td>{ontime}</td>
                    </tr>
                    """
                merchant_tables += "</table><br>"

            subject = "Summary email to check merchant progress"
            message = f"""
            <html>
            <body>
            <p>Hi {user.user_name},</p>
            <p>You have merchants and their assigned tasks. Details are as below:</p>
            {merchant_tables}
            <p>Thanks,<br>Onboarding Team</p>
            </body>
            </html>
            """
            send_mail(
                subject,
                "",
                settings.DEFAULT_FROM_EMAIL,
                [user.user_email],
                html_message=message,
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"Sent summary email to {user.user_email}"))