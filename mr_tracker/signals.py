from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import *
from datetime import datetime

@receiver(pre_save, sender=Merchant)
def send_manager_assignment_email(sender, instance, **kwargs):
    send = False
    if not instance.pk:
        # New merchant, assigned_manager is set
        if instance.assigned_manager:
            send = True
    else:
        old = Merchant.objects.filter(pk=instance.pk).first()
        old_manager = old.assigned_manager if old else None
        send = old_manager != instance.assigned_manager and instance.assigned_manager is not None

    if send:
        manager = instance.assigned_manager
        subject = "Your Onboarding Manager is Assigned"
        message = f"""Hi {instance.m_name},

Your onboarding manager has been assigned:

👤 Manager: {manager.user_name}
📧 Email: {manager.user_email}
📞 Phone: {manager.user_phone}

They will support you throughout the onboarding process.

Thank you,
Onboarding Team
"""
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.m_email],
            fail_silently=True,
        )

@receiver(post_save, sender=MerchantTask)
def notify_task_assigned(sender, instance, created, **kwargs):
    if created:
        merchant = instance.merchant
        user = instance.user
        subject = f"New Task Assigned for Merchant: {merchant.m_name}"
        due_date_str = instance.due_date
        if hasattr(instance.due_date, 'strftime'):
            due_date_str = instance.due_date.strftime('%Y-%m-%d')
        message = f"""Hi {user.user_name},

You have been assigned a new onboarding task for merchant {merchant.m_name}:

- Task: {instance.custom_task_name}
- Due: {due_date_str if due_date_str else 'N/A'}

Please begin your work as per the timeline.

Thanks,  
Onboarding Team
"""
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.user_email],
            fail_silently=False,
        )

@receiver(pre_save, sender=MerchantTask)
def cache_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = MerchantTask.objects.get(pk=instance.pk)
            instance._old_status = old.status
        except MerchantTask.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=MerchantTask)
def send_task_completion_email(sender, instance, created, **kwargs):
    def get_in_time(task):
        if task.end_date and task.due_date:
            return "In Time" if task.end_date <= task.due_date else "Overdue"
        return ""
    # Send email if task is created with completed status
    if created and instance.status == 'completed':
        support_user = instance.user
        merchant = instance.merchant
        subject = f"Task Completed for Merchant: {merchant.m_name}"
        in_time = get_in_time(instance)
        message = f"""
        <html>
        <body>
        <p>Hi {support_user.user_name},</p>
        <p>Your merchant {merchant.m_name} completed the task:</p>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;">
            <tr>
                <th>Task Name</th>
                <th>Due Date</th>
                <th>Status</th>
                <th>In Time?</th>
            </tr>
            <tr>
                <td>
                    {instance.custom_task_name}
                    <br>
                    <small>{instance.category.cat_name if instance.category else ''}</small>
                </td>
                <td>{instance.due_date.strftime('%Y-%m-%d') if instance.due_date else ''}</td>
                <td>{instance.status.title()}</td>
                <td>{in_time}</td>
            </tr>
        </table>
        <p>Regards,<br>Onboarding Team</p>
        </body>
        </html>
        """
        send_mail(
            subject,
            "",
            settings.DEFAULT_FROM_EMAIL,
            [support_user.user_email],
            html_message=message,
            fail_silently=False,
        )
    # Send email if status changed to completed
    elif not created and getattr(instance, '_old_status', None) != 'completed' and instance.status == 'completed':
        support_user = instance.user
        merchant = instance.merchant
        subject = f"Task Completed for Merchant: {merchant.m_name}"
        in_time = get_in_time(instance)
        message = f"""
        <html>
        <body>
        <p>Hi {support_user.user_name},</p>
        <p>Your merchant {merchant.m_name} completed the task:</p>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;">
            <tr>
                <th>Task Name</th>
                <th>Due Date</th>
                <th>Status</th>
                <th>In Time?</th>
            </tr>
            <tr>
                <td>
                    {instance.custom_task_name}
                    <br>
                    <small>{instance.category.cat_name if instance.category else ''}</small>
                </td>
                <td>{instance.due_date.strftime('%Y-%m-%d') if instance.due_date else ''}</td>
                <td>{instance.status.title()}</td>
                <td>{in_time}</td>
            </tr>
        </table>
        <p>Regards,<br>Onboarding Team</p>
        </body>
        </html>
        """
        send_mail(
            subject,
            "",
            settings.DEFAULT_FROM_EMAIL,
            [support_user.user_email],
            html_message=message,
            fail_silently=False,
        )

def get_in_time(task):
    end_date = task.end_date
    due_date = task.due_date
    # Convert to date if they are strings
    if isinstance(end_date, str):
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except Exception:
            return ""
    if isinstance(due_date, str):
        try:
            due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
        except Exception:
            return ""
    if end_date and due_date:
        return "In Time" if end_date <= due_date else "Overdue"
    return ""

@receiver(post_save, sender=Merchant)
def send_all_tasks_completed_email(sender, instance, **kwargs):
    # Only send if status is completed and just changed to completed
    if hasattr(instance, '_old_status') and instance._old_status != 'completed' and instance.m_status == 'completed':
        all_tasks = MerchantTask.objects.filter(merchant=instance)
        if all_tasks.exists() and all(task.status == 'completed' for task in all_tasks):
            support_users = set(all_tasks.values_list('user', flat=True))
            support_user_objs = User.objects.filter(id__in=support_users)
            # Build HTML table
            table_rows = ""
            for task in all_tasks:
                in_time = get_in_time(task)
                table_rows += f"""
                <tr>
                    <td>
                        {task.custom_task_name}
                        <br>
                        <small>{task.category.cat_name if task.category else ''}</small>
                    </td>
                    <td>{task.due_date.strftime('%Y-%m-%d') if task.due_date else ''}</td>
                    <td>{task.status.title()}</td>
                    <td>{in_time}</td>
                </tr>
                """
            subject = f"All {instance.m_name}'s tasks are completed"
            table_html = f"""
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;">
                <tr>
                    <th>Task Name</th>
                    <th>Due Date</th>
                    <th>Status</th>
                    <th>In Time?</th>
                </tr>
                {table_rows}
            </table>
            """
            for support_user in support_user_objs:
                message = f"""
                <html>
                <body>
                <p>Hi {support_user.user_name},</p>
                <p>Your merchant {instance.m_name} completed all the assigned tasks.</p>
                {table_html}
                <p>Regards,<br>Onboarding Team</p>
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

@receiver(pre_save, sender=Merchant)
def cache_old_merchant_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = Merchant.objects.get(pk=instance.pk)
            instance._old_status = old.m_status
        except Merchant.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=MerchantTask)
def update_merchant_status(sender, instance, **kwargs):
    merchant = instance.merchant
    all_tasks = MerchantTask.objects.filter(merchant=merchant)
    if all_tasks.exists() and all(task.status == 'completed' for task in all_tasks):
        merchant.m_status = 'completed'
    else:
        merchant.m_status = 'pending'
    merchant.save(update_fields=['m_status'])