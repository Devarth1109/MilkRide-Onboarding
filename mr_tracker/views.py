from django.shortcuts import HttpResponse, render, redirect, get_object_or_404
from .models import *
from django.core.exceptions import ValidationError
import decimal
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.db import transaction
from datetime import datetime

def dashboard(request):
    if 'email' not in request.session:
        return redirect('login')
    
    user = get_object_or_404(User, user_email=request.session['email'])
    context = {
        'user': user,
        'today': timezone.now().strftime('%Y-%m-%d')
    }

    if user.role == 'admin':
        context.update({
            'merchants': Merchant.objects.all(),
            'support_users': User.objects.filter(role='support'),
            'task_templates': TaskTemplate.objects.filter(user=user),
            'categories': Category.objects.all(),
        })
    elif user.role == 'support':
        # Assigned merchants
        assigned_merchants = Merchant.objects.filter(assigned_manager=user)
        # Categories assigned to this support user
        assigned_categories = Category.objects.filter(assigned_support_users=user)
        # Tasks for those categories
        assigned_tasks = MerchantTask.objects.filter(category__in=assigned_categories)
        context.update({
            'assigned_merchants': assigned_merchants,
            'assigned_categories': assigned_categories,
            'assigned_tasks': assigned_tasks,
            'merchants': assigned_merchants,  # for backward compatibility in template
            'categories': assigned_categories,
            'task_templates': assigned_tasks,  # for backward compatibility in template
        })
    return render(request, 'dashboard.html', context)

def view_support_users(request):
    if 'email' not in request.session:
        return redirect('login')
    user = get_object_or_404(User, user_email=request.session['email'])
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)
    support_users = User.objects.filter(role='support')
    context = {
        'support_users': support_users,
        'user': user,
        'today': timezone.now().strftime('%Y-%m-%d'),
    }
    return render(request, 'admin_user/view_support_users.html', context)

def add_support_user(request):
    if 'email' not in request.session:
        return redirect('login')
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)
    if request.method == 'POST':
        if request.POST['pswd'] != request.POST['c_pswd']:
            return render(request, 'admin_user/add_support_user.html', {'error': 'Passwords do not match'})
        try:
            User.objects.get(user_email=request.POST['email'])
            return render(request, 'admin_user/add_support_user.html', {'error': 'Email already exists'})
        except User.DoesNotExist:
            support_user = User.objects.create(
                user_name=request.POST['username'],
                user_email=request.POST['email'],
                user_pswd=request.POST['pswd'],
                user_confirm_pswd=request.POST['c_pswd'],
                user_phone=request.POST['phone'],
                role='support',
                user_status=request.POST.get('status', 'active')
            )
            # Send credentials email
            subject = "Your Support User Account Has Been Created"
            message = (
                f"Hello {support_user.user_name},\n\n"
                f"Your support user account has been created by the admin.\n\n"
                f"Login Credentials:\n"
                f"Email: {support_user.user_email}\n"
                f"Password: {support_user.user_pswd}\n\n"
                f"Please log in and change your password after first login.\n\n"
                f"Thank you."
            )
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [support_user.user_email],
                fail_silently=True,
            )
            messages.success(request, 'Support user added successfully and credentials sent via email.')
            return redirect('view_support_users')
    return render(request, 'admin_user/add_support_user.html', {'user': user, 'today': today})

def update_support_user(request, user_id):
    if 'email' not in request.session:
        return redirect('login')
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)
    support_user = get_object_or_404(User, id=user_id, role='support')
    if request.method == 'POST':
        support_user.user_name = request.POST['username']
        support_user.user_email = request.POST['email']
        support_user.user_phone = request.POST['phone']
        support_user.user_status = request.POST.get('status', 'active')
        if request.POST.get('pswd'):
            if request.POST['pswd'] != request.POST['c_pswd']:
                return render(request, 'admin_user/update_support_user.html', {'support_user': support_user, 'error': 'Passwords do not match'})
            support_user.user_pswd = request.POST['pswd']
            support_user.user_confirm_pswd = request.POST['c_pswd']
        support_user.save()
        messages.success(request, 'Support user updated successfully.')
        return redirect('view_support_users')
    return render(request, 'admin_user/update_support_user.html', {'support_user': support_user, 'user': user, 'today': today})

