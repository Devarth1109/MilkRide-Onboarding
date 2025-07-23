from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from mr_tracker.models import User, MerchantTask

def get_progress_badge(task, today):
    # Returns HTML badge for progress color with task name inside
    if not task.start_date or not task.due_date:
        return f'<span style="background:gray;color:white;padding:2px 8px;border-radius:8px;">{task.custom_task_name} (No Dates)</span>'
    total_days = (task.due_date - task.start_date).days
    if total_days <= 0:
        return f'<span style="background:gray;color:white;padding:2px 8px;border-radius:8px;">{task.custom_task_name} (Invalid Dates)</span>'
    elapsed_days = (today - task.start_date).days
    percent = max(0, min(100, int((elapsed_days / total_days) * 100)))
    if percent <= 25:
        color = "#28a745"  # Green
    elif percent <= 50:
        color = "#ffc107"  # Yellow
    elif percent <= 75:
        color = "#fd7e14"  # Orange
    else:
        color = "#dc3545"  # Red
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:8px;">{task.custom_task_name}</span>'

class Command(BaseCommand):
    help = 'Send daily task reminders to support users (10 AM and 4 PM)'

    def handle(self, *args, **kwargs):
        print("Command started")  # Debug
        today = timezone.now().date()
        support_users = User.objects.filter(role='support', user_status='active')
        print(f"Found {support_users.count()} support users")  # Debug
        for user in support_users:
            tasks = MerchantTask.objects.filter(
                user=user,
                status__in=['pending', 'in_progress', 'on_hold'],
                due_date__gte=today
            ).select_related('merchant', 'category')
            print(f"User: {user.user_name}, Tasks: {tasks.count()}")  # Debug
            if tasks.exists():
                # Group tasks by merchant
                merchant_map = {}
                for task in tasks:
                    merchant = task.merchant
                    if merchant not in merchant_map:
                        merchant_map[merchant] = []
                    merchant_map[merchant].append(task)
                # Compose HTML email
                merchant_tables = ""
                for merchant, tasks_list in merchant_map.items():
                    merchant_tables += f"""
                    <h4>Merchant: {merchant.m_name}</h4>
                    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;">
                        <tr>
                            <th>Task Name</th>
                            <th>Due Date</th>
                            <th>Status</th>
                        </tr>
                    """
                    for task in tasks_list:
                        badge = get_progress_badge(task, today)
                        merchant_tables += f"""
                        <tr>
                            <td>
                                {badge}
                                <br>
                                <small>{task.category.cat_name if hasattr(task, 'category') and task.category else ''}</small>
                            </td>
                            <td>{task.due_date.strftime('%Y-%m-%d') if task.due_date else ''}</td>
                            <td>{task.status.replace('_', ' ').title()}</td>
                        </tr>
                        """
                    merchant_tables += "</table><br>"

                subject = "Daily Reminder: You Have Pending Onboarding Tasks"
                message = f"""
                <html>
                <body>
                <p>Hi {user.user_name},</p>
                <p>You have tasks pending across the following merchants:</p>
                {merchant_tables}
                <p>Please make progress before the due dates.</p>
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
                self.stdout.write(self.style.SUCCESS(f"Sent task reminders to {user.user_email}"))