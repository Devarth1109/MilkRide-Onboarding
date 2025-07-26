from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.core.exceptions import ValidationError
from django.utils import timezone

class User(models.Model):
    user_name = models.CharField(max_length=150)
    user_email = models.EmailField(unique=True, null=False, blank=False)
    user_pswd = models.CharField(max_length=128)
    user_confirm_pswd = models.CharField(max_length=128, null=True, blank=True)
    user_phone = PhoneNumberField(unique=True, null=False, blank=False)
    role = models.CharField(max_length=50, choices=[('admin', 'Admin'), ('support', 'Support')], default='support')
    user_status = models.CharField(max_length=50, choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')

    def __str__(self):
        return self.user_name

class Merchant(models.Model):
    m_name = models.CharField(max_length=255)
    m_email = models.EmailField(unique=True, null=False, blank=False)
    m_phone = PhoneNumberField(unique=True, null=False, blank=False)
    m_city = models.CharField(max_length=100)
    m_onboarding_date = models.DateField(null=True, blank=True)
    m_due_date = models.DateField(null=True, blank=True)
    m_status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('on_hold', 'On Hold'),
            ('completed', 'Completed')
        ],
        default='pending'
    )
    m_setup_fees = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    m_amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    m_amount_paid_date = models.DateField(null=True, blank=True)
    m_pending_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    m_pending_amount_due_date = models.DateField(null=True, blank=True)
    m_payment_status = models.CharField(
        max_length=50,
        choices=[('paid', 'Paid'), ('unpaid', 'Unpaid')],
        default='unpaid'
    )
    assigned_manager = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_merchants'
    )
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.m_setup_fees is not None and self.m_amount_paid is not None:
            if self.m_amount_paid > self.m_setup_fees:
                raise ValidationError("Amount paid cannot exceed setup fees.")
        if self.m_pending_amount is not None:
            if self.m_pending_amount < 0:
                raise ValidationError("Pending amount cannot be negative.")
        if self.m_due_date and self.m_onboarding_date:
            if self.m_due_date < self.m_onboarding_date:
                raise ValidationError("Due date cannot be earlier than onboarding date.")

    def save(self, *args, **kwargs):
        # Calculate pending amount
        if self.m_setup_fees is not None and self.m_amount_paid is not None:
            self.m_pending_amount = self.m_setup_fees - self.m_amount_paid
        elif self.m_setup_fees is not None:
            self.m_pending_amount = self.m_setup_fees
        else:
            self.m_pending_amount = None

        # Set payment status
        if self.m_setup_fees is not None and self.m_amount_paid is not None:
            self.m_payment_status = 'paid' if self.m_amount_paid >= self.m_setup_fees else 'unpaid'
        else:
            self.m_payment_status = 'unpaid'

        # Set amount paid date if not set and amount paid is entered
        if self.m_amount_paid and not self.m_amount_paid_date:
            self.m_amount_paid_date = timezone.now().date()

        # Set pending amount due date if not set and there is a pending amount
        if self.m_pending_amount and self.m_pending_amount > 0 and not self.m_pending_amount_due_date:
            self.m_pending_amount_due_date = self.m_due_date

        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.m_name

class Category(models.Model):
    cat_name = models.CharField(max_length=100, unique=True)
    cat_description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    assigned_support_users = models.ManyToManyField('User', blank=True, related_name='categories')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if not self.cat_name:
            raise ValidationError("Category name cannot be empty.")

    def __str__(self):
        return self.cat_name

class TaskTemplate(models.Model):
    task_name = models.CharField(max_length=255)
    task_description = models.TextField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_templates')
    duration = models.IntegerField(help_text="Duration in days")
    priority = models.CharField(max_length=50, choices=[
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='task_templates')
    order = models.IntegerField(default=0, help_text="Order of the task in the template")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Ensure duration is always an integer
        if isinstance(self.duration, str):
            try:
                self.duration = int(self.duration)
            except ValueError:
                raise ValidationError("Duration must be a positive integer.")
        if not self.task_name:
            raise ValidationError("Task name cannot be empty.")
        if self.duration <= 0:
            raise ValidationError("Duration must be a positive integer.")
        
    def __str__(self):
        return self.task_name
    
class MerchantTask(models.Model):
    custom_task_name = models.CharField(max_length=255)
    custom_task_description = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('on_hold', 'On Hold'),
            ('completed', 'Completed')
        ],
        default='pending'
    )
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='merchant_tasks')
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='merchant_tasks')
    merchant = models.ForeignKey('Merchant', on_delete=models.CASCADE, related_name='tasks')
    task_template = models.ForeignKey('TaskTemplate', on_delete=models.CASCADE, null=True, blank=True, related_name='merchant_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Only require custom_task_name if no template is used
        if not self.task_template and not self.custom_task_name:
            raise ValidationError("Custom task name cannot be empty.")
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValidationError("Start date cannot be after due date.")
        if self.task_template and self.task_template.duration <= 0:
            raise ValidationError("Task template duration must be a positive integer.")
        if self.task_template:
            self.custom_task_name = self.task_template.task_name
            self.custom_task_description = self.task_template.task_description
            self.category = self.task_template.category
        if self.status not in ['pending', 'in_progress', 'on_hold', 'completed']:
            raise ValidationError("Invalid status for the task.")
        if self.user and self.user.role != 'support':
            raise ValidationError("Only support users can be assigned to tasks.")
        super().clean()

    def save(self, *args, **kwargs):
        # Automatically set end_date if status is completed
        if self.status == 'completed' and not self.end_date:
            from django.utils import timezone
            self.end_date = timezone.now().date()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.custom_task_name

class MerchantUserNotification(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notified = models.BooleanField(default=False)

    class Meta:
        unique_together = ('merchant', 'user')

class MerchantTaskHistory(models.Model):
    task = models.ForeignKey('MerchantTask', on_delete=models.CASCADE, related_name='history')
    changed_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True)
    change_time = models.DateTimeField(auto_now_add=True)
    change_description = models.TextField()

    def __str__(self):
        return f"History for {self.task} at {self.change_time}"