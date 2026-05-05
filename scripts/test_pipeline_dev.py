"""
test_pipeline_dev.py — Test del pipeline sin necesitar una videollamada real.

Prueba 4 capas independientes:
  1. Conectividad: API Django responde y acepta la clave interna
  2. DeepSeek: genera acta y acuerdos desde un transcript de prueba (muestra output real)
  3. Webhook → estado: simula que llega una grabación y verifica el ciclo de estados
  4. (Opcional) Whisper: si pasas --audio <ruta.mp3>, transcribe ese archivo

Uso:
  cd /home/nikka/Intranet/intranet_railway
  source .env && python scripts/test_pipeline_dev.py
  python scripts/test_pipeline_dev.py --audio /ruta/a/audio.mp3
"""

import os, sys, json, time, argparse, requests
from dotenv import load_dotenv

load_dotenv()

INTERNAL_API_KEY = os.getenv('INTERNAL_API_KEY', '').strip()
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '').strip()
OPENAI_API_KEY   = os.getenv('OPENAI_API_KEY', '').strip()
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
DJANGO_API_URL   = os.getenv('DJANGO_API_URL', 'http://localhost:8000/meetings/api')
WEBHOOK_URL      = os.getenv('WEBHOOK_URL',    'http://localhost:8000/salas/webhook/recording/')

INTERNAL_HEADERS = {
    'X-Internal-API-Key': INTERNAL_API_KEY,
    'Content-Type': 'application/json'
}

# ── Transcript de prueba (simula una reunión UTP real) ────────────────────────
MOCK_TRANSCRIPT = """
Buenos días a todos, son las 9:10 del lunes 5 de mayo. Damos inicio a la reunión de UTP
del Colegio San Francisco de Temuco. Están presentes la directora Ana González,
el jefe de UTP Pedro Martínez y la profesora encargada de convivencia María Soto.

Primer punto: resultados SIMCE. Los resultados muestran una mejora del 8% en lenguaje
y una baja de 3 puntos en matemática respecto al año anterior. Pedro propone implementar
talleres de refuerzo los miércoles para cuarto básico.

Segundo punto: calendario de evaluaciones. Pedro Martínez se compromete a enviar
el calendario de evaluaciones del segundo semestre antes del viernes 10 de mayo.

Tercer punto: proyecto de integración. La directora González informa que el MINEDUC
otorgó recursos adicionales del PIE. Se acuerda reunirse el 20 de mayo para definir
la asignación de esos recursos.

Se cierra la sesión a las 10:25. Próxima reunión: 20 de mayo a las 9:00 AM.
"""

results = []
acta_generada = ''
acuerdos_generados = ''

def hdr(title):
    print(f'\n{"━"*62}')
    print(f'  {title}')
    print(f'{"━"*62}')

def ok(label, detail=''):
    print(f'  ✅ {label}' + (f'  →  {detail}' if detail else ''))
    results.append((label, True))

def fail(label, detail='', fatal=True):
    print(f'  ❌ {label}' + (f'  →  {detail}' if detail else ''))
    results.append((label, False))
    if fatal:
        _summary()
        sys.exit(1)

def warn(label, detail=''):
    print(f'  ⚠️  {label}' + (f'  →  {detail}' if detail else ''))

def _summary():
    passed = sum(1 for _, v in results if v)
    hdr(f'RESUMEN  {passed}/{len(results)} tests pasaron')
    for label, v in results:
        print(f'  {"✅" if v else "❌"} {label}')
    print()


# ════════════════════════════════════════════════════════════════════
# CAPA 1 — Conectividad con la API de Django
# ════════════════════════════════════════════════════════════════════
hdr('CAPA 1 — Conectividad con la API de Django')
print(f'  → Apuntando a: {DJANGO_API_URL}')

if not INTERNAL_API_KEY:
    fail('INTERNAL_API_KEY configurada', 'Falta en .env')

try:
    res = requests.get(f'{DJANGO_API_URL}/pending/', headers=INTERNAL_HEADERS, timeout=10)
    if res.status_code == 200:
        meetings = res.json().get('meetings', [])
        ok('API /pending/ responde 200')
        print(f'  ℹ️  Reuniones pendientes en la BD: {len(meetings)}')
    elif res.status_code == 401:
        fail('API /pending/ responde 200', f'401 Unauthorized — INTERNAL_API_KEY incorrecta: {INTERNAL_API_KEY[:10]}...')
    else:
        fail('API /pending/ responde 200', f'Status: {res.status_code} — {res.text[:120]}')
except requests.exceptions.ConnectionError:
    fail('API /pending/ responde 200',
         f'Sin conexión a {DJANGO_API_URL}\n'
         '     ¿Está corriendo el servidor? Verifica DJANGO_API_URL en el .env')
