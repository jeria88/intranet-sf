# PROGRESS.md — Guía de continuación para cualquier IA

> **Actualizado:** 2026-04-21 · Últimos commits: `9856433` (PROGRESS) → `19eb392` (meetings optimize) → `5987e1e` (auto-recording)
> Leer esto ANTES de hacer cualquier cambio al código.

---

## 🏗️ Arquitectura General

Intranet escolar chilena (Red SFA — múltiples establecimientos) desplegada en **Railway** + **GitHub Actions**.
- Stack: **Django / Python 3.11 / SQLite (default) + SQLite knowledge_base (ai_modules) / Daily.co / OpenAI / DeepSeek**
- Restricción crítica: servidor <4 GB RAM → procesamiento pesado va a GitHub Actions
- Roles de usuario: `DIRECTOR`, `UTP`, `INSPECTOR`, `CONVIVENCIA`, `REPRESENTANTE`, `RED` (superusuario de red)
- Establecimientos: `TEMUCO`, `ANGOL`, `ARAUCO`, `IMPERIAL`, `LAUTARO`, `ERCILLA`, `SANTIAGO`, `RENAICO`

---

## ✅ MÓDULO COMPLETADO: Videollamadas (`meetings/`)

Pipeline 100% automático. Ver sección completa abajo.

### Flujo del Pipeline

```
Booking creado → CalendarEvent + ImprovementGoal (IA)
Usuario entra → Daily dispara "meeting-started" → Django inicia grabación (async thread)
Reunión termina → "recording.ready-to-download" → booking.processing_status = 'pendiente'
GitHub Actions (cron 15min) → /api/pending/ → descarga → chunks 10min + detección silencio
→ Whisper (chunks dBFS > -40) → DeepSeek (acta + acuerdos) → Daily (participantes)
→ /api/update/ → booking.processing_status = 'completado' → ImprovementGoal actualizado
```

### Estados `processing_status`
`sin_grabacion` → `pendiente` → `procesando` → `completado` / `fallido`

### Archivos Clave
| Archivo | Nota |
|---------|------|
| `meetings/views.py` | Sin N+1 queries; webhook async; recording_id se guarda en sync |
| `meetings/models.py` | default=`'sin_grabacion'` (migration 0007) |
| `meetings/templates/meetings/_room_card.html` | Partial nuevo (DRY) |
| `scripts/process_recordings.py` | Detección silencio, logging detallado |
| `.github/workflows/process_recordings.yml` | Early-exit si no hay pendientes |
| `meetings/management/commands/register_daily_webhook.py` | Re-registra en deploy |

### Pendientes Menores (Meetings)
- [ ] Probar pipeline end-to-end con reunión real
- [ ] Notificación al `booked_by` cuando `processing_status = completado`
- [ ] Badges de estado en `recording_list.html`
- [ ] Consolidar `MeetingAttendance` vs `MeetingParticipant` en `booking_detalle.html`

---

## 🚧 MÓDULO EN DESARROLLO: Agentes IA (`ai_modules/`)

### Lo que YA existe (NO reescribir)

| Componente | Estado | Descripción |
|------------|--------|-------------|
| `models.py` | ✅ Completo | `AIAssistant`, `AIKnowledgeBase`, `AIQuery`, `AIChatMessage`, `AIKnowledgeChunk`, `AICase`, `CaseObservation` |
| `utils.py` | ✅ Completo | Motor RAG con embeddings OpenAI + numpy, caché binario mmap, similitud coseno, boosting normativo |
| `services.py` | ✅ Completo | `call_deepseek_ai()` — inyecta RAG + historial → DeepSeek |
| `views.py` | ✅ Completo | chat, casos, consultas, repositorio, impresión, descargos |
| `urls.py` | ✅ Completo | Rutas completas |
| Base de conocimiento | ✅ 23.568 chunks indexados con embeddings | Ver documentos listados abajo |
| BD separada | ✅ `knowledge_base` router SQLite separado | `ai_modules/db_routers.py` |
| Cmds admin | ✅ | `setup_utp_temuco.py`, `setup_representante_temuco.py`, `sync_centralized_knowledge.py` |

### Agentes existentes en BD

| slug | Rol | Est. | Chat | System Prompt |
|------|-----|------|------|---------------|
| `utp-temuco` | UTP | TEMUCO | ✅ | ~970 chars — **INCOMPLETO** |
| `representante-temuco` | REPRESENTANTE | TEMUCO | ✅ | ~1916 chars — **INCOMPLETO** |
| `director-temuco` | DIRECTOR | TEMUCO | ✅ | ~1104 chars — **INCOMPLETO** |
| `director` | DIRECTOR | (todos) | ❌ | **VACÍO** |
| `utp` | UTP | (todos) | ❌ | **VACÍO** |
| `inspector` | INSPECTOR | (todos) | ❌ | **VACÍO** |
| `convivencia` | CONVIVENCIA | (todos) | ❌ | **VACÍO** |
| `global-knowledge` | — | — | ❌ | **VACÍO** |

### Documentos ya indexados en la Knowledge Base (23.568 chunks)