def delete_support_user(request, user_id):
    if 'email' not in request.session:
        return redirect('login')
    user = get_object_or_404(User, user_email=request.session['email'])
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)
    support_user = get_object_or_404(User, id=user_id, role='support')
    support_user.delete()
    messages.success(request, 'Support user deleted successfully.')
    return redirect('view_support_users')

def signup(request):
    if request.method == 'POST':
        if request.POST.get('role') != 'admin':
            return render(request, 'signup.html', {'error': 'Only admin signup is allowed. Support users must be added by admin.'})
        try:
            user = User.objects.get(user_email=request.POST['email'])
            return render(request, 'signup.html', {'error': 'Email already exists'})
        except User.DoesNotExist:
            if request.POST['pswd'] == request.POST['c_pswd']:
                user = User.objects.create(
                    user_name=request.POST['username'],
                    user_email=request.POST['email'],
                    user_pswd=request.POST['pswd'],
                    user_confirm_pswd=request.POST['c_pswd'],
                    user_phone=request.POST['phone'],
                    role='admin',
                    user_status=request.POST['status']
                )
                request.session['email'] = user.user_email
                request.session['pswd'] = user.user_pswd
                return redirect('dashboard')
            else:
                return render(request, 'signup.html', {'error': 'Password and Confirm Password do not match... Please try again!!!'})
    else:
        return render(request, 'signup.html')

def login(request):
    if request.method == 'POST':
        try:
            user = User.objects.get(user_email=request.POST['email'], user_pswd=request.POST['pswd'])
            request.session['email'] = user.user_email
            request.session['pswd'] = user.user_pswd

            user_role = user.role
            if user_role == 'admin' or user_role == 'support':
                return redirect('dashboard')
            else: 
                return render(request, 'login.html', {'error': 'Invalid role'})
        except User.DoesNotExist:
            return render(request, 'login.html', {'error': 'Invalid email or password'})
    else:
        return render(request, 'login.html')

def logout(request):
    if 'email' in request.session:
        del request.session['email']
    if 'pswd' in request.session:
        del request.session['pswd']
    return redirect('login')

def add_merchant(request):
    if 'email' not in request.session:
        return redirect('login')
    
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)

    support_users = User.objects.filter(role='support', user_status='active')
    if request.method == 'POST':
        try:
            merchant = Merchant.objects.get(m_email=request.POST['email'])
            return render(request, 'admin_user/add_merchant.html', {'error': 'Merchant with this email already exists'})
        except Merchant.DoesNotExist:
            try:
                setup_fees = request.POST['setup_fees']
                amount_paid = request.POST.get('amount_paid', '')
                pending_amount = request.POST.get('pending_amount', '')
                setup_fees = decimal.Decimal(setup_fees) if setup_fees else None
                amount_paid = decimal.Decimal(amount_paid) if amount_paid else None
                pending_amount = decimal.Decimal(pending_amount) if pending_amount else None

                assigned_manager_id = request.POST.get('assigned_manager')
                assigned_manager = User.objects.get(id=assigned_manager_id) if assigned_manager_id else None

                merchant = Merchant.objects.create(
                    m_name=request.POST['name'],
                    m_email=request.POST['email'],
                    m_phone=request.POST['phone'],
                    m_city=request.POST['city'],
                    m_onboarding_date=request.POST['onboarding_date'],
                    m_due_date=request.POST['due_date'],
                    m_status=request.POST.get('status', 'pending'),
                    m_setup_fees=setup_fees,
                    m_amount_paid=amount_paid,
                    m_amount_paid_date=request.POST.get('amount_paid_date') or None,
                    m_pending_amount=pending_amount,
                    m_pending_amount_due_date=request.POST.get('pending_amount_due_date') or None,
                    m_payment_status=request.POST.get('payment_status', 'unpaid'),
                    assigned_manager=assigned_manager,
                    notes=request.POST.get('notes', '')
                )
                merchant.clean()
                merchant.save()
                return redirect('view_merchants')
            except ValidationError as e:
                return render(request, 'admin_user/add_merchant.html', {'error': str(e), 'support_users': support_users, 'user': user, 'today': today})
    else:
        return render(request, 'admin_user/add_merchant.html', {'support_users': support_users, 'user': user, 'today': today})

