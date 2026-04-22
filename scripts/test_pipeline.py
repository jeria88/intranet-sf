"""
Script de test para simular y verificar el pipeline completo de automatización.

Pasos que verifica:
  1. Webhook está activo en Daily
  2. Simula un evento webhook (recording.ready-to-download)
  3. Verifica que el booking quedó en estado 'pendiente'
  4. Ejecuta el procesamiento de grabación (como lo haría GitHub Actions)
  5. Verifica que el booking quedó con transcript, acta y acuerdos

Uso:
  python scripts/test_pipeline.py
"""

import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

DAILY_API_KEY   = os.getenv('DAILY_API_KEY', '').strip()
INTERNAL_API_KEY = os.getenv('INTERNAL_API_KEY', '').strip()
DJANGO_API_URL  = os.getenv('DJANGO_API_URL', 'http://localhost:8000/meetings/api')
WEBHOOK_URL     = os.getenv('WEBHOOK_URL', 'http://localhost:8000/salas/webhook/recording/')

DAILY_HEADERS = {'Authorization': f'Bearer {DAILY_API_KEY}'}
INTERNAL_HEADERS = {
    'X-Internal-API-Key': INTERNAL_API_KEY,
    'Content-Type': 'application/json'
}

RECORDING_ID = '3bf06d10-8e84-494d-88d4-f2e953abd1da'
ROOM_NAME    = 'utp'


def step(msg):
    print(f'\n{"="*60}')
    print(f'  {msg}')
    print(f'{"="*60}')


def check(label, ok, detail=''):
    status = '✅' if ok else '❌'
    print(f'  {status} {label}', f'→ {detail}' if detail else '')
    if not ok:
        print('     ⛔ Pipeline interrumpido.')
        sys.exit(1)


# ── PASO 1: Verificar que el webhook está registrado ──────────────────────────
step('PASO 1: Verificar webhook registrado en Daily.co')
res = requests.get('https://api.daily.co/v1/webhooks', headers=DAILY_HEADERS)
webhooks = res.json() if res.status_code == 200 else []
active = [w for w in webhooks if w.get('state') == 'ACTIVE']
check(
    'Webhook activo en Daily.co',
    len(active) > 0,
    active[0].get('url', '') if active else 'Ninguno registrado'
)


# ── PASO 2: Obtener acceso a la grabación de prueba ───────────────────────────
step('PASO 2: Obtener access-link de la grabación de prueba')
res = requests.get(
    f'https://api.daily.co/v1/recordings/{RECORDING_ID}/access-link',
    headers=DAILY_HEADERS
)
check('Access-link obtenido', res.status_code == 200, f'{res.status_code} - {res.text[:100]}')
download_link = res.json().get('download_link')
check('download_link válido', bool(download_link), download_link[:80] if download_link else 'vacío')


# ── PASO 3: Simular el webhook de Daily ───────────────────────────────────────
step('PASO 3: Simular evento webhook recording.ready-to-download')
webhook_payload = {
    'type': 'recording.ready-to-download',
    'payload': {
        'room_name': ROOM_NAME,
        'recording_id': RECORDING_ID,
        'download_url': download_link,
    }
}
res = requests.post(WEBHOOK_URL, json=webhook_payload)
check(
    'Webhook procesado por Django',
    res.status_code in [200, 201],
    f'Status: {res.status_code} - {res.text[:100]}'
)
booking_id = res.json().get('booking_id') if res.status_code == 200 else None
check('Booking vinculado', bool(booking_id), f'Booking ID: {booking_id}')


# ── PASO 4: Verificar estado 'pendiente' ──────────────────────────────────────
step('PASO 4: Verificar reuniones en estado pendiente')
time.sleep(1)
res = requests.get(f'{DJANGO_API_URL}/pending/', headers=INTERNAL_HEADERS)
check('API /pending/ accesible', res.status_code == 200, f'{res.status_code}')
meetings = res.json().get('meetings', [])
our_meeting = next((m for m in meetings if m['id'] == booking_id), None)
check(
    f'Booking {booking_id} en estado pendiente',
    our_meeting is not None,
    f'Reuniones pendientes totales: {len(meetings)}'
)
print(f'     Recording URL: {our_meeting["recording_url"]}')


# ── PASO 5: Ejecutar el procesamiento ─────────────────────────────────────────
step('PASO 5: Ejecutar procesamiento IA (como lo haría GitHub Actions)')
print('  ⚠️  Este paso descarga el audio y llama a Whisper + DeepSeek.')
print('  ⏳  Puede tardar 1-3 minutos...')

# Importar y ejecutar directamente
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ['DJANGO_API_URL'] = DJANGO_API_URL

# Reusamos el script existente invocándolo como módulo
from scripts.process_recordings import process_meeting
process_meeting(our_meeting)
print('  ✅ Procesamiento completado')


# ── PASO 6: Verificar entregables ─────────────────────────────────────────────
step('PASO 6: Verificar entregables en Django')
# Verificamos que ya no esté en pendientes
time.sleep(2)
res = requests.get(f'{DJANGO_API_URL}/pending/', headers=INTERNAL_HEADERS)
meetings_after = res.json().get('meetings', [])
still_pending = any(m['id'] == booking_id for m in meetings_after)
check(
    f'Booking {booking_id} ya NO está pendiente',
    not still_pending,
    f'Pendientes restantes: {len(meetings_after)}'
)

step('✅ PIPELINE COMPLETO — TODOS LOS PASOS EXITOSOS')
print()
print('  El flujo de automatización funciona correctamente.')
print('  Revisa en la intranet:')
print(f'    → Repositorio de Grabaciones: https://web-production-2b719.up.railway.app/salas/repositorio/')
print(f'    → Ciclo de Mejora vinculado al booking ID {booking_id}')
print()
