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

Consolidación total de 5 asistentes exclusivos para **Temuco** con motor RAG y protocolo institucional.

### Agentes Configurados (Exclusivo Temuco)
| slug | Rol | Dominio Principal |
|------|-----|-------------------|
| `director-temuco` | DIRECTOR | Coordinación, Liderazgo, Matriz Eisenhower |
| `utp-temuco` | UTP | Curricular, Pedagógico, Decreto 67/83/170 |
| `representante-temuco` | REPRESENTANTE | Legal, Contratos, Recursos SEP/PIE, Ley 21809 |
| `inspector-temuco` | INSPECTOR | RIOHS personal, Estatuto Docente, Sumarios |
| `convivencia-temuco` | CONVIVENCIA | RICE, Ley 20536, Política Nacional de Convivencia |

### Capacidades Implementadas
- ✅ **Motor RAG**: Inyección de contexto normativo (23.7k+ chunks) en DeepSeek.
- ✅ **Protocolo Institucional**: Jerarquía de roles, Regla de Derivación y Blindaje Legal (San Francisco de Asís).
- ✅ **Formato Universal**: Sustento + Plan (Preventivo/Formativo/Reparatorio) + Checklist Obligatorio.
- ✅ **Auto-Case**: Generación automática de casos y descargos desde el chat.
- ✅ **Acceso Global**: Redirección inteligente por rol en `ai_list`.
- ✅ **Limpieza de DB**: Eliminación definitiva de asistentes "fantasma" y genéricos mediante migración de datos.

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
- [x] **Consolidación Temuco**: Eliminados todos los asistentes que no pertenecían a la sede Temuco.
- [x] **Restauración de Prompts**: Recuperado el prompt detallado ("spectacular tips") para el asistente `director-general` y añadido como migración persistente.
- [x] **Protocolo Global IA**: Integrado el Protocolo Institucional estricto (Regla de Derivación, Enfoque Triple y Blindaje Legal) a todos los asistentes.
- [x] **Acceso Director.Admin**: Normalizado el acceso de `director.admin` (removido staff) mediante migración de datos (`0020`) para asegurar persistencia en producción (Railway).
- [ ] **Migración a PostgreSQL**: Configurar base de datos relacional robusta en Railway para reemplazar SQLite.
- [ ] **Litestream (Opcional)**: Si se mantiene SQLite, implementar replicación a R2.
- [ ] **Test Pipeline**: Realizar una prueba completa de videollamada -> grabación -> procesamiento -> IA -> R2.
- [ ] **Carga de Documentos**: Indexar `PME` faltante en la Knowledge Base (El `RICE` y el `RIOHS` ya se encuentran indexados).

### Interfaz y UX
- [x] **Botones de Descarga PDF**: Implementar botones de descarga para Acta, Acuerdos y Lista de Participantes con estados de "En proceso..." mientras la IA trabaja.
- [x] **Ciclo de Mejora Dinámico**: Implementada la carga de múltiples objetivos estratégicos y opción "No corresponde" en subvenciones.
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