def view_merchants(request):
    if 'email' not in request.session:
        return redirect('login')
    
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    if user.role == 'admin':
        merchants = Merchant.objects.all()
        template = 'admin_user/view_merchants.html'
    else:
        merchants = Merchant.objects.filter(assigned_manager=user)
        template = 'support_user/view_merchants.html'
    context = {
        'merchants': merchants,
        'user_role': user.role,
        'user': user,
        'today': today,
    }
    return render(request, template, context)

def update_merchant(request, merchant_id):
    if 'email' not in request.session:
        return redirect('login')
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    if user.role == 'admin':
        merchant = get_object_or_404(Merchant, id=merchant_id)
    else:
        merchant = get_object_or_404(Merchant, id=merchant_id, assigned_manager=user)
    
    support_users = User.objects.filter(role='support', user_status='active')
    if request.method == 'POST':
        try:
            merchant.m_name = request.POST['name']
            merchant.m_email = request.POST['email']
            merchant.m_phone = request.POST['phone']
            merchant.m_city = request.POST['city']
            merchant.m_onboarding_date = request.POST['onboarding_date']
            merchant.m_due_date = request.POST['due_date']
            merchant.m_status = request.POST.get('status', 'pending')
            merchant.m_setup_fees = decimal.Decimal(request.POST['setup_fees']) if request.POST['setup_fees'] else None
            merchant.m_amount_paid = decimal.Decimal(request.POST.get('amount_paid', '') or 0)
            merchant.m_amount_paid_date = request.POST.get('amount_paid_date') or None
            merchant.m_pending_amount = decimal.Decimal(request.POST.get('pending_amount', '') or 0)
            merchant.m_pending_amount_due_date = request.POST.get('pending_amount_due_date') or None
            merchant.m_payment_status = request.POST.get('payment_status', 'unpaid')
            merchant.notes = request.POST.get('notes', '')
            assigned_manager_id = request.POST.get('assigned_manager')
            merchant.assigned_manager = User.objects.get(id=assigned_manager_id) if assigned_manager_id else None
            merchant.clean()
            merchant.save()
            return redirect('view_merchants')
        except ValidationError as e:
            return render(request, 'admin_user/update_merchant.html', {'merchant': merchant, 'error': str(e), 'support_users': support_users, 'user': user, 'today': today})
    else:
        return render(request, 'admin_user/update_merchant.html', {'merchant': merchant, 'support_users': support_users, 'user': user, 'today': today})

def delete_merchant(request, merchant_id):
    if 'email' not in request.session:
        return redirect('login')
    user = get_object_or_404(User, user_email=request.session['email'])
    if user.role == 'admin':
        merchant = get_object_or_404(Merchant, id=merchant_id)
    else:
        merchant = get_object_or_404(Merchant, id=merchant_id, assigned_manager=user)
    merchant.delete()
    return redirect('view_merchants')

