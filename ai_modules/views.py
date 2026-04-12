from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from .models import AIAssistant, AIQuery, AIChatMessage
from notifications.models import Notification
from .forms import AIQueryForm
from .services import call_deepseek_ai
from django.http import JsonResponse


@login_required
def ai_list(request):
    """Muestra el catálogo de asistentes si es staff/Red, o redirige según rol."""
    # Admins y Equipo Red ven todos los asistentes oficiales
    if request.user.is_staff or request.user.is_red_team:
        assistants = AIAssistant.objects.filter(is_active=True).order_by('name')
        return render(request, 'ai_modules/ai_list.html', {'assistants': assistants})
    
    # Usuarios regulares son redirigidos directamente a su asistente asignado
    # Prioridad 1: Rol + Establecimiento (ej: UTP Temuco)
    assistant = AIAssistant.objects.filter(
        profile_role=request.user.role, 
        establishment=request.user.establishment,
        is_active=True
    ).first()
    
    # Prioridad 2: Solo Rol (Asistente genérico)
    if not assistant:
        assistant = AIAssistant.objects.filter(
            profile_role=request.user.role, 
            establishment='', # Genéricos tienen establishment vacío
            is_active=True
        ).first()
    
    if assistant:
        return redirect('ai_modules:ai_detail', slug=assistant.slug)
    
    # Si no tiene un asistente asignado, mostramos página de no acceso
    return render(request, 'ai_modules/no_access.html')

@login_required
def ai_detail(request, slug):
    assistant = get_object_or_404(AIAssistant, slug=slug, is_active=True)
    
    # 3. Verificación de seguridad: solo puede ver su propio asistente o uno de su establecimiento
    if not request.user.is_staff:
        # Si el asistente es de rol distinto, denegar
        if assistant.profile_role != request.user.role:
            return render(request, 'ai_modules/no_access.html')
        
        # Si el asistente es de un establecimiento distinto al del usuario, denegar
        if assistant.establishment and assistant.establishment != request.user.establishment:
            return render(request, 'ai_modules/no_access.html')

    user_queries = AIQuery.objects.filter(
        user=request.user, assistant=assistant
    ).order_by('-submitted_at')[:5]
    return render(request, 'ai_modules/ai_detail.html', {
        'assistant': assistant,
        'user_queries': user_queries,
    })


@login_required
def nueva_consulta(request, slug):
    assistant = get_object_or_404(AIAssistant, slug=slug, is_active=True)
    if request.method == 'POST':
        form = AIQueryForm(request.POST, request.FILES)
        if form.is_valid():
            query = form.save(commit=False)
            query.user = request.user
            query.assistant = assistant
            query.save()
            
            # Generar sugerencia automática de la IA (RAG)
            if assistant.system_instruction or assistant.context_text:
                # El historial para una consulta única es solo la pregunta actual
                history = [{"role": "user", "content": query.question}]
                suggestion = call_deepseek_ai(
                    assistant,
                    history,
                    query.question
                )
                query.ai_suggestion = suggestion
                query.save(update_fields=['ai_suggestion'])
            
            # Notificar a todos los admins (staff)
            from users.models import User
            for admin_user in User.objects.filter(is_staff=True):
                Notification.notify(
                    recipient=admin_user,
                    notification_type='alerta',
                    title=f'Nueva consulta IA de {request.user.get_full_name() or request.user.username}',
                    message=f'Asistente: {assistant.name} — Plazo: {query.deadline:%d/%m/%Y %H:%M}',
                    url=f'/ia/admin/consulta/{query.pk}/',
                )
            return redirect('ai_modules:mis_consultas')
    else:
        form = AIQueryForm()
        
    return render(request, 'ai_modules/nueva_consulta.html', {
        'assistant': assistant,
        'form': form
    })


@login_required
def mis_consultas(request):
    queries = AIQuery.objects.filter(user=request.user).select_related('assistant').order_by('-submitted_at')
    return render(request, 'ai_modules/mis_consultas.html', {'queries': queries})


