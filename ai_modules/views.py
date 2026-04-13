from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from .models import AIAssistant, AIQuery, AIChatMessage, AICase
from notifications.models import Notification
from .forms import AIQueryForm
from .services import call_deepseek_ai
from django.http import JsonResponse


@login_required
def ai_list(request):
    """Redirige automáticamente según el rol y establecimiento del usuario."""
    # 1. Admins y Equipo Red ven la lista completa
    if request.user.is_staff or request.user.is_red_team:
        assistants = AIAssistant.objects.filter(is_active=True).order_by('name')
        return render(request, 'ai_modules/ai_list.html', {'assistants': assistants})
    
    # 2. UTP Temuco va directo al chat de DeepSeek
    if request.user.role == 'UTP' and request.user.establishment == 'TEMUCO':
        assistant = AIAssistant.objects.filter(slug='utp-temuco', is_active=True).first()
        if assistant:
            return redirect('ai_modules:ai_chat', slug=assistant.slug)

    # 3. Resto de perfiles van a la vista de NotebookLM
    return redirect('ai_modules:notebooklm_instruction')


@login_required
def notebooklm_instruction(request):
    """Vista de instrucciones para NotebookLM (usuarios no-UTP Temuco)."""
    # Buscamos el asistente que corresponde al rol del usuario para sacar su notebook_url
    assistant = AIAssistant.objects.filter(
        profile_role=request.user.role,
        establishment=request.user.establishment,
        is_active=True
    ).first()
    
    if not assistant:
        # Fallback a asistente por rol genérico
        assistant = AIAssistant.objects.filter(
            profile_role=request.user.role,
            is_active=True
        ).first()

    return render(request, 'ai_modules/notebooklm_instruction.html', {
        'assistant': assistant
    })

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
    
    # Obtener la última respuesta de la IA (para el Canvas)
    last_ai_response = messages.filter(role='assistant').last()
    
    return render(request, 'ai_modules/chat.html', {
        'assistant': assistant,
        'chat_messages': messages,
        'last_ai_response': last_ai_response.content if last_ai_response else None
    })

@login_required
def case_repository(request):
    """Listado de casos guardados."""
    cases = AICase.objects.all().select_related('assistant', 'user')
    # Si no es staff, filtrar solo los suyos (o por establecimiento si prefieres)
    if not request.user.is_staff:
        cases = cases.filter(user=request.user)
    
    return render(request, 'ai_modules/repository.html', {
        'cases': cases
    })


@login_required
def save_as_case(request):
    """AJAX: Guarda contenido como un caso."""
    if request.method == 'POST':
        assistant_slug = request.POST.get('assistant_slug')
        title = request.POST.get('title', 'Caso sin título')
        sustento = request.POST.get('sustento', '')
        ruta = request.POST.get('ruta', '')
        checklist = request.POST.get('checklist', '')
        observations = request.POST.get('observations', '')
        
        assistant = get_object_or_404(AIAssistant, slug=assistant_slug)
        
        case = AICase.objects.create(
            user=request.user,
            assistant=assistant,
            title=title,
            sustento=sustento,
            ruta=ruta,
            checklist=checklist,
            observations=observations
        )
        
        return JsonResponse({'status': 'success', 'case_id': case.id})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def toggle_case_status(request, pk):
    """Cambia el estado del caso."""
    case = get_object_or_404(AICase, pk=pk)
    if not request.user.is_staff and case.user != request.user:
        return JsonResponse({'status': 'error'}, status=403)
        
    case.status = 'cerrado' if case.status == 'abierto' else 'abierto'
    case.save()
    return JsonResponse({'status': 'success', 'new_status': case.get_status_display()})


@login_required
def generate_case_defense(request, pk):
    """Genera redacción de descargos para fiscalizadores externos."""
    case = get_object_or_404(AICase, pk=pk)
    
    prompt = f"""
    Actúa como un experto en normativa educacional chilena. 
    Basado en el siguiente sustento normativo:
    {case.sustento}
    
    Redacta un documento formal de DESCARGOS para ser presentado ante fiscalizadores externos (como la Superintendencia de Educación).
    El tono debe ser técnico, respetuoso y fundamentado legalmente.
    Resalta los puntos clave que demuestran el cumplimiento del establecimiento.
    """
    
    # Usamos el historial vacío para esta petición puntual
    defense_text = call_deepseek_ai(case.assistant, [], prompt)
    
    case.descargos = defense_text
    case.save(update_fields=['descargos'])
    
    return JsonResponse({'status': 'success', 'defense': defense_text})

@login_required
def update_case(request, pk):
    """AJAX: Actualiza un caso existente."""
    case = get_object_or_404(AICase, pk=pk)
    if not request.user.is_staff and case.user != request.user:
        return JsonResponse({'status': 'error', 'message': 'No tienes permiso'}, status=403)
        
    if request.method == 'POST':
        case.title = request.POST.get('title', case.title)
        case.sustento = request.POST.get('sustento', case.sustento)
        case.ruta = request.POST.get('ruta', case.ruta)
        case.checklist = request.POST.get('checklist', case.checklist)
        case.observations = request.POST.get('observations', case.observations)
        case.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
