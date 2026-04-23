# Intranet Congregacional — Railway Edition

Sistema de gobernanza digital para 8 establecimientos educativos de la Congregación Hermanas Terceras Franciscanas.

**Stack:** Django 6.0.2 · PostgreSQL · Railway.app · WhiteNoise · Gunicorn  
**Proyecto:** Desarrollo SFA · Abril 2026

---

## 🚀 Deploy en Railway

### 1. Crear proyecto en Railway
1. Ir a [railway.app](https://railway.app) y crear un nuevo proyecto
2. Conectar este repositorio GitHub
3. Agregar el **plugin PostgreSQL** desde Railway Dashboard

### 2. Configurar variables de entorno en Railway

```
SECRET_KEY         = <genera uno con: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DJANGO_SETTINGS_MODULE = config.settings
DATABASE_URL       = <Railway lo provee automáticamente>
ALLOWED_HOSTS      = tu-proyecto.railway.app
```

### 3. Comandos de build (configurar en Railway)
```
# Build command:
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate

# Start command (en Railway: Settings > Start Command):
python manage.py migrate && python seed_railway.py && gunicorn config.wsgi --log-file -
```

---

## 💻 Desarrollo Local

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar BD local (SQLite por defecto)
python manage.py migrate

# 4. Cargar datos iniciales
python seed_railway.py

# 5. Correr servidor
python manage.py runserver
```

Acceder a: http://127.0.0.1:8000/  
Admin: http://127.0.0.1:8000/admin/ → admin / Admin1234!

---

## 🏗️ Arquitectura

```
intranet_railway/
├── config/               # Configuración Django
│   ├── settings.py       # Configuración unificada (Dev/Prod)
│   ├── urls.py
│   ├── wsgi.py           # Entrypoint Gunicorn
│   └── asgi.py
│
├── users/                # Modelo User (5 roles × 8 establecimientos)
├── portal/               # Dashboard + Circulares
├── meetings/             # Salas Jitsi + Grabaciones + Acuerdos
├── ai_modules/           # Asesores IA por perfil (40 total)
├── library/              # Biblioteca Documental
├── evidencia/            # Formularios de Evaluación
├── messaging/            # Mensajería Interna
├── calendar_red/         # Calendario Estratégico
├── improvement_cycle/    # Metas de Mejora + Alertas de Riesgo
├── notifications/        # Notificaciones Internas
│
├── templates/            # Base template
├── static/               # CSS + Imágenes
├── media/                # Archivos subidos (vacío en repo)
│
├── requirements.txt      # Sin Firebase
├── Procfile              # web: gunicorn config.wsgi
├── runtime.txt           # python-3.12
├── seed_railway.py       # Datos iniciales
└── .env.example          # Variables de entorno documentadas
```

---

## 🎥 Módulo Videollamadas (Daily.co)

Guía para la implementación del sistema de salas dinámicas por Establecimiento y Rol.

### 1. Preparar Rama de Desarrollo
Inicia el trabajo en una rama aislada para este módulo:
```bash
git checkout -b modulo-videollamadas
```

### 2. Configuración en `.env`
Documentar las claves y la base de las salas:
```env
# Daily.co Configuration
DAILY_API_KEY=tu_api_key_aqui
DAILY_DOMAIN=intranet-sfa
```

### 3. Lógica de Salas Identificadas
Las salas seguirán el formato simétrico `https://intranet-sfa.daily.co/{identificador}`.

**Mapeo de URLs:**
- **Por Rol:** `https://intranet-sfa.daily.co/director`, `https://intranet-sfa.daily.co/utp`, etc.
- **Por Establecimiento:** `https://intranet-sfa.daily.co/temuco`, `https://intranet-sfa.daily.co/angol`, etc.

### 4. Flujo Automatizado y Reportes (IA)
1. **Generación de Artefactos**: Al terminar la reunión, la grabación se procesa para generar automáticamente:
   - Acta de la Reunión (DeepSeek)
   - Acuerdos Detectados y Compromisos
   - Lista de Participantes (Validación de Asistencia)
2. **Descarga de PDFs**: Todos estos artefactos pueden ser descargados como documentos PDF listos para imprimir desde el detalle de la reunión. Antes de que el procesamiento termine, la plataforma mostrará un estado de "En proceso...".

### 5. Pasos de Implementación (Próximamente)
1.  **Refactorización de Modelos:** Ajustar `MeetingRoom` en `meetings/models.py` para incluir campos de filtrado por establecimiento y mejorar la validación de roles.
2.  **Lógica de Redirección:** Modificar la vista principal de `meetings` para que detecte el origen del clic (Rol vs Establecimiento) y redirija a la URL de Daily correspondiente.
3.  **Interfaz Dinámica:** Actualizar los botones en el frontend para que solo se muestren las salas permitidas según el contexto del usuario autenticado.

---

## 📋 Carta Gantt (extracto)

| Jornada | Fecha | Módulo |
|---------|-------|--------|
| 1-4 | 02-05 Abr | Infraestructura base + Railway deploy |
| 5-9 | 07-11 Abr | Módulo Videollamadas (Daily.co) |
| 10-13 | 14-17 Abr | Asesores IA (DeepSeek API) |
| 14-17 | 21-24 Abr | Sistematización + Calendario |
| 18-20 | 28-30 Abr | Testing + MVP final |

**Fecha MVP demo:** 15 de mayo 2026

---

## 💰 Costos Mensuales Estimados

| Componente | Costo USD/mes |
|-----------|--------------|
| Railway app + PostgreSQL | ~$7 |
| Daily.co videollamadas | $0-5 |
| Cloudflare R2 (videos 90 días) | ~$3 |
| DeepSeek V4 API (40 asesores) | ~$0.80-1.50 |
| OpenAI Whisper (transcripciones) | ~$3-5 |
| Claude Haiku (actas) | ~$1-2 |
| **Total** | **~$15-24 USD** |

---

## 🔑 Roles del Sistema

| Rol | Descripción |
|-----|-------------|
| `REPRESENTANTE` | Representante Legal Congregacional |
| `DIRECTOR` | Director/a de establecimiento |
| `UTP` | Unidad Técnica Pedagógica |
| `INSPECTOR` | Inspector/a General |
| `CONVIVENCIA` | Encargado/a Convivencia Escolar |
| `RED` | Equipo Red Congregacional (acceso total) |

**Establecimientos:** Temuco · Lautaro · Renaico · Santiago · Imperial · Ercilla · Arauco · Angol

---

## 🧠 Manual de Entrenamiento RAG (DeepSeek)

Este manual describe el flujo para actualizar el conocimiento de los 40 asesores IA (5 roles × 8 establecimientos) utilizando **DeepSeek v4** y documentos **PDF** institucionales.

### 1. Segmentación de Fuentes (PDF)
Para que el entrenamiento coincida con la configuración de la intranet, los documentos deben organizarse por categorías:
- **Nivel Red (Global):** Estatuto Docente, Normas Mineduc, Manuales de Convivencia General.
- **Nivel Establecimiento:** Reglamento Interno (RICE), PME local, protocolos de seguridad específicos.
- **Nivel Rol:** Formatos de planificación (UTP), manuales de liderazgo (Director), actas de mediación (Convivencia).

### 2. Procesamiento del Conocimiento (Embedding)
Para que DeepSeek pueda "leer" los PDFs con precisión:
1. **Extracción:** Convertir PDFs a Markdown para preservar la jerarquía de títulos.
2. **Chunking:** Dividir el texto en bloques de **1000 tokens** con un solapamiento (overlap) de **200 tokens**. Esto evita que la IA pierda el contexto entre páginas.
3. **Indexación:** Generar vectores (embeddings) que se almacenarán en el Vector Store vinculado a la API de DeepSeek.

### 3. Configuración de Identidad (System Prompt)
Cada IA tiene una instrucción base distinta según su `slug` en la base de datos. La estructura del prompt debe ser:
> "Eres el Asistente IA de **[ROL]** del establecimiento **[ESTABLECIMIENTO]**. Tu conocimiento está basado en los documentos adjuntos. Responde siempre con un tono profesional y utiliza los protocolos locales del establecimiento cuando la consulta lo requiera."

### 4. Flujo de Respuesta RAG
1. **Consulta:** El usuario pregunta algo en la intranet.
2. **Búsqueda (Retrieval):** El sistema busca en el Vector Store los 3 bloques de PDF más relevantes.
3. **Aumentación (Augmentation):** Se combinan esos bloques con el *System Prompt* del rol.
4. **Generación:** DeepSeek procesa todo y entrega la respuesta final basada únicamente en el conocimiento institucional.

### 5. Ciclo de Actualización
- **Documentos Normativos:** Actualización inmediata tras publicarse en la Biblioteca Digital.
- **Documentos Operativos:** Sincronización mensual (Metas PME, Acuerdos de Reunión).
