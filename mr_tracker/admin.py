from django.contrib import admin
from .models import User, Merchant, Category, TaskTemplate, MerchantTask

class UserAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'user_email', 'role', 'user_status')
    search_fields = ('user_name', 'user_email')

class MerchantAdmin(admin.ModelAdmin):
    list_display = ('m_name', 'm_email', 'm_phone', 'm_city', 'm_status')
    search_fields = ('m_name', 'm_email', 'm_phone')
    list_filter = ('m_status',)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('cat_name', 'is_active')
    search_fields = ('cat_name',)

class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'duration', 'priority', 'user')
    search_fields = ('task_name',)
    list_filter = ('priority',)

class MerchantTaskAdmin(admin.ModelAdmin):
    list_display = ('custom_task_name', 'status', 'merchant', 'user')
    search_fields = ('custom_task_name',)
    list_filter = ('status',)

admin.site.register(User, UserAdmin)
admin.site.register(Merchant, MerchantAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(TaskTemplate, TaskTemplateAdmin)
admin.site.register(MerchantTask, MerchantTaskAdmin)