**Internacionales:** `DERECHOS HUMANOS.pdf`, `derechos DEL NIÑO.pdf`
**Nacionales:** `constitucion.pdf`, `DFL-1_22-ENE-1997.pdf` (Estatuto Docente), `REGLAMENTO_INTERNO_N_2025.pdf`
**Educación:** `5.-DFL-2_28-NOV-1998.pdf`, `Ley-20370_12-SEP-2009.pdf` (LGE), `Decreto-67_31-DIC-2018.pdf`, `Decreto-83-EXENTO_05-FEB-2015.pdf`, `Decreto-170_21-ABR-2010.pdf`, `MBE-2-1.pdf`, `MBDLE_2015.pdf`, `EID_estandar.pdf`, `Ley-20845_08-JUN-2015.pdf` (LIE), `LEY-20248_01-FEB-2008.pdf` (SEP), `3_-_Manual-de-cuentas-2026.pdf`, `2.-Ley-21809_01-ABR-2026.pdf`, `Ley-21545_10-MAR-2023.pdf` (TEA), `Ley-20536.pdf` (convivencia), `politica-nacional-de-convivencia-educativa-mineduc-2024.pdf`, `REGLAMENTO DE EVALUACIÓN 2025.pdf`
**Internos:** `1.-PEI - TEMUCO.pdf`, `ia-representante-legal.docx`, `ia utp.pdf`, `promt directores-comparativa.pdf`, `promt entrenamiento IA CONVIVENCIA EDUCATIVA.pdf`

**Documentos faltantes en la knowledge base:**
- `RICE` (Reglamento Interno de Convivencia Escolar) — No indexado
- `RIOHS` (Reglamento Interno de Orden, Higiene y Seguridad) — Presente como `REGLAMENTO_INTERNO_N_2025` (verificar si es el mismo)
- `PME` (Plan de Mejoramiento Educativo) — No indexado
- PEI de establecimientos distintos a Temuco — Solo está `1.-PEI - TEMUCO.pdf`

---

## 🎯 TAREA ACTUAL: Completar los 5 Agentes IA

### Especificaciones del usuario (LEER COMPLETO)

Cada agente debe:

1. **Disclaimer inicial y final**: *"La Inteligencia Artificial es un asesor que operacionaliza los procesos en pos de la optimización de los tiempos para promover el análisis y reflexión de los equipos"*
2. **Verificar pertinencia del rol**: si la consulta corresponde → resuelve; si no → aconseja y deriva
3. **Jerarquía documental**: PEI → Normativos → Documentos internos
4. **Plan de acción estructurado**: a) Preventivo b) Formativo c) Reparatorio
5. **Checklist de proceso**
6. **Bienestar superior del estudiante** como prioridad transversal

### Agente 1: DIRECTOR
- **Dominio**: Cualquier consulta (rol coordinador)
- **Misión específica**: Evaluar urgente/importante · Delegar liderazgo · Asegurar monitoreo
- **Marco**: Matrícula Eisenhower + MBDLE + PEI

### Agente 2: UTP
- **Dominio**: Curricular · Pedagógico · Reglamento de Evaluación · PIE
- **Leyes clave**: Decreto 67, 83, 170 · LGE Art. que apliquen · DFL-2 · LIE · SEP
- **Marco**: MBE + MBDLE + PEI

### Agente 3: REPRESENTANTE LEGAL
- **Dominio**: Contratos · Recursos (SEP, PIE) · Fiscalizaciones · Normativa laboral
- **Leyes clave**: Ley 21809 · Manual de Cuentas · Código del Trabajo · Estatuto Docente · DFL-2

### Agente 4: INSPECTOR GENERAL
- **Dominio**: Aplicación del RIOHS al personal
- **Marco**: RIOHS + Código del Trabajo + Estatuto Docente + debida investigación
- **Enfoque**: Proceso sumarial · Medidas disciplinarias · Derechos del funcionario

### Agente 5: CONVIVENCIA ESCOLAR
- **Dominio**: Aplicación del RICE · Debido proceso
- **Marco (en orden)**: urgente/importante → lo inmediato/conflicto → preventivo → formativo → reparatorio
- **Leyes clave**: Ley 20536 · Política Nacional de Convivencia · Protocolo de actuación

### Plan de Implementación

La implementación se hace actualizando los `system_instruction` de los agentes existentes y habilitando `is_chat_enabled=True`. Se usa un **management command** `setup_all_agents.py` para aplicar de forma reproducible.

**Archivos a crear/modificar:**

1. `ai_modules/management/commands/setup_all_agents.py` — **[NUEVO]** Script que actualiza los 5 agentes con sus prompts completos y habilita el chat
2. `ai_modules/views.py` — Ampliar la lógica de redirección en `ai_list()` para cubrir Inspector y Convivencia
3. `ai_modules/templates/ai_modules/chat.html` — Revisar si el disclaimer aparece en la UI

**Orden de trabajo:**
1. Crear `setup_all_agents.py` con los 5 prompts completos
2. Ejecutar: `python manage.py setup_all_agents`
3. Verificar en `ai_list()` que Inspector y Convivencia también van a `ai_chat`
4. Probar cada agente con consultas de prueba representativas de su rol

---

## Módulos Relacionados (No tocar sin contexto)

### `improvement_cycle/`
- `ImprovementGoal` — FK `associated_booking` → `MeetingBooking`
- `is_meeting_cycle=True` marca ciclos generados desde reuniones
- `api_update_meeting` marca acciones como completadas al finalizar el proceso IA

### `calendar_red/`
- `CalendarEvent` tiene `OneToOne` → `MeetingBooking.calendar_event`
- Se crea automáticamente en `booking_crear`

---

## Secretos de Entorno

### Railway
`DAILY_API_KEY`, `DAILY_BASE_URL` (https://intranet-sfa.daily.co/), `INTERNAL_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`

### GitHub Actions
`DJANGO_API_URL` (https://web-production-2b719.up.railway.app/meetings/api), `INTERNAL_API_KEY`, `DAILY_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`

---

## Commits Recientes

| Hash | Descripción |
|------|-------------|
| `9856433` | docs: update PROGRESS.md |
| `19eb392` | perf: optimize meetings module (N+1, silence detection, async webhook, DRY) |
| `5987e1e` | feat: auto-recording via meeting-started webhook |
| `2d031dd` | feat: webhook registration management command |
