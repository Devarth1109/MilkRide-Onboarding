from django.urls import path
from .views import *

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('signup/', signup, name='signup'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    
    # Admin URLs
    path('support-users/', view_support_users, name='view_support_users'),
    path('support-users/add/', add_support_user, name='add_support_user'),
    path('support-users/update/<int:user_id>/', update_support_user, name='update_support_user'),
    path('support-users/delete/<int:user_id>/', delete_support_user, name='delete_support_user'),

    path('admin_user/add_merchant/', add_merchant, name='add_merchant'),
    path('admin_user/update_merchant/<int:merchant_id>/', update_merchant, name='update_merchant'),
    path('admin_user/view_merchants/', view_merchants, name='view_merchants'),
    path('admin_user/delete_merchant/<int:merchant_id>/', delete_merchant, name='delete_merchant'),
    
    path('admin_user/add_category/', add_category, name='add_category'),
    path('admin_user/update_category/<int:category_id>/', update_category, name='update_category'),
    path('admin_user/view_categories/', view_categories, name='view_categories'),
    path('admin_user/delete_category/<int:category_id>/', delete_category, name='delete_category'),
    
    path('admin_user/add_task_template/', add_task_template, name='add_task_template'),
    path('admin_user/update_task_template/<int:task_id>/', update_task_template, name='update_task_template'),
    path('admin_user/view_task_templates/', view_task_templates, name='view_task_templates'),
    path('admin_user/delete_task_template/<int:task_id>/', delete_task_template, name='delete_task_template'),
    
    path('get-task-templates/', get_task_templates_by_category, name='get_task_templates_by_category'),
    path('admin_user/add_merchant_task/<int:merchant_id>/', add_merchant_task, name='add_merchant_task'),
    path('admin_user/update_merchant_task/<int:task_id>/', update_merchant_task, name='update_merchant_task'),
    path('admin_user/delete_merchant_task/<int:task_id>/', delete_merchant_task, name='delete_merchant_task'),
    path('admin_user/view_merchant_tasks/<int:merchant_id>/', view_merchant_tasks, name='view_merchant_tasks'),
    path('admin_user/view_task_history/<int:task_id>/', view_task_history, name='view_task_history'),

    # Support URLs
    path('support_user/view_merchants/', view_merchants, name='support_view_merchants'),
    path('support_user/view_categories/', view_categories, name='support_view_categories'),
    path('support_user/view_category_tasks/<int:category_id>/', view_category_tasks, name='support_view_category_tasks'),
    path('support_user/view_merchant_tasks/<int:merchant_id>/', view_merchant_tasks, name='support_view_merchant_tasks'),
    path('support_user/merchant_task_details/<int:task_id>/', merchant_task_details, name='support_merchant_task_details')
]