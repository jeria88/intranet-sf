# PROGRESS.md — Guía de continuación para cualquier IA

> **Actualizado:** 2026-04-22 · Últimos commits: `260422` (Cloudflare R2) → `9856433` (AI Agents) → `19eb392` (meetings optimize)
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

Pipeline 100% automático.

### Flujo del Pipeline
```
Booking creado → CalendarEvent + ImprovementGoal (IA)
Usuario entra → Daily dispara "meeting-started" → Django inicia grabación (async thread)
Reunión termina → "recording.ready-to-download" → booking.processing_status = 'pendiente'
GitHub Actions (cron 15min) → /api/pending/ → descarga → chunks 10min + detección silencio
→ Whisper (chunks dBFS > -40) → DeepSeek (acta + acuerdos) → Daily (participantes)
→ /api/update/ → booking.processing_status = 'completado' → ImprovementGoal actualizado
```

### Archivos Clave
| Archivo | Nota |
|---------|------|
| `meetings/views.py` | Sin N+1 queries; webhook async; recording_id se guarda en sync |
| `scripts/process_recordings.py` | Detección silencio, logging detallado |
| `.github/workflows/process_recordings.yml` | Early-exit si no hay pendientes |

---

## ✅ MÓDULO COMPLETADO: Agentes IA (`ai_modules/`)

Estandarización y despliegue de 5 asistentes especializados con motor RAG y acceso por rol.

### Agentes Configurados
| slug | Rol | Dominio Principal |
|------|-----|-------------------|
| `director` | DIRECTOR | Coordinación, Liderazgo, Matriz Eisenhower |
| `utp` | UTP | Curricular, Pedagógico, Decreto 67/83/170 |
| `representante` | REPRESENTANTE | Legal, Contratos, Recursos SEP/PIE, Ley 21809 |
| `inspector` | INSPECTOR | RIOHS personal, Estatuto Docente, Sumarios |
| `convivencia` | CONVIVENCIA | RICE, Ley 20536, Política Nacional de Convivencia |

### Capacidades Implementadas
- ✅ **Motor RAG**: Inyección de contexto normativo (23k+ chunks) en DeepSeek.
- ✅ **Formato Universal**: Sustento + Plan (Preventivo/Formativo/Reparatorio) + Checklist.
- ✅ **Auto-Case**: Generación automática de casos y descargos desde el chat.
- ✅ **Acceso Global**: Redirección inteligente por rol en `ai_list`.

---

## ✅ MÓDULO COMPLETADO: Cloudflare R2 Storage

Migración de archivos multimedia a almacenamiento compatible con S3 para optimizar Railway.

### Configuración
- ✅ **Backend**: `django-storages` + `boto3`.
- ✅ **Endpoint**: Cloudflare R2 (10GB Free Tier).
- ✅ **Seguridad**: URLs firmadas (por defecto en S3Boto3Storage).
- ✅ **Media**: Todos los `FileField` y `ImageField` (grabaciones, actas, perfiles) se suben al bucket.

---

## 🎯 TAREAS PENDIENTES / PRÓXIMOS PASOS

### Estabilización y Optimización
- [ ] **Variables de Entorno**: Actualizar secretos de R2 (`AWS_*`) en los paneles de Railway y GitHub Actions.
- [ ] **Migración a PostgreSQL**: Configurar base de datos relacional robusta en Railway para reemplazar SQLite.
- [ ] **Litestream (Opcional)**: Si se mantiene SQLite, implementar replicación a R2.
- [ ] **Test Pipeline**: Realizar una prueba completa de videollamada -> grabación -> procesamiento -> IA -> R2.
- [ ] **Carga de Documentos**: Indexar `RICE`, `RIOHS` y `PME` faltantes en la Knowledge Base.

### Interfaz y UX
- [ ] **Notificaciones Push**: Avisar al usuario cuando el procesamiento de su reunión termine.
- [ ] **Badges de Estado**: Mejorar visibilidad del estado de procesamiento en la lista de grabaciones.

---

## Secretos de Entorno (Actualizado)

### Railway / GitHub
| Variable | Descripción |
|----------|-------------|
| `DAILY_API_KEY` | Acceso a API de Daily.co |
| `OPENAI_API_KEY` | Embeddings y GPT-4o-mini |
| `DEEPSEEK_API_KEY` | Motor principal de los agentes IA |
| `AWS_ACCESS_KEY_ID` | Cloudflare R2 Key |
| `AWS_SECRET_ACCESS_KEY` | Cloudflare R2 Secret |
| `AWS_STORAGE_BUCKET_NAME` | `intranet-sfa-storage` |
| `AWS_S3_ENDPOINT_URL` | Endpoint de R2 |
| `INTERNAL_API_KEY` | Seguridad para webhooks y API interna |

---

## Commits Recientes

| Hash | Descripción |
|------|-------------|
| `260422` | feat: implement Cloudflare R2 storage for media files |
| `9856433` | feat: finalize and standardize 5 AI agents (Director, UTP, etc) |
| `19eb392` | perf: optimize meetings module (N+1, silence detection) |
| `5987e1e` | feat: auto-recording via meeting-started webhook |