def add_category(request):
    if 'email' not in request.session:
        return redirect('login')
    
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)

    support_users = User.objects.filter(role='support', user_status='active')
    if request.method == 'POST':
        try:
            if Category.objects.filter(cat_name=request.POST['name']).exists():
                return render(request, 'admin_user/add_category.html', {
                    'error': 'Category with this name already exists',
                    'support_users': support_users,
                    'user': user,
                    'today': today
                })
            category = Category.objects.create(
                cat_name=request.POST['name'],
                cat_description=request.POST.get('description', ''),
                is_active=True if request.POST.get('is_active', 'true') == 'true' else False
            )
            # Assign support users
            support_user_ids = request.POST.getlist('support_users')
            if support_user_ids:
                category.assigned_support_users.set(support_user_ids)
            category.clean()
            category.save()
            return redirect('view_categories')
        except ValidationError as e:
            return render(request, 'admin_user/add_category.html', {
                'error': str(e),
                'support_users': support_users,
                'user': user,
                'today': today
            })
    else:
        return render(request, 'admin_user/add_category.html', {
            'support_users': support_users,
            'user': user,
            'today': today
        })

def view_categories(request):
    if 'email' not in request.session:
        return redirect('login')
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    if user.role == 'admin':
        categories = Category.objects.all()
        template = 'admin_user/view_categories.html'
    else:
        categories = Category.objects.filter(assigned_support_users=user)
        template = 'support_user/view_categories.html'
    context = {
        'categories': categories,
        'user_role': user.role,
        'user': user,
        'today': today,
    }
    return render(request, template, context)

def update_category(request, category_id):
    if 'email' not in request.session:
        return redirect('login')

    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)

    category = get_object_or_404(Category, id=category_id)
    support_users = User.objects.filter(role='support', user_status='active')

    if request.method == 'POST':
        try:
            category.cat_name = request.POST['name']
            category.cat_description = request.POST.get('description', '')
            is_active_str = request.POST.get('is_active', 'true')
            category.is_active = True if is_active_str == 'true' else False
            support_user_ids = request.POST.getlist('support_users')
            if support_user_ids is not None:
                category.assigned_support_users.set(support_user_ids)
            category.clean()
            category.save()
            return redirect('view_categories')
        except ValidationError as e:
            return render(request, 'admin_user/update_category.html', {
                'category': category,
                'support_users': support_users,
                'error': str(e),
                'user': user,
                'today': today
            })
    else:
        return render(request, 'admin_user/update_category.html', {
            'category': category,
            'support_users': support_users,
            'user': user,
            'today': today
        })

def delete_category(request, category_id):
    if 'email' not in request.session:
        return redirect('login')
    
    user = get_object_or_404(User, user_email=request.session['email'])
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)

    category = get_object_or_404(Category, id=category_id)
    category.delete()
    return redirect('view_categories')

def add_task_template(request):
    if 'email' not in request.session:
        return redirect('login')
    
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)

    if request.method == 'POST':
        try:
            task = TaskTemplate.objects.get(task_name=request.POST['name'])
            return render(request, 'admin_user/add_task_template.html', {'error': 'Task template with this name already exists'})
        except TaskTemplate.DoesNotExist:
            duration = int(request.POST['duration']) if request.POST.get('duration') else 1
            task = TaskTemplate.objects.create(
                task_name=request.POST['name'],
                task_description=request.POST.get('description', ''),
                user=user,
                duration=duration,
                priority=request.POST['priority'],
                category=get_object_or_404(Category, id=request.POST['category_id'])
            )
            task.clean()
            task.save()
            return redirect('view_task_templates')
    else:
        return render(request, 'admin_user/add_task_template.html', {'categories': Category.objects.all(), 'user': user, 'today': today})

def view_task_templates(request):
    if 'email' not in request.session:
        return redirect('login')
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    if user.role not in ['admin', 'support']:
        return HttpResponse('Unauthorized', status=403)
    task_templates = TaskTemplate.objects.all()
    if user.role == 'admin':
        template = 'admin_user/view_task_templates.html'
    else:
        return HttpResponse('Unauthorized', status=403)
    context = {
        'task_templates': task_templates,
        'user_role': user.role,
        'user': user,
        'today': today,
    }
    return render(request, template, context)

