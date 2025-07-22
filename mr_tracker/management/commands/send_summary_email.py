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
            merchants = user.assigned_merchants.all()
            print(f"User: {user.user_email}, Merchants: {merchants.count()}")
            if not merchants.exists():
                continue
            tasks = MerchantTask.objects.filter(
                merchant__in=merchants
            ).select_related('merchant', 'category')
            print(f"User: {user.user_email}, Tasks: {tasks.count()}")
            if not tasks.exists():
                continue

            # Summary counts
            total_merchants = merchants.count()
            total_tasks = tasks.count()
            total_completed_tasks = tasks.filter(status='completed').count()
            total_completed_merchants = merchants.filter(m_status='completed').count()
            total_overdue_tasks = tasks.filter(due_date__lt=today).exclude(status='completed').count()
            total_pending_inprogress_tasks = tasks.filter(status__in=['pending', 'in_progress']).count()

            subject = "Summary email to check merchant progress"
            message = f"""
            <html>
            <body>
            <p>Hi {user.user_name},</p>
            <p>You have merchants and it's assigned task, it's details is as below</p>
            <ul>
                <li><b>Total merchants:</b> {total_merchants}</li>
                <li><b>Total merchant's tasks:</b> {total_tasks}</li>
                <li><b>Total completed merchant's tasks:</b> {total_completed_tasks}</li>
                <li><b>Total completed merchants:</b> {total_completed_merchants}</li>
                <li><b>Total overdue tasks:</b> {total_overdue_tasks}</li>
                <li><b>Total pending or in progress tasks:</b> {total_pending_inprogress_tasks}</li>
            </ul>
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