from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from mr_tracker.models import User, Merchant, MerchantTask

class Command(BaseCommand):
    help = 'Send daily summary email to admin users at 7:30 PM'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        admin_users = User.objects.filter(role='admin', user_status='active')
        support_users = User.objects.filter(role='support', user_status='active')

        summary_sections = ""
        for support_user in support_users:
            # Only merchants not completed
            merchants = support_user.assigned_merchants.exclude(m_status='completed')
            if not merchants.exists():
                continue

            # Only merchants with at least one task
            merchants_with_tasks = []
            for merchant in merchants:
                if merchant.tasks.exists():
                    merchants_with_tasks.append(merchant)
            if not merchants_with_tasks:
                continue

            summary_sections += f"""
            <div style="margin-bottom: 20px;">
            <h4 style="text-align:center;">
                Support User: {support_user.user_email}
            </h4>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse; width:100%;">
                <tr>
                    <th>Merchant</th>
                    <th>Task</th>
                    <th>Status</th>
                    <th>Due Date</th>
                    <th>On Time?</th>
                </tr>
            """
            for merchant in merchants_with_tasks:
                tasks = merchant.tasks.all()
                for task in tasks:
                    due_date = task.due_date.strftime('%Y-%m-%d') if task.due_date else ''
                    on_time = ""
                    if task.end_date and task.due_date:
                        on_time = "Yes" if task.end_date <= task.due_date else "No"
                    elif task.status == 'completed':
                        on_time = "N/A"
                    summary_sections += f"""
                    <tr>
                        <td>{merchant.m_name}</td>
                        <td>{task.custom_task_name}</td>
                        <td>{task.status.replace('_', ' ').title()}</td>
                        <td>{due_date}</td>
                        <td>{on_time}</td>
                    </tr>
                    """
            summary_sections += "</table></div>"

        if not summary_sections:
            self.stdout.write(self.style.WARNING("No merchants with tasks to summarize. No email sent."))
            return

        subject = "Daily Summary of Merchants and Tasks"
        for admin in admin_users:
            message = f"""
            <html>
            <body>
            <p>Hi {admin.user_name},</p>
            <p>This is your daily summary of merchants and tasks assigned to support users.<br>
            Please find the details below:</p>
            {summary_sections}
            <p>Thanks & Regards.</p>
            </body>
            </html>
            """
            send_mail(
                subject,
                "",
                settings.DEFAULT_FROM_EMAIL,
                [admin.user_email],
                html_message=message,
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"Summary email sent to {admin.user_email}"))