def view_category_tasks(request, category_id):
    if 'email' not in request.session:
        return redirect('login')
    
    user = get_object_or_404(User, user_email=request.session['email'])
    category = get_object_or_404(Category, id=category_id, assigned_support_users=user)
    task_templates = TaskTemplate.objects.filter(category=category)
    context = {
        'category': category,
        'tasks': task_templates,
        'user': user,
        'today': timezone.now().strftime('%Y-%m-%d'),
    }
    return render(request, 'support_user/view_category_tasks.html', context)

def update_task_template(request, task_id):
    if 'email' not in request.session:
        return redirect('login')
    
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)

    task = get_object_or_404(TaskTemplate, id=task_id, user=user)
    
    if request.method == 'POST':
        try:
            task.task_name = request.POST['name']
            task.task_description = request.POST.get('description', '')
            task.duration = int(request.POST['duration']) if request.POST.get('duration') else 1
            task.priority = request.POST['priority']
            task.category = get_object_or_404(Category, id=request.POST['category_id'])
            task.clean()
            task.save()
            return redirect('view_task_templates')
        except ValidationError as e:
            return render(request, 'admin_user/update_task_template.html', {'task': task, 'error': str(e), 'user': user, 'today': today})
    else:
        return render(request, 'admin_user/update_task_template.html', {'task': task, 'categories': Category.objects.all(), 'user': user, 'today': today})

def delete_task_template(request, task_id):
    if 'email' not in request.session:
        return redirect('login')
    
    user = get_object_or_404(User, user_email=request.session['email'])
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)

    task = get_object_or_404(TaskTemplate, id=task_id, user=user)
    task.delete()
    return redirect('view_task_templates')

