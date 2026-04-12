from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ImprovementGoal, RiskAlert, ImprovementAction
from users.models import User
from django.db.models import Count
from django.contrib import messages


@login_required
def dashboard_ee(request):
    """Dashboard del establecimiento del usuario autenticado."""
    establishment = request.GET.get('ee') or request.user.establishment
    goals = ImprovementGoal.objects.filter(establishment=establishment)
    # SQLite no soporta JSONField __contains → filtramos en Python
    all_alerts = RiskAlert.objects.filter(is_active=True)
    alerts = [a for a in all_alerts if not a.affected_establishments or establishment in a.affected_establishments]
    return render(request, 'improvement_cycle/dashboard_ee.html', {
        'goals': goals,
        'alerts': alerts,
        'establishment': establishment,
        'establishments': User.ESTABLISHMENT_CHOICES,
    })


@login_required
def dashboard_red(request):
    """Dashboard consolidado de toda la Red Congregacional."""
    all_goals = ImprovementGoal.objects.all().order_by('establishment', 'deadline')
    all_alerts = RiskAlert.objects.filter(is_active=True).order_by('-triggered_at')
    stats = ImprovementGoal.objects.values('status').annotate(count=Count('id'))
    return render(request, 'improvement_cycle/dashboard_red.html', {
        'all_goals': all_goals,
        'all_alerts': all_alerts,
        'stats': {s['status']: s['count'] for s in stats},
    })


@login_required
def alertas_activas(request):
    alerts = RiskAlert.objects.filter(is_active=True).order_by('-triggered_at')
    return render(request, 'improvement_cycle/alertas.html', {'alerts': alerts})


@login_required
def meta_crear(request):
    if not (request.user.role in ['REPRESENTANTE', 'DIRECTOR', 'UTP'] or request.user.is_staff):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    
    ee_initial = request.GET.get('ee') or request.user.establishment

    if request.method == 'POST':
        ee = request.POST.get('establishment')
        target_val_str = request.POST.get('target_value', '0')
        target_val = float(target_val_str) if target_val_str.strip() else 0.0
        
        goal = ImprovementGoal.objects.create(
            establishment=ee,
            profile_role=request.POST.get('profile_role', ''),
            subvention_type=request.POST.get('subvention_type', 'SEP'),
            title=request.POST.get('title', ''),
            description=request.POST.get('description', ''),
            target_value=target_val,
            measurement_unit=request.POST.get('measurement_unit', ''),
            deadline=request.POST.get('deadline'),
            created_by=request.user,
        )
        return redirect(f'/mejora/?ee={ee}')
    return render(request, 'improvement_cycle/meta_form.html', {
        'establishments': User.ESTABLISHMENT_CHOICES,
        'roles': User.ROLE_CHOICES,
        'ee_initial': ee_initial,
        'initial_title': request.GET.get('title', ''),
        'initial_description': request.GET.get('description', ''),
    })


@login_required
def goal_detail(request, pk):
    goal = get_object_or_404(ImprovementGoal, pk=pk)
    actions = goal.actions.all()
    can_edit = request.user.role in ['REPRESENTANTE', 'DIRECTOR', 'UTP'] or request.user.is_staff or request.user == goal.created_by
    
    return render(request, 'improvement_cycle/goal_detail.html', {
        'goal': goal,
        'actions': actions,
        'can_edit': can_edit,
    })


@login_required
def action_create(request, goal_pk):
    goal = get_object_or_404(ImprovementGoal, pk=goal_pk)
    if not (request.user.role in ['REPRESENTANTE', 'DIRECTOR', 'UTP'] or request.user.is_staff or request.user == goal.created_by):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()

    if request.method == 'POST':
        responsible_id = request.POST.get('responsible')
        responsible = User.objects.get(id=responsible_id) if responsible_id else None
        
        ImprovementAction.objects.create(
            goal=goal,
            responsible=responsible,
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            evidence=request.POST.get('evidence', ''),
            deadline=request.POST.get('deadline'),
            weight=float(request.POST.get('weight', 1)),
            status='pendiente'
        )
        messages.success(request, "Acción creada correctamente.")
        return redirect('improvement_cycle:goal_detail', pk=goal.pk)

    users = User.objects.filter(establishment=goal.establishment, is_active=True)
    return render(request, 'improvement_cycle/action_form.html', {
        'goal': goal,
        'users': users,
    })


@login_required
def action_toggle(request, pk):
    action = get_object_or_404(ImprovementAction, pk=pk)
    if not (request.user == action.responsible or request.user == action.goal.created_by or request.user.is_staff):
        messages.error(request, "No tienes permiso para cambiar el estado de esta acción.")
        return redirect('improvement_cycle:goal_detail', pk=action.goal.pk)
    
    if action.status == 'completado':
        action.status = 'pendiente'
    else:
        action.status = 'completado'
    action.save()
    
    messages.success(request, f"Estado de '{action.title}' actualizado.")
    return redirect('improvement_cycle:goal_detail', pk=action.goal.pk)
