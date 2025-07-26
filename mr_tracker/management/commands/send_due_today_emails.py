from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from mr_tracker.models import Merchant

class Command(BaseCommand):
    help = "Send pending amount due today email to support users"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        # Get all merchants with pending amounts due today
        merchants_due_today = Merchant.objects.filter(
            m_pending_amount__gt=0,
            m_pending_amount_due_date=today,
            assigned_manager__isnull=False
        )

        if not merchants_due_today.exists():
            self.stdout.write("No merchants with pending amounts due today.")
            return

        # Group merchants by support user
        support_user_map = {}
        for merchant in merchants_due_today:
            manager = merchant.assigned_manager
            if manager not in support_user_map:
                support_user_map[manager] = []
            support_user_map[manager].append(merchant)

        for support_user, merchants in support_user_map.items():
            table_rows = ""
            for merchant in merchants:
                table_rows += f"""
                <tr>
                    <td>{merchant.m_name}</td>
                    <td>{merchant.m_setup_fees or ''}</td>
                    <td>{merchant.m_amount_paid or ''}</td>
                    <td>{merchant.m_amount_paid_date or ''}</td>
                    <td>{merchant.m_pending_amount or ''}</td>
                </tr>
                """

            today_str = timezone.now().strftime('%d %b %Y')
            subject = f"⏰ Action Required: Pending Amounts for Assigned Merchants Due Today ({today_str})"
            message = f"""
            <html>
            <body>
            <p>Hi {support_user.user_name},</p>
            <p>This is a reminder that the following merchants have pending amounts due today (<strong>{today_str}</strong>):</p>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;">
                <tr>
                    <th>Merchant</th>
                    <th>Setup Fees</th>
                    <th>Paid Amount</th>
                    <th>Paid Date</th>
                    <th>Pending Amount</th>
                </tr>
                {table_rows}
            </table>
            <p>Please take the necessary action or follow up accordingly.<br>
            Let us know if you need any further details.</p>
            <p>Thanks & Regards,<br>Onboarding Team</p>
            </body>
            </html>
            """
            send_mail(
                subject,
                "",
                settings.DEFAULT_FROM_EMAIL,
                [support_user.user_email],
                html_message=message,
                fail_silently=True,
            )
            self.stdout.write(f"Email sent to {support_user.user_email} for {len(merchants)} merchant(s).")
