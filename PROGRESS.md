# PROGRESS.md — Guía de continuación para cualquier IA

> **Actualizado:** 2026-05-11 · Últimos commits: `4c4498e` (nueva arquitectura SIMCE) → `e01e3f5` (fix migración) → `b94ad21` (CRUD biblioteca)
> Leer esto ANTES de hacer cualquier cambio al código.

---

## 🏗️ Arquitectura General

Intranet escolar chilena (Red SFA — múltiples establecimientos) desplegada en **Railway** + **GitHub Actions**.
- Stack: **Django / Python 3.12 / PostgreSQL (Railway) / Cloudflare R2 / Daily.co / OpenAI / DeepSeek**
- Restricción crítica: servidor <4 GB RAM → sin numpy, sin pgvector; embeddings como JSONField
- Roles de usuario: `DIRECTOR`, `UTP`, `INSPECTOR`, `CONVIVENCIA`, `REPRESENTANTE`, `RED` (superusuario de red)
- Establecimientos: `TEMUCO`, `ANGOL`, `ARAUCO`, `IMPERIAL`, `LAUTARO`, `ERCILLA`, `SANTIAGO`, `RENAICO`
- **Demo MVP: 15 de mayo 2026**

---

## 🚧 MÓDULO EN CURSO: SIMCE (`simce/`)

### Arquitectura nueva (migración 0005 — pendiente de aplicar en Railway)

La migración `0005_nueva_arquitectura.py` transforma completamente el módulo:

| Modelo nuevo | Rol |
|---|---|
| `TextoBiblioteca` | Texto independiente, reutilizable en múltiples pruebas |
| `PreguntaBanco` + `AlternativaBanco` | Preguntas reutilizables asociadas a un texto |
| `PruebaTexto` | Junction: Prueba ↔ TextoBiblioteca, con n_nivel1/2/3 por texto |
| `SimceDocumento` + `SimceChunk` | RAG con embeddings en JSONField (puro Python) |

### Flujo admin completo
```
Biblioteca → generar/crear textos → revisar/aprobar textos
→ "Crear test desde biblioteca" → selecciona textos aprobados → configura preguntas por nivel
→ lanzar generación de preguntas → revisión final → aprobar → publicar
```

### Dos modos para estudiantes
- **Modo SIMCE**: form clásico, se entrega todo junto al final
- **Modo Pistas**: AJAX por pregunta, puntaje 4-3-2-0 según intentos

### Archivos clave
| Archivo | Estado |
|---------|--------|
| `simce/models.py` | ✅ Reescrito — nuevos modelos + ESTADO_PRUEBA completo |
| `simce/migrations/0005_nueva_arquitectura.py` | ✅ Incluye SET CONSTRAINTS ALL IMMEDIATE (fix trigger) |
| `simce/generator.py` | ✅ Reescrito — generar_texto_biblioteca, generar_preguntas_banco, poblar_preguntas_prueba_texto |
| `simce/views.py` | ✅ Reescrito — CRUD completo biblioteca + banco + pruebas |
| `simce/urls.py` | ✅ Actualizado con todas las rutas nuevas |
| `simce/rag.py` | ✅ Nuevo — RAG puro Python con cosine similarity |
| `simce/management/commands/index_simce_docs.py` | ✅ Nuevo — indexar PDFs MINEDUC |
| `simce/admin.py` | ✅ Actualizado — TextoBiblioteca, PreguntaBanco |

### Templates nuevos/actualizados
| Template | Estado |
|----------|--------|
| `admin_dashboard.html` | ✅ Botones Biblioteca + Crear test |
| `biblioteca_list.html` | ✅ Listado con filtros + "Crear manual" + "Generar con IA" |
| `biblioteca_texto_detalle.html` | ✅ CRUD inline preguntas + ajustes IA |
| `biblioteca_texto_form.html` | ✅ Nuevo — crear/editar texto manualmente |
| `admin_crear_test.html` | ✅ Nuevo — seleccionar textos de biblioteca |
| `admin_revisar_textos.html` | ✅ Reescrito — revisar textos antes de generar preguntas |
| `admin_revisar.html` | ✅ Adaptado a nueva estructura PruebaTexto |
| `prueba_rendir.html` | ✅ Adaptado a prueba_textos |

### CRUD implementado
- **TextoBiblioteca**: crear manual, editar (form completo), eliminar, aprobar/rechazar, ajuste IA
- **PreguntaBanco**: crear manual (modal), editar (modal pre-cargado con json_script), eliminar, aprobar/rechazar, generar con IA

### Pendiente post-deploy
- [ ] Verificar que migración 0005 se aplica correctamente en Railway (el push ya fue hecho)
- [ ] Correr `python manage.py index_simce_docs` para indexar PDFs MINEDUC en `simce_docs/`
- [ ] Test completo del flujo: biblioteca → crear test → generar preguntas → publicar → rendir

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

---

## ✅ MÓDULO COMPLETADO: Cloudflare R2 Storage

Migración de archivos multimedia a almacenamiento compatible con S3 para optimizar Railway.

---

## 🎯 PRÓXIMOS PASOS

- [ ] Verificar deploy Railway con migración 0005 (puede que requiera un redeploy manual si falla)
- [ ] Test flujo SIMCE completo end-to-end
- [ ] Indexar PDFs MINEDUC para RAG (`python manage.py index_simce_docs`)
- [ ] Notificaciones Push cuando procesamiento de reunión termine
- [ ] Badges de estado en lista de grabaciones
- [ ] Indexar PME faltante en Knowledge Base

---

## Secretos de Entorno

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL Railway (base principal) |
| `KNOWLEDGE_BASE_URL` | Supabase (ai_modules — pausa si inactivo 7 días en plan free) |
| `DAILY_API_KEY` | API Daily.co |
| `OPENAI_API_KEY` | Embeddings text-embedding-3-small |
| `DEEPSEEK_API_KEY` | Motor principal IA (base_url: api.deepseek.com, modelo: deepseek-chat) |
| `AWS_ACCESS_KEY_ID` | Cloudflare R2 |
| `AWS_SECRET_ACCESS_KEY` | Cloudflare R2 |
| `AWS_STORAGE_BUCKET_NAME` | `intranet-sfa-storage` |
| `AWS_S3_ENDPOINT_URL` | Endpoint R2 |
| `INTERNAL_API_KEY` | Seguridad webhooks/API interna |

---

## Commits Recientes

| Hash | Descripción |
|------|-------------|
| `b94ad21` | feat(simce): CRUD completo TextoBiblioteca y PreguntaBanco |
| `e01e3f5` | fix(simce): SET CONSTRAINTS ALL IMMEDIATE antes de ALTER TABLE |
| `4c4498e` | feat(simce): nueva arquitectura — Biblioteca + PreguntaBanco + RAG |
| `d78990e` | fix(simce): recuperación robusta de errores en hilos |
| `22c4565` | feat(simce): flujo en 2 fases — revisión de textos antes de generar preguntas |