def get_task_templates_by_category(request):
    if 'email' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    user = get_object_or_404(User, user_email=request.session['email'])
    if user.role != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    category_id = request.GET.get('category_id')
    if not category_id:
        return JsonResponse({'templates': []})
    
    try:
        category = Category.objects.get(id=category_id, is_active=True)
        task_templates = TaskTemplate.objects.filter(
            user=user, 
            category=category
        ).values('id', 'task_name', 'task_description', 'duration', 'priority').order_by('task_name')
        
        return JsonResponse({
            'templates': list(task_templates),
            'category_name': category.cat_name
        })
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def add_merchant_task(request, merchant_id):
    if 'email' not in request.session:
        return redirect('login')
    
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)

    merchant = get_object_or_404(Merchant, id=merchant_id)
    categories = Category.objects.filter(is_active=True).order_by('cat_name')
    support_users = User.objects.filter(role='support', user_status='active').order_by('user_name')
    tasks = MerchantTask.objects.filter(merchant=merchant).order_by('-created_at')[:10]  # Show last 10

    # AJAX support for "+Add" button
    if request.method == 'POST' and request.GET.get('ajax') == '1':
        try:
            with transaction.atomic():
                support_user_id = request.POST.get('support_user_id')
                support_user = get_object_or_404(User, id=support_user_id, role='support')
                task_template_id = request.POST.get('task_template_id')
                category_id = request.POST.get('category_id')

                if not category_id:
                    return JsonResponse({'success': False, 'error': 'Please select a category.'})
                
                category = get_object_or_404(Category, id=category_id)
                status = request.POST.get('status', 'pending')
                start_date = request.POST.get('start_date') or None
                due_date = request.POST.get('due_date') or None
                end_date = request.POST.get('end_date') or None

                if task_template_id:
                    try:
                        task_template = TaskTemplate.objects.get(id=task_template_id, category=category, user=user)
                        task = MerchantTask.objects.create(
                            custom_task_name=task_template.task_name,
                            custom_task_description=task_template.task_description,
                            status=status,
                            start_date=start_date,
                            due_date=due_date,
                            end_date=end_date,
                            category=task_template.category,
                            user=support_user,
                            merchant=merchant,
                            task_template=task_template
                        )
                        task.clean()
                        task.save()
                        tasks_count = MerchantTask.objects.filter(merchant=merchant).count()
                        return JsonResponse({
                            'success': True,
                            "forloop_counter": tasks_count,
                            'task': {
                                'category': category.cat_name,
                                'name': task.custom_task_name,
                                'start_date': str(task.start_date),
                                'due_date': str(task.due_date),
                            }
                        })
                    except TaskTemplate.DoesNotExist:
                        return JsonResponse({'success': False, 'error': 'Task template does not exist for the selected category.'})
                else:
                    name = request.POST.get('name', '').strip()
                    description = request.POST.get('description', '').strip()
                    duration = request.POST.get('duration')
                    priority = request.POST.get('priority')

                    if not all([name, description, duration, priority]):
                        return JsonResponse({'success': False, 'error': 'Custom task name, description, duration, and priority are required.'})
                    
                    try:
                        duration = int(duration)
                        if duration <= 0:
                            raise ValueError()
                    except ValueError:
                        return JsonResponse({'success': False, 'error': 'Duration must be a positive integer.'})

                    task_template = TaskTemplate.objects.create(
                        task_name=name,
                        task_description=description,
                        user=user,
                        duration=duration,
                        priority=priority,
                        category=category
                    )
                    task_template.clean()
                    task_template.save()

                    task = MerchantTask.objects.create(
                        custom_task_name=name,
                        custom_task_description=description,
                        status=status,
                        start_date=start_date,
                        due_date=due_date,
                        end_date=end_date,
                        category=category,
                        user=support_user,
                        merchant=merchant,
                        task_template=task_template
                    )
                    task.clean()
                    task.save()
                    tasks_count = MerchantTask.objects.filter(merchant=merchant).count()
                    return JsonResponse({
                        'success': True,
                        "forloop_counter": tasks_count,
                        'task': {
                            'category': category.cat_name,
                            'name': task.custom_task_name,
                            'start_date': str(task.start_date),
                            'due_date': str(task.due_date),
                        }
                    })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    # Standard POST (non-AJAX, fallback)
    elif request.method == 'POST':
        try:
            with transaction.atomic():
                support_user_id = request.POST.get('support_user_id')
                support_user = get_object_or_404(User, id=support_user_id, role='support')
                task_template_id = request.POST.get('task_template_id')
                category_id = request.POST.get('category_id')

                if not category_id:
                    raise ValidationError("Please select a category.")
                
                category = get_object_or_404(Category, id=category_id)
                status = request.POST.get('status', 'pending')
                start_date = request.POST.get('start_date') or None
                due_date = request.POST.get('due_date') or None
                end_date = request.POST.get('end_date') or None

                if task_template_id:
                    try:
                        task_template = TaskTemplate.objects.get(id=task_template_id, category=category, user=user)
                        task = MerchantTask.objects.create(
                            custom_task_name=task_template.task_name,
                            custom_task_description=task_template.task_description,
                            status=status,
                            start_date=start_date,
                            due_date=due_date,
                            end_date=end_date,
                            category=task_template.category,
                            user=support_user,
                            merchant=merchant,
                            task_template=task_template
                        )
                        task.clean()
                        task.save()
                        messages.success(request, f'Task "{task_template.task_name}" has been successfully added for {merchant.m_name}.')
                        return redirect('view_merchant_tasks', merchant_id=merchant.id)
                    except TaskTemplate.DoesNotExist:
                        raise ValidationError('Task template does not exist for the selected category.')
                else:
                    name = request.POST.get('name', '').strip()
                    description = request.POST.get('description', '').strip()
                    duration = request.POST.get('duration')
                    priority = request.POST.get('priority')

                    if not all([name, description, duration, priority]):
                        raise ValidationError('Custom task name, description, duration, and priority are required.')
                    
                    try:
                        duration = int(duration)
                        if duration <= 0:
                            raise ValueError()
                    except ValueError:
                        raise ValidationError('Duration must be a positive integer.')

                    task_template = TaskTemplate.objects.create(
                        task_name=name,
                        task_description=description,
                        user=user,
                        duration=duration,
                        priority=priority,
                        category=category
                    )
                    task_template.clean()
                    task_template.save()

                    task = MerchantTask.objects.create(
                        custom_task_name=name,
                        custom_task_description=description,
                        status=status,
                        start_date=start_date,
                        due_date=due_date,
                        end_date=end_date,
                        category=category,
                        user=support_user,
                        merchant=merchant,
                        task_template=task_template
                    )
                    task.clean()
                    task.save()
                    messages.success(request, f'Custom task "{name}" has been successfully added for {merchant.m_name}.')
                    return redirect('view_merchant_tasks', merchant_id=merchant.id)
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')

    # GET request
    return render(request, 'admin_user/add_merchant_task.html', {
        'merchant': merchant,
        'categories': categories,
        'support_users': support_users,
        'tasks': tasks,
        'user_role': user.role,
        'user': user
    })

