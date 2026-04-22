# PROGRESS.md — Guía de continuación para cualquier IA

> **Actualizado:** 2026-04-21 · Commit: `19eb392`
> Leer esto ANTES de hacer cualquier cambio al código.

---

## Objetivo General

Intranet escolar chilena (Red SFA) desplegada en **Railway** + **GitHub Actions**.
Stack: **Django 6 / Python 3.11 / SQLite / Daily.co / OpenAI Whisper / DeepSeek**.
Restricción crítica: servidor <4 GB RAM → todo procesamiento pesado va a GitHub Actions.

---

## Arquitectura del Pipeline de Reuniones (COMPLETADA ✅)

```
Usuario agenda reunión (booking_crear)
       ↓
Django crea: MeetingBooking + CalendarEvent + ImprovementGoal (con IA)
       ↓
Participante entra a sala Daily.co
       ↓
Daily dispara webhook → "meeting-started" → Django inicia grabación via API (async thread)
       ↓
Reunión termina → Daily dispara → "recording.ready-to-download"
       ↓
Django: booking.processing_status = 'pendiente', guarda recording_url + recording_id
       ↓
GitHub Actions (cron 15 min) → consulta /meetings/api/pending/
       ↓
Descarga video → pydub chunks 10 min → detección silencio (dBFS < -40) → Whisper
       ↓
DeepSeek → genera Acta + Acuerdos → Daily API → Lista participantes reales
       ↓
Django: actualiza booking (completado) + ImprovementGoal actions marcadas completadas
```

---

## Estado Actual de los Módulos

### `meetings/` — Módulo de Videollamadas ✅ OPTIMIZADO

| Archivo | Estado | Notas |
|---------|--------|-------|
| `models.py` | ✅ | `processing_status` default = `'sin_grabacion'` (no `'pendiente'`) |
| `views.py` | ✅ | Sin N+1 queries; webhook meeting-started usa threading; recording_id se guarda en sync |
| `admin.py` | ✅ | search_fields, inlines, fieldsets, MeetingParticipant registrado |
| `urls.py` | ✅ | Webhook con y sin trailing slash |
| `templates/meeting_list.html` | ✅ | Calendario dinámico desde BD; cards usan `_room_card.html` |
| `templates/_room_card.html` | ✅ | Partial nuevo, elimina duplicación |
| `management/commands/register_daily_webhook.py` | ✅ | Registra webhook al hacer deploy |
| `migrations/0007_...py` | ✅ | Migración para nuevo default + choice |

### `scripts/process_recordings.py` ✅ OPTIMIZADO

- Detección de silencio: chunks con `dBFS < -40` se saltan (ahorra costo Whisper)
- Logging detallado con progreso de chunks
- `temperature=0.3` en DeepSeek para documentos formales
- System prompt específico para establecimientos educacionales chilenos

### `.github/workflows/process_recordings.yml` ✅ OPTIMIZADO

- Early-exit: verifica pendientes ANTES de instalar ffmpeg/pip (ahorra ~60s si no hay trabajo)
- Máximo 10 reuniones por ciclo de procesamiento

---

## Flujo de Estados de `MeetingBooking.processing_status`

```
sin_grabacion → (webhook recording.ready-to-download) → pendiente
pendiente     → (GH Actions api_start_processing)     → procesando
procesando    → (GH Actions api_update_meeting OK)    → completado
procesando    → (GH Actions api_update_meeting fail)  → fallido
fallido       → (reintento automático en próximo cron) → procesando
```

---

## Configuración de Secretos Requeridos

### Railway (variables de entorno)
- `DAILY_API_KEY` — API key de Daily.co
- `DAILY_BASE_URL` — `https://intranet-sfa.daily.co/`
- `INTERNAL_API_KEY` — clave compartida entre Django y GitHub Actions

### GitHub Actions Secrets
- `DJANGO_API_URL` — `https://web-production-2b719.up.railway.app/meetings/api`
- `INTERNAL_API_KEY` — mismo valor que en Railway
- `DAILY_API_KEY` — mismo que en Railway
- `OPENAI_API_KEY` — para Whisper
- `DEEPSEEK_API_KEY` — para generación de acta/acuerdos
- `DEEPSEEK_BASE_URL` — (opcional) default: `https://api.deepseek.com`

---

## Salas Daily.co Configuradas

Nombres en `daily_identifier` (= nombre en Daily): `angol`, `arauco`, `imperial`,
`lautaro`, `ercilla`, `santiago`, `renaico`, `temuco`, `utp`, `director`,
`inspector`, `convivenciaescolar`.

La URL del webhook es:
`https://web-production-2b719.up.railway.app/salas/webhook/recording/`

El webhook se re-registra automáticamente en cada deploy via `Procfile`:
```
web: python manage.py register_daily_webhook && gunicorn config.wsgi ...
```

---

## Tareas Pendientes (Próximas sesiones)

- [ ] **Probar el pipeline end-to-end** con una reunión real: entrar a sala → salir → esperar 15 min → verificar que GH Actions procesó y subió acta al intranet.
- [ ] **Notificaciones**: cuando `processing_status` cambia a `completado`, notificar al `booked_by` por correo o notificación interna.
- [ ] **Dashboard de estadísticas**: en `recording_list.html`, mostrar procesamiento_status con badges de color (actualmente solo muestra grabaciones sin estado).
- [ ] **Consolidar asistencia**: `MeetingAttendance` (quien entró por el intranet) vs `MeetingParticipant` (quien detectó Daily) — actualmente son dos secciones separadas en `booking_detalle.html`.
- [ ] **Prueba de silencio**: verificar que el threshold de -40 dBFS es correcto para reuniones escolares (puede necesitar ajuste a -35 dBFS si hay ruido de fondo leve).

---

## Módulos Relacionados (No tocar sin contexto)

### `improvement_cycle/`
- `ImprovementGoal` — tiene FK `associated_booking` → `MeetingBooking`
- `is_meeting_cycle=True` marca los ciclos generados automáticamente desde reuniones
- Al completar una reunión, `api_update_meeting` marca acciones como completadas

### `calendar_red/`
- `CalendarEvent` tiene `OneToOne` → `MeetingBooking.calendar_event`
- Se crea automáticamente en `booking_crear`

---

## Commits Recientes Relevantes

| Hash | Descripción |
|------|-------------|
| `19eb392` | Optimize meetings: N+1 fix, silence detection, async webhook, DRY templates |
| `5987e1e` | Auto-recording via meeting-started webhook + meeting-ended handler |
| `2d031dd` | (anterior) Webhook registration management command |
