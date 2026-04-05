# Intranet Congregacional — Railway Edition

Sistema de gobernanza digital para 8 establecimientos educativos de la Congregación Hermanas Terceras Franciscanas.

**Stack:** Django 6.0.2 · PostgreSQL · Railway.app · WhiteNoise · Gunicorn  
**Proyecto:** Franco Jeria Castro · Abril 2026

---

## 🚀 Deploy en Railway

### 1. Crear proyecto en Railway
1. Ir a [railway.app](https://railway.app) y crear un nuevo proyecto
2. Conectar este repositorio GitHub
3. Agregar el **plugin PostgreSQL** desde Railway Dashboard

### 2. Configurar variables de entorno en Railway

```
SECRET_KEY         = <genera uno con: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DJANGO_SETTINGS_MODULE = config.settings_prod
DATABASE_URL       = <Railway lo provee automáticamente>
ALLOWED_HOSTS      = tu-proyecto.railway.app
```

### 3. Comandos de build (configurar en Railway)
```
# Build command:
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate

# Start command:
gunicorn config.wsgi --log-file -
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
│   ├── settings.py       # Dev (SQLite)
│   ├── settings_prod.py  # Producción (PostgreSQL Railway)
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
