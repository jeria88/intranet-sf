import os
import requests
import json
import tempfile
from pydub import AudioSegment
from openai import OpenAI

# Configuración desde variables de entorno (Secretos de GitHub)
DJANGO_API_URL = os.environ.get('DJANGO_API_URL')  # Ej: https://tudominio.railway.app/meetings/api
INTERNAL_API_KEY = os.environ.get('INTERNAL_API_KEY')
DAILY_API_KEY = os.environ.get('DAILY_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

# Umbral de silencio: chunks más silenciosos que esto se omiten (evita costos innecesarios en Whisper)
SILENCE_THRESHOLD_DBFS = -40  # dB

client_openai = OpenAI(api_key=OPENAI_API_KEY)


def get_headers():
    return {
        "X-Internal-API-Key": INTERNAL_API_KEY,
        "Content-Type": "application/json"
    }


def process_all_pending():
    print("🔍 Buscando reuniones pendientes...")
    try:
        res = requests.get(f"{DJANGO_API_URL}/pending/", headers=get_headers())
        if res.status_code != 200:
            print(f"❌ Error al obtener pendientes: {res.status_code}")
            return

        meetings = res.json().get('meetings', [])
        print(f"Found {len(meetings)} meetings to process.")

        for m in meetings:
            process_meeting(m)

    except Exception as e:
        print(f"❌ Error crítico: {e}")


def process_meeting(m):
    booking_id = m['id']
    download_url = m['recording_url']
    recording_id = m['recording_id']
    room_name = m['room_name']

    print(f"\n{'='*50}")
    print(f"  Procesando Reunión ID {booking_id} — Sala: {room_name}")
    print(f"{'='*50}")

    # 1. Marcar como iniciado (evita que otro worker tome el mismo registro)
    requests.post(f"{DJANGO_API_URL}/start/{booking_id}/", headers=get_headers())

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 2. Resolver URL de descarga (soporta 'daily_id:' markers)
            print("📥 Descargando audio...")
            audio_path = os.path.join(tmpdir, "recording.mp4")
            final_download_url = download_url

            if download_url.startswith('daily_id:'):
                daily_id = download_url.replace('daily_id:', '')
                print(f"   Obteniendo enlace fresco para Daily ID: {daily_id}")
                access_url = f"https://api.daily.co/v1/recordings/{daily_id}/access-link"
                headers_daily = {"Authorization": f"Bearer {DAILY_API_KEY}"}
                acc_res = requests.get(access_url, headers=headers_daily, timeout=10)
                if acc_res.status_code == 200:
                    final_download_url = acc_res.json().get('download_link')
                    print(f"   ✅ Enlace obtenido correctamente.")
                else:
                    raise Exception(f"Could not get access link: {acc_res.status_code} — {acc_res.text[:80]}")

            resp = requests.get(final_download_url, stream=True, timeout=120)
            resp.raise_for_status()
            total_bytes = 0
            with open(audio_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    total_bytes += len(chunk)
            print(f"   Descargados {total_bytes / 1024 / 1024:.1f} MB")

            # 3. Transcribir con Whisper (chunking + detección de silencio)
            print("🎙️ Transcribiendo con Whisper...")
            transcript = transcribe_audio(audio_path, tmpdir)

            if not transcript.strip():
                print("   ⚠️ Transcripción vacía — la grabación no tiene audio detectable.")
                # Igual completamos para no reintentarlo indefinidamente
                requests.post(
                    f"{DJANGO_API_URL}/update/{booking_id}/",
                    headers=get_headers(),
                    json={"transcript": "", "acta": "Sin contenido de audio.", "acuerdos_text": "", "status": "completed"}
                )
                return

            # 4. Acta y Acuerdos con DeepSeek
            print("🤖 Generando acta con DeepSeek...")
            acta = generate_ai_content(
                transcript,
                "Redacta un acta formal de esta reunión escolar chilena. "
                "Incluye: fecha inferida, participantes mencionados, puntos tratados, y conclusiones."
            )

            print("📋 Extrayendo acuerdos...")
            acuerdos = generate_ai_content(
                transcript,
                "Extrae los acuerdos y compromisos de esta reunión como una lista numerada. "
                "Para cada acuerdo indica: descripción, responsable (si se menciona), y plazo (si se indica)."
            )

            # 5. Obtener participantes de Daily
            print("👥 Obteniendo participantes de Daily...")
            participants = fetch_daily_participants(recording_id)
            print(f"   {len(participants)} participante(s) detectado(s).")

            # 6. Enviar resultados a Django
            print("🚀 Enviando resultados al servidor...")
            payload = {
                "transcript": transcript,
                "acta": acta,
                "acuerdos_text": acuerdos,
                "participants": participants,
                "status": "completed"
            }
            res = requests.post(
                f"{DJANGO_API_URL}/update/{booking_id}/",
                headers=get_headers(),
                json=payload,
                timeout=30
            )
            print(f"   ✅ Completado! Status: {res.status_code}")

    except Exception as e:
        print(f"❌ Error en reunión {booking_id}: {e}")
        requests.post(
            f"{DJANGO_API_URL}/update/{booking_id}/",
            headers=get_headers(),
            json={"status": "failed"}
        )


def transcribe_audio(path, tmpdir):
    """
    Divide el audio en chunks de 10 minutos y transcribe cada uno.
    Los chunks silenciosos (dBFS < SILENCE_THRESHOLD_DBFS) se omiten
    para ahorrar costos en la API de Whisper.
    """
    audio = AudioSegment.from_file(path)
    ten_minutes = 10 * 60 * 1000
    chunks = [audio[i:i + ten_minutes] for i in range(0, len(audio), ten_minutes)]
    total = len(chunks)
    print(f"   Audio dividido en {total} chunk(s) de 10 min.")

    texts = []
    for i, chunk in enumerate(chunks):
        # Detección de silencio — omite chunks sin audio útil
        if chunk.dBFS < SILENCE_THRESHOLD_DBFS:
            print(f"   Chunk {i+1}/{total}: silencioso (dBFS={chunk.dBFS:.1f} < {SILENCE_THRESHOLD_DBFS}), omitiendo.")
            continue

        c_path = os.path.join(tmpdir, f"chunk_{i}.mp3")
        chunk.export(c_path, format="mp3")
        with open(c_path, "rb") as f:
            res = client_openai.audio.transcriptions.create(model="whisper-1", file=f)
            texts.append(res.text)
            print(f"   Chunk {i+1}/{total}: ✅ transcrito ({len(res.text)} chars)")

    return " ".join(texts)


def generate_ai_content(transcript, prompt):
    """Genera contenido con DeepSeek dado un prompt y la transcripción."""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
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
            {
                "role": "user",
                "content": f"{prompt}\n\nTranscripción:\n{transcript}"
            }
        ],
        "temperature": 0.3  # Más determinístico para documentos formales
    }
    res = requests.post(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=120
    )
    if res.status_code == 200:
        return res.json()['choices'][0]['message']['content']
    return f"Error IA: {res.status_code} — {res.text[:200]}"