def view_merchant_tasks(request, merchant_id):
    if 'email' not in request.session:
        return redirect('login')
    
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    merchant = get_object_or_404(Merchant, id=merchant_id)
    tasks = MerchantTask.objects.filter(merchant=merchant)
    if user.role == 'admin':
        template = 'admin_user/view_merchant_tasks.html'
    else:
        template = 'support_user/view_merchant_tasks.html'
    context = {
        'tasks': tasks,
        'merchant': merchant,
        'user_role': user.role,
        'user': user,
        'today': today
    }
    return render(request, template, context)

def merchant_task_details(request, task_id):
    task = get_object_or_404(MerchantTask, pk=task_id)
    merchant = task.merchant
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status and new_status in ['pending', 'in_progress', 'on_hold', 'completed']:
            previous_status = task.status
            if previous_status != new_status:
                MerchantTaskHistory.objects.create(
                    task=task,
                    changed_by=user,
                    change_description=f"Status changed from '{previous_status}' to '{new_status}'",
                    change_time=timezone.now()
                )
            task.status = new_status
            if new_status == 'completed':
                task.end_date = timezone.now().date()
            elif previous_status == 'completed' and new_status in ['pending', 'in_progress', 'on_hold']:
                task.end_date = None
            task.save()
            return redirect('support_merchant_task_details', task_id=task.id)

    context = {
        'task': task,
        'merchant': merchant,
        'user': user,
        'today': today,
    }
    return render(request, 'support_user/merchant_task_details.html', context)

