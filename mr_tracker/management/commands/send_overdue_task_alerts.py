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
            ).select_related('merchant')
            print(f"User: {user.user_name}, Tasks: {overdue_tasks.count()}")
            if overdue_tasks.exists():
                # Group tasks by merchant
                print(f"Found {overdue_tasks.count()} overdue tasks for user {user.user_name}")
                merchant_map = {}
                for task in overdue_tasks:
                    merchant = task.merchant
                    if merchant not in merchant_map:
                        merchant_map[merchant] = []
                    days_overdue = (today - task.due_date).days
                    merchant_map[merchant].append(
                        f"- {task.custom_task_name} — Overdue by {days_overdue} day{'s' if days_overdue > 1 else ''}"
                    )
                # Compose email
                lines = []
                for merchant, tasks in merchant_map.items():
                    lines.append(f"\n📍 Merchant: {merchant.m_name}")
                    lines.extend(tasks)
                subject = "⚠️ Urgent: Overdue Tasks Require Your Attention"
                message = f"""Hi {user.user_name},

You have overdue tasks across the following merchants:
{chr(10).join(lines)}

Please address these as soon as possible to avoid delays.

Regards,  
Onboarding Team
"""
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.user_email],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f"Sent overdue alert to {user.user_email}"))