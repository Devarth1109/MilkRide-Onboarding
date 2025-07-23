from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from mr_tracker.models import User, MerchantTask

class Command(BaseCommand):
    help = 'Send daily overdue task alerts to support users'

    def handle(self, *args, **kwargs):
        print("Command started")
        today = timezone.now().date()
        support_users = User.objects.filter(role='support', user_status='active')
        print(f"Found {support_users.count()} support users")
        for user in support_users:
            overdue_tasks = MerchantTask.objects.filter(
                user=user,
                status__in=['pending', 'in_progress', 'on_hold'],
                due_date__lt=today
            ).select_related('merchant', 'category')
            print(f"User: {user.user_name}, Tasks: {overdue_tasks.count()}")
            if overdue_tasks.exists():
                # Group tasks by merchant
                merchant_map = {}
                for task in overdue_tasks:
                    merchant = task.merchant
                    if merchant not in merchant_map:
                        merchant_map[merchant] = []
                    days_overdue = (today - task.due_date).days if task.due_date else ''
                    merchant_map[merchant].append({
                        "task_name": task.custom_task_name,
                        "category": task.category.cat_name if task.category else '',
                        "start_date": task.start_date.strftime('%Y-%m-%d') if task.start_date else '',
                        "due_date": task.due_date.strftime('%Y-%m-%d') if task.due_date else '',
                        "overdue_by": days_overdue,
                    })
                # Compose HTML email
                merchant_tables = ""
                for merchant, tasks in merchant_map.items():
                    merchant_tables += f"""
                    <h4>Merchant: {merchant.m_name}</h4>
                    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;">
                        <tr>
                            <th>Task Name</th>
                            <th>Due Date</th>
                            <th>Overdue By (Days)</th>
                        </tr>
                    """
                    for t in tasks:
                        merchant_tables += f"""
                        <tr>
                            <td>
                                {t['task_name']}
                                <br>
                                <small>{t['category']}</small>
                            </td>
                            <td>{t['due_date']}</td>
                            <td>{t['overdue_by']}</td>
                        </tr>
                        """
                    merchant_tables += "</table><br>"

                subject = "⚠️ Urgent: Overdue Tasks Require Your Attention"
                message = f"""
                <html>
                <body>
                <p>Hi {user.user_name},</p>
                <p>You have overdue tasks across the following merchants:</p>
                {merchant_tables}
                <p>Please address these as soon as possible to avoid delays.</p>
                <p>Regards,<br>Onboarding Team</p>
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
                self.stdout.write(self.style.SUCCESS(f"Sent overdue alert to {user.user_email}"))