def update_merchant_task(request, task_id):
    if 'email' not in request.session:
        return redirect('login')
    
    user = get_object_or_404(User, user_email=request.session['email'])
    today = timezone.now().strftime('%Y-%m-%d')
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)

    task = get_object_or_404(MerchantTask, id=task_id)
    categories = Category.objects.all()
    task_templates = TaskTemplate.objects.all()

    def parse_date(date_str):
        if date_str:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return None
        return None

    if request.method == 'POST':
        try:
            # Store old values for logging
            old_name = task.custom_task_name
            old_desc = task.custom_task_description
            old_status = task.status
            old_start_date = task.start_date
            old_due_date = task.due_date
            old_end_date = task.end_date
            old_category = task.category

            template_id = request.POST.get('task_template_id')
            name = request.POST.get('name', '')
            description = request.POST.get('description', '')
            status = request.POST.get('status', '')
            start_date = parse_date(request.POST.get('start_date'))
            due_date = parse_date(request.POST.get('due_date'))
            end_date = parse_date(request.POST.get('end_date'))
            category = get_object_or_404(Category, id=request.POST['category_id'])

            # If a template is selected, link it and update its fields
            if template_id:
                selected_template = get_object_or_404(TaskTemplate, id=template_id)
                selected_template.task_name = name
                selected_template.task_description = description
                selected_template.category = category
                selected_template.save()
                task.task_template = selected_template
                task.custom_task_name = ''
                task.custom_task_description = ''
            else:
                # Custom task: update or create a template and link it
                if task.task_template:
                    # Update the existing template
                    template = task.task_template
                    template.task_name = name
                    template.task_description = description
                    template.category = category
                    template.save()
                else:
                    # Create a new template for this custom task
                    template = TaskTemplate.objects.create(
                        task_name=name,
                        task_description=description,
                        category=category
                    )
                    task.task_template = template
                task.custom_task_name = name
                task.custom_task_description = description

            previous_status = task.status
            task.status = status
            task.start_date = start_date
            task.due_date = due_date
            task.category = category

            # Set end_date logic
            if previous_status == 'completed' and status in ['pending', 'in_progress', 'on_hold']:
                task.end_date = None
            elif status == 'completed':
                task.end_date = task.end_date or timezone.now().date()
            else:
                task.end_date = end_date

            # Build change description for logging
            changes = []
            if old_name != task.custom_task_name:
                changes.append(f"Task Name changed from '{old_name}' to '{task.custom_task_name}'")
            else:
                changes.append("Task Name unchanged")

            if old_desc != task.custom_task_description:
                changes.append("Description updated")
            else:
                changes.append("Description unchanged")

            if old_status != task.status:
                changes.append(f"Status changed from '{old_status}' to '{task.status}'")
            else:
                changes.append("Status unchanged")

            if str(old_start_date) != str(task.start_date):
                changes.append(f"Start date changed from '{old_start_date}' to '{task.start_date}'")
            else:
                changes.append("Start date unchanged")

            if str(old_due_date) != str(task.due_date):
                changes.append(f"Due date changed from '{old_due_date}' to '{task.due_date}'")
            else:
                changes.append("Due date unchanged")

            if str(old_end_date) != str(task.end_date):
                changes.append(f"End date changed from '{old_end_date}' to '{task.end_date}'")
            else:
                changes.append("End date unchanged")

            if old_category != task.category:
                changes.append(f"Category changed from '{old_category}' to '{task.category}'")
            else:
                changes.append("Category unchanged")

            task.clean()
            task.save()

            # Log the changes if any
            if changes:
                change_description = "; ".join(changes)
                MerchantTaskHistory.objects.create(
                    task=task,
                    changed_by=user,
                    change_description=change_description,
                    change_time=timezone.now()
                )

            return redirect('view_merchant_tasks', merchant_id=task.merchant.id)
        except ValidationError as e:
            return render(request, 'admin_user/update_merchant_task.html', {
                'task': task,
                'categories': categories,
                'task_templates': task_templates,
                'error': str(e),
                'user': user,
                'today': today
            })
    else:
        return render(request, 'admin_user/update_merchant_task.html', {
            'task': task,
            'categories': categories,
            'task_templates': task_templates,
            'user': user,
            'today': today
        })

def delete_merchant_task(request, task_id):
    if 'email' not in request.session:
        return redirect('login')
    user = get_object_or_404(User, user_email=request.session['email'])
    if user.role != 'admin':
        return HttpResponse('Unauthorized', status=403)
    task = get_object_or_404(MerchantTask, id=task_id)
    merchant_id = task.merchant.id
    task.delete()
    return redirect('view_merchant_tasks', merchant_id=merchant_id)

def view_task_history(request, task_id):
    if 'email' not in request.session:
        return redirect('login')
    user = get_object_or_404(User, user_email=request.session['email'])
    task = get_object_or_404(MerchantTask, id=task_id)
    history = MerchantTaskHistory.objects.filter(task=task).order_by('-change_time')
    context = {
        'task': task,
        'history': history,
        'user': user,
    }
    return render(request, 'admin_user/view_task_history.html', context)