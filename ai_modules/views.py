from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from .models import AIAssistant, AIQuery, AIChatMessage, AICase, CaseObservation
from notifications.models import Notification
from .forms import AIQueryForm
from .services import call_deepseek_ai
from django.http import JsonResponse


@login_required
def ai_list(request):
    """Redirige automáticamente según el rol y establecimiento del usuario."""
    # 1. Admins y Equipo Red ven la lista completa
    if request.user.is_staff or getattr(request.user, 'is_red_team', False):
        assistants = AIAssistant.objects.filter(is_active=True).order_by('name')
        return render(request, 'ai_modules/ai_list.html', {'assistants': assistants})
    
    # 2. Excepción para representantes específicos
    if request.user.role == 'REPRESENTANTE' or request.user.username in ['representante.temuco', 'representante.utp']:
        # Buscar el específico primero, si no el general
        assistant = AIAssistant.objects.filter(profile_role='REPRESENTANTE', is_active=True).filter(
            models.Q(establishment=request.user.establishment) | models.Q(establishment='')
        ).first()
        if assistant:
            return redirect('ai_modules:ai_chat', slug=assistant.slug)

    # 3. Redirección dinámica para todos los roles con agente
    allowed_roles = ['DIRECTOR', 'UTP', 'INSPECTOR', 'CONVIVENCIA']
    if request.user.role in allowed_roles:
        # Buscar asistente que coincida con rol y (establecimiento o sin establecimiento)
        from django.db import models
        assistant = AIAssistant.objects.filter(profile_role=request.user.role, is_active=True).filter(
            models.Q(establishment=request.user.establishment) | models.Q(establishment='')
        ).order_by('-establishment').first() # Priorizar el que tiene establecimiento definido
        
        if assistant:
            return redirect('ai_modules:ai_chat', slug=assistant.slug)

    # 4. Resto de perfiles van a la vista de NotebookLM
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
    
    # Verificación de seguridad básica
    has_access = request.user.is_staff or getattr(request.user, 'is_red_team', False)
    if not has_access:
        role_match = (request.user.role == assistant.profile_role)
        establishment_match = True
        if assistant.establishment:
            establishment_match = (request.user.establishment == assistant.establishment)
        
        is_representante_exception = (assistant.profile_role == 'REPRESENTANTE' and request.user.username in ['representante.temuco', 'representante.utp'])
        
        if (role_match and establishment_match) or is_representante_exception:
            has_access = True

    if not has_access:
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
    """Listado de casos guardados con filtrado por actividad."""
    cases = AICase.objects.all().select_related('assistant', 'user').prefetch_related('obs_log__user')
    # Si no es staff, filtrar sus propios casos y solo los ACTIVOS
    if not request.user.is_staff:
        cases = cases.filter(user=request.user, is_active=True)
    
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
        
        # Priorizar query del POST, si no viene, usar lo que sea que ayude a la trazabilidad
        user_query = request.POST.get('query', '').strip()
        if not user_query:
            user_query = f"Consulta automática generada para el caso: {title}"

        case = AICase.objects.create(
            user=request.user,
            assistant=assistant,
            title=title,
            user_query=user_query,
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
    
    import time
    timestamp = int(time.time())
    
    # Prompt técnico y formal con inyección de variabilidad
    system_prompt = f"""
    Actúa como un experto en Normativa Educacional y Gestión Jurídica-Pedagógica de Chile. 
    Tu misión es redactar un documento formal de DESCARGOS para ser presentado ante entes fiscalizadores.
    
    CRITICAL UNIQUE SEED: {case.pk}-{timestamp}
    ESTILO DE REDACCIÓN: Rotar hacia un tono profundamente técnico y personalizado.
    
    INSTRUCCIONES DE VARIABILIDAD:
    1. PROHIBIDO usar frases de plantilla como "en relación a lo consultado" o "se procede a informar".
    2. Inicia el documento directamente con los hechos o la base legal.
    3. Cada oración debe ser construida de forma única para este caso {case.pk}.
    4. Si has redactado algo similar antes, CAMBIA totalmente los conectores y la estructura de los párrafos.
    
    ESTRUCTURA OBLIGATORIA: 
    1. Antecedentes (Hechos específicos del caso)
    2. Fundamentación Técnico-Normativa (Citas legales precisas)
    3. Acciones de Mitigación/Corrección (Pasos realizados)
    4. Conclusión y petitorio.
    """

    user_prompt = f"""
    Genera los descargos institucionales para el siguiente caso:
    ---
    Título del Caso: {case.title}
    Consulta Original (Hechos): {case.user_query}
    Sustento Normativo: {case.sustento}
    Ruta de Acción: {case.ruta}
    ---
    El documento debe estar listo para ser copiado y pegado en una minuta oficial.
    """
    
    # Se debe incluir el user_prompt dentro del messages_history para que la IA lo lea
    messages_for_ai = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt}
    ]
    
    # Usamos temperatura máxima recomendada para redacción variada (1.3)
    defense_text = call_deepseek_ai(case.assistant, messages_for_ai, user_prompt, temperature=1.3)
    
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
        case.status = request.POST.get('status', case.status)
        case.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def add_case_observation(request, pk):
    """AJAX: Añade una observación al log."""
    case = get_object_or_404(AICase, pk=pk)
    if not request.user.is_staff and case.user != request.user:
        return JsonResponse({'status': 'error'}, status=403)
        
    content = request.POST.get('content', '').strip()
    if content:
        obs = CaseObservation.objects.create(
            case=case,
            user=request.user,
            content=content
        )
        return JsonResponse({
            'status': 'success',
            'obs': {
                'user': obs.user.get_full_name() or obs.user.username,
                'content': obs.content,
                'created_at': obs.created_at.strftime('%d/%m/%Y %H:%M')
            }
        })
    return JsonResponse({'status': 'error', 'message': 'Contenido vacío'}, status=400)


@login_required
def case_report_print(request, pk):
    """Vista optimizada para impresión de un caso guardado."""
    case = get_object_or_404(AICase, pk=pk)
    if not request.user.is_staff and case.user != request.user:
        return render(request, 'ai_modules/no_access.html')
    
    return render(request, 'ai_modules/case_report_print.html', {
        'case': case
    })


@login_required
def case_defense_print(request, pk):
    """Vista optimizada para impresión de la DEFENSA (Descargos)."""
    case = get_object_or_404(AICase, pk=pk)
    # Si el caso está inactivo y el usuario no es staff, denegar acceso
    if not case.is_active and not request.user.is_staff:
        return render(request, 'ai_modules/no_access.html')
        
    if not request.user.is_staff and case.user != request.user:
        return render(request, 'ai_modules/no_access.html')
    
    return render(request, 'ai_modules/case_defense_print.html', {
        'case': case
    })


@login_required
def soft_delete_case(request, pk):
    """AJAX: Marca un caso como inactivo (Soft Delete)."""
    case = get_object_or_404(AICase, pk=pk)
    if not request.user.is_staff and case.user != request.user:
        return JsonResponse({'status': 'error', 'message': 'No tienes permiso'}, status=403)
        
    if request.method == 'POST':
        case.is_active = False
        case.save(update_fields=['is_active'])
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