@login_required
def consulta_detalle(request, pk):
    query = get_object_or_404(AIQuery, pk=pk, user=request.user)
    return render(request, 'ai_modules/consulta_detalle.html', {'query': query})


# ── Admin area ──────────────────────────────────────────────────────────
@staff_member_required
def cola_consultas(request):
    """Panel del admin: cola de consultas ordenadas por deadline."""
    queries = AIQuery.objects.filter(
        status__in=['pendiente', 'en_proceso']
    ).select_related('user', 'assistant').order_by('deadline')
    return render(request, 'ai_modules/cola_consultas.html', {'queries': queries})


@staff_member_required
def responder_consulta(request, pk):
    query = get_object_or_404(AIQuery, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'tomar' and query.status == 'pendiente':
            query.status = 'en_proceso'
            query.save(update_fields=['status'])
        elif action == 'responder':
            answer = request.POST.get('answer', '').strip()
            if answer:
                query.answer = answer
                query.status = 'respondida'
                query.answered_at = timezone.now()
                query.answered_by = request.user
                query.save()
                # Notificar al usuario que su consulta fue respondida
                Notification.notify(
                    recipient=query.user,
                    notification_type='ai_respuesta',
                    title=f'Tu consulta a {query.assistant.name} fue respondida',
                    message='Haz clic para ver la respuesta.',
                    url=f'/ia/mis-consultas/{query.pk}/',
                )
        return redirect('ai_modules:cola_consultas')

    return render(request, 'ai_modules/responder_consulta.html', {'query': query})


@login_required
def ai_chat(request, slug):
    """Vista de chat tipo ChatGPT para asistentes internos."""
    assistant = get_object_or_404(AIAssistant, slug=slug, is_active=True, is_chat_enabled=True)
    
    # Verificación de seguridad básica (UTP y Admin)
    # Si el usuario es de Temuco y el asistente es de Temuco, o es Admin
    is_temuco_user = (request.user.establishment == 'TEMUCO' and request.user.role == 'UTP')
    if not request.user.is_staff and not is_temuco_user:
        return render(request, 'ai_modules/no_access.html')

    if request.method == 'POST':
        import traceback
        try:
            # Opción para limpiar historial
            action = request.POST.get('action')
            if action == 'clear_history':
                AIChatMessage.objects.filter(user=request.user, assistant=assistant).delete()
                return JsonResponse({'status': 'success'})

            user_message = request.POST.get('message', '').strip()
            if not user_message:
                return JsonResponse({'error': 'Mensaje vacío'}, status=400)
            
            # 1. Guardar mensaje del usuario
            AIChatMessage.objects.create(
                user=request.user,
                assistant=assistant,
                role='user',
                content=user_message
            )
            
            # 2. Obtener historial reciente para el contexto
            history_objs = AIChatMessage.objects.filter(
                user=request.user, assistant=assistant
            ).order_by('timestamp')
            
            history = []
            for h in history_objs:
                history.append({'role': h.role, 'content': h.content})
            
            # 3. Llamar a la IA
            ai_response = call_deepseek_ai(
                assistant,
                history,
                user_message
            )
            
            # 4. Guardar respuesta de la IA
            AIChatMessage.objects.create(
                user=request.user,
                assistant=assistant,
                role='assistant',
                content=ai_response
            )
            
            return JsonResponse({
                'response': ai_response,
                'status': 'success'
            })
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error CRITICO en ai_chat: {error_trace}")
            return JsonResponse({
                'response': f'ERROR INTERNO: {str(e)}\n\nDetalle:\n{error_trace}',
                'status': 'success'
            })

    # Para GET: Cargar historial y renderizar template
    messages = AIChatMessage.objects.filter(
        user=request.user, assistant=assistant
    ).order_by('timestamp')
    
    return render(request, 'ai_modules/chat.html', {
        'assistant': assistant,
        'chat_messages': messages
    })
