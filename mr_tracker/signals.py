from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import *

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
    # Send email if task is created with completed status
    if created and instance.status == 'completed':
        support_user = instance.user
        merchant = instance.merchant
        subject = f"Task Completed for Merchant: {merchant.m_name}"
        message = f"""Hi {support_user.user_name},

Your merchant {merchant.m_name} completed the task:

Task details:
- Task: {instance.custom_task_name}
- Status: Completed
- Category: {instance.category.cat_name}

📍 Merchant: {merchant.m_name}
- {instance.custom_task_name}

Regards,  
Onboarding Team
"""
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [support_user.user_email],
            fail_silently=False,
        )
    # Send email if status changed to completed
    elif not created and getattr(instance, '_old_status', None) != 'completed' and instance.status == 'completed':
        support_user = instance.user
        merchant = instance.merchant
        subject = f"Task Completed for Merchant: {merchant.m_name}"
        message = f"""Hi {support_user.user_name},

Your merchant {merchant.m_name} completed the task:

Task details:
- Task: {instance.custom_task_name}
- Status: Completed
- Category: {instance.category.cat_name}

📍 Merchant: {merchant.m_name}
- {instance.custom_task_name}

Regards,  
Onboarding Team
"""
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [support_user.user_email],
            fail_silently=False,
        )

@receiver(post_save, sender=MerchantTask)
def send_all_tasks_completed_email(sender, instance, **kwargs):
    merchant = instance.merchant
    all_tasks = MerchantTask.objects.filter(merchant=merchant)
    print("Signal triggered for merchant:", merchant.m_name)
    print("Merchant status:", merchant.m_status)
    print("All tasks completed:", all(task.status == 'completed' for task in all_tasks))
    if all_tasks.exists() and all(task.status == 'completed' for task in all_tasks) and merchant.m_status == 'completed':
        support_users = set(all_tasks.values_list('user', flat=True))
        support_user_objs = User.objects.filter(id__in=support_users)
        task_lines = []
        for task in all_tasks:
            task_lines.append(
                f"- {task.custom_task_name} - Start Date [{task.start_date}] - Due Date [{task.due_date}] - End Date [{task.end_date}]"
            )
        task_details = "\n\t" + "\n\t".join(task_lines)
        subject = f"All {merchant.m_name}'s tasks are completed"
        for support_user in support_user_objs:
            message = f"""Hi {support_user.user_name},

Your merchant {merchant.m_name} completed all the assigned tasks.

Task Details:
{task_details}

Regards,
Onboarding Team
"""
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [support_user.user_email],
                fail_silently=True,
            )

@receiver(post_save, sender=MerchantTask)
def update_merchant_status(sender, instance, **kwargs):
    merchant = instance.merchant
    all_tasks = MerchantTask.objects.filter(merchant=merchant)
    if all_tasks.exists() and all(task.status == 'completed' for task in all_tasks):
        merchant.m_status = 'completed'
    else:
        merchant.m_status = 'pending'
    merchant.save(update_fields=['m_status'])