def fetch_daily_participants(recording_id):
    """
    Consulta la API de Daily.co para obtener los participantes reales de la sesión.
    """
    if not recording_id or not DAILY_API_KEY:
        return []

    headers = {"Authorization": f"Bearer {DAILY_API_KEY}"}

    try:
        # 1. Obtener detalles de la grabación para encontrar el session_id
        rec_url = f"https://api.daily.co/v1/recordings/{recording_id}"
        res = requests.get(rec_url, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"   ⚠️ No se pudo obtener info de grabación {recording_id}: {res.status_code}")
            return []

        session_id = res.json().get('session_id')
        if not session_id:
            print(f"   ⚠️ No se encontró session_id para la grabación {recording_id}")
            return []

        # 2. Obtener presencia de la sesión (quién estuvo y cuánto tiempo)
        pres_url = f"https://api.daily.co/v1/sessions/{session_id}/presence"
        res = requests.get(pres_url, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"   ⚠️ No se pudo obtener presencia de sesión {session_id}: {res.status_code}")
            return []

        participants = []
        for p in res.json().get('data', []):
            participants.append({
                "name": p.get('user_name') or p.get('user_id') or "Participante Anónimo",
                "joined_at": p.get('join_time'),
                "left_at": p.get('leave_time'),
                "duration_seconds": p.get('duration', 0)
            })
        return participants

    except Exception as e:
        print(f"   ❌ Error al consultar participantes en Daily: {e}")
        return []


if __name__ == "__main__":
    process_all_pending()