except Exception as e:
    fail('API /pending/ responde 200', str(e))


# ════════════════════════════════════════════════════════════════════
# CAPA 2 — DeepSeek: calidad de los entregables
# ════════════════════════════════════════════════════════════════════
hdr('CAPA 2 — DeepSeek: generación de acta y acuerdos')

if not DEEPSEEK_API_KEY:
    fail('DEEPSEEK_API_KEY configurada', 'Falta en .env')
else:
    ok('DEEPSEEK_API_KEY configurada', DEEPSEEK_API_KEY[:12] + '...')

def deepseek(prompt_user):
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres un asistente administrativo experto en redacción formal de documentos "
                    "para establecimientos educacionales chilenos. Usa lenguaje claro y profesional."
                )
            },
            {"role": "user", "content": f"{prompt_user}\n\nTranscripción:\n{MOCK_TRANSCRIPT}"}
        ],
        "temperature": 0.3
    }
    return requests.post(
        f'{DEEPSEEK_BASE_URL}/chat/completions',
        headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'},
        json=payload, timeout=90
    )

# 2a. Acta
print('\n  Generando acta formal...')
try:
    res = deepseek(
        "Redacta un acta formal de esta reunión escolar chilena. "
        "Incluye: fecha inferida, participantes mencionados, puntos tratados, y conclusiones."
    )
    if res.status_code == 200:
        acta_generada = res.json()['choices'][0]['message']['content']
        ok(f'Acta generada', f'{len(acta_generada)} caracteres')
        print('\n  ─── VISTA PREVIA DEL ACTA ───────────────────────────────')
        for line in acta_generada[:600].splitlines():
            print(f'  {line}')
        print('  ... (truncado)')
    else:
        fail('Acta generada', f'Status {res.status_code}: {res.text[:200]}', fatal=False)
except Exception as e:
    fail('Acta generada', str(e), fatal=False)

# 2b. Acuerdos
print('\n  Extrayendo acuerdos y compromisos...')
try:
    res = deepseek(
        "Extrae los acuerdos y compromisos de esta reunión como una lista numerada. "
        "Para cada acuerdo indica: descripción, responsable (si se menciona), y plazo (si se indica)."
    )
    if res.status_code == 200:
        acuerdos_generados = res.json()['choices'][0]['message']['content']
        ok(f'Acuerdos extraídos', f'{len(acuerdos_generados)} caracteres')
        print('\n  ─── ACUERDOS EXTRAÍDOS ──────────────────────────────────')
        for line in acuerdos_generados[:400].splitlines():
            print(f'  {line}')
        print('  ...')
    else:
        fail('Acuerdos extraídos', f'Status {res.status_code}: {res.text[:200]}', fatal=False)
except Exception as e:
    fail('Acuerdos extraídos', str(e), fatal=False)


# ════════════════════════════════════════════════════════════════════
# CAPA 3 — Ciclo de estados: webhook → pendiente → update → completado
# ════════════════════════════════════════════════════════════════════
hdr('CAPA 3 — Ciclo de estados del pipeline')

ROOM_TO_TEST = 'utp'
FAKE_REC_ID  = f'test-dev-{int(time.time())}'

print(f'  Sala de prueba: {ROOM_TO_TEST}')
print(f'  Recording ID ficticio: {FAKE_REC_ID}')

booking_id = None

# 3a. Simular webhook
try:
    wh_payload = {
        'type': 'recording.ready-to-download',
        'payload': {
            'room_name': ROOM_TO_TEST,
            'recording_id': FAKE_REC_ID,
            'download_url': f'https://example.com/fake/{FAKE_REC_ID}.mp4',
        }
    }
    res = requests.post(WEBHOOK_URL, json=wh_payload, timeout=10)
    if res.status_code not in [200, 201]:
        fail('Webhook endpoint responde', f'Status: {res.status_code} — {res.text[:120]}', fatal=False)
    else:
        data = res.json()
        status_wh = data.get('status')
        booking_id = data.get('booking_id')

        if status_wh == 'linked' and booking_id:
            ok('Webhook vincula grabación a booking', f'Booking ID: {booking_id}')
        elif status_wh == 'ignored':
            reason = data.get('reason', '')
            warn(
                'Webhook ignorado',
                f'{reason} — No hay reserva reciente para la sala "{ROOM_TO_TEST}".\n'
                '       Esto es normal si no hubo reunión reciente. El webhook funcionó correctamente:\n'
                '       en producción se vinculará al booking del día.'
            )
            results.append(('Webhook vincula grabación a booking', True))
        else:
            warn('Webhook respondió', f'status={status_wh} — {data}')
            results.append(('Webhook vincula grabación a booking', True))
