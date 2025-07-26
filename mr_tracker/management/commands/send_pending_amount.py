from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from mr_tracker.models import User, Merchant

class Command(BaseCommand):
    help = 'Send daily pending amount summary to admin users at 10 AM'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        admin_users = User.objects.filter(role='admin', user_status='active')
        support_users = User.objects.filter(role='support', user_status='active')

        # Build the summary for all support users
        support_sections = ""
        for support_user in support_users:
            merchants = support_user.assigned_merchants.filter(
                m_pending_amount__gt=0
            )
            if not merchants.exists():
                continue

            support_sections += f"""
            <div style="margin-bottom: 20px;">
            <h4 style="text-align:center;">
                Support User: {support_user.user_email}
            </h4>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse; width:100%;">
                <tr>
                    <th>Merchant</th>
                    <th>Setup Fees</th>
                    <th>Paid Amount</th>
                    <th>Paid Date</th>
                    <th>Pending Amount</th>
                    <th>Due Date</th>
                </tr>
            """
            for merchant in merchants:
                support_sections += f"""
                <tr>
                    <td>{merchant.m_name}</td>
                    <td>{merchant.m_setup_fees or ''}</td>
                    <td>{merchant.m_amount_paid or ''}</td>
                    <td>{merchant.m_amount_paid_date or ''}</td>
                    <td>{merchant.m_pending_amount or ''}</td>
                    <td>{merchant.m_pending_amount_due_date or ''}</td>
                </tr>
                """
            support_sections += "</table></div>"

        if not support_sections:
            self.stdout.write(self.style.WARNING("No merchants with pending amounts. No email sent."))
            return

        subject = "🔰 Urgent: Pending Amounts of merchants"
        for admin in admin_users:
            message = f"""
            <html>
            <body>
            <p>Hi {admin.user_name},</p>
            <p>This is a reminder that the following support user's merchants have pending amounts.</p>
            {support_sections}
            <p>Please take the necessary action or follow up.</p>
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
            self.stdout.write(self.style.SUCCESS(f"Pending amount summary sent to {admin.user_email}"))