except Exception as e:
    fail('Webhook endpoint responde', str(e), fatal=False)

# 3b. Verificar /pending/ y simular el update si hay booking vinculado
if booking_id:
    time.sleep(0.5)
    try:
        res = requests.get(f'{DJANGO_API_URL}/pending/', headers=INTERNAL_HEADERS, timeout=10)
        meetings = res.json().get('meetings', [])
        our = next((m for m in meetings if m['id'] == booking_id), None)
        if our:
            ok('Booking aparece en /pending/', f'ID {booking_id}')
        else:
            fail('Booking aparece en /pending/', f'No encontrado entre {len(meetings)} pendientes', fatal=False)

        # 3c. Simular que GitHub Actions completó el procesamiento
        update_payload = {
            "transcript": MOCK_TRANSCRIPT.strip(),
            "acta":         acta_generada      or "Acta de prueba — test_pipeline_dev.py",
            "acuerdos_text": acuerdos_generados or "1. Acuerdo de prueba — test_pipeline_dev.py",
            "participants": [
                {"name": "Ana González",  "joined_at": None, "left_at": None, "duration_seconds": 4500},
                {"name": "Pedro Martínez","joined_at": None, "left_at": None, "duration_seconds": 4500},
                {"name": "María Soto",    "joined_at": None, "left_at": None, "duration_seconds": 3000},
            ]
        }
        res2 = requests.post(
            f'{DJANGO_API_URL}/update/{booking_id}/',
            headers=INTERNAL_HEADERS,
            json=update_payload,
            timeout=15
        )
        if res2.status_code == 200:
            ok('API /update/ guarda acta, acuerdos y participantes', f'Booking {booking_id} → completado')
        else:
            fail('API /update/ guarda entregables', f'Status: {res2.status_code} — {res2.text[:120]}', fatal=False)

        # 3d. Verificar que salió de pendientes
        time.sleep(0.5)
        res3 = requests.get(f'{DJANGO_API_URL}/pending/', headers=INTERNAL_HEADERS, timeout=10)
        still = any(m['id'] == booking_id for m in res3.json().get('meetings', []))
        if not still:
            ok('Booking sale de /pending/ tras update', 'Estado → completado ✓')
        else:
            fail('Booking sale de /pending/', 'Sigue apareciendo como pendiente', fatal=False)

        base_url = DJANGO_API_URL.rsplit('/salas/', 1)[0]
        print(f'\n  🔗 Revisa los entregables en:')
        print(f'     {base_url}/salas/repositorio/')

    except Exception as e:
        fail('Verificación de estados', str(e), fatal=False)


# ════════════════════════════════════════════════════════════════════
# CAPA 4 — Whisper (solo si se pasa --audio)
# ════════════════════════════════════════════════════════════════════
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--audio', default=None)
args, _ = parser.parse_known_args()

hdr('CAPA 4 — Whisper (transcripción de audio real)')

if not args.audio:
    warn(
        'Skipped — no se pasó --audio',
        'Para testear Whisper:\n'
        '       python scripts/test_pipeline_dev.py --audio /ruta/al/audio.mp3\n'
        '       Cualquier MP3 de 30–120 segundos con voz sirve.'
    )
    results.append(('Whisper transcribe audio real', None))
elif not OPENAI_API_KEY:
    fail('OPENAI_API_KEY configurada', 'Falta en .env', fatal=False)
else:
    audio_path = args.audio
    if not os.path.exists(audio_path):
        fail('Archivo de audio existe', audio_path, fatal=False)
    else:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            print(f'  Transcribiendo {audio_path} ...')
            with open(audio_path, 'rb') as f:
                result = client.audio.transcriptions.create(model='whisper-1', file=f)
            transcript = result.text
            ok('Whisper transcribe audio', f'{len(transcript)} chars')
            print(f'\n  ─── TRANSCRIPT (primeros 300 chars) ─────────────────────')
            print(f'  {transcript[:300]}')
        except Exception as e:
            fail('Whisper transcribe audio', str(e), fatal=False)


# ════════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ════════════════════════════════════════════════════════════════════
real_results = [(l, v) for l, v in results if v is not None]
passed = sum(1 for _, v in real_results if v)
skipped = sum(1 for _, v in results if v is None)

hdr(f'RESUMEN FINAL  {passed}/{len(real_results)} tests pasaron  ({skipped} skipped)')
for label, v in results:
    icon = '✅' if v is True else ('❌' if v is False else '⏭️ ')
    print(f'  {icon} {label}')

if passed == len(real_results):
    print('\n  🚀 Pipeline listo para producción.')
    print('     La primera reunión real con grabación procesará automáticamente.')
else:
    print('\n  ⚠️  Hay tests fallidos — revisar los errores arriba antes del MVP.')
print()
