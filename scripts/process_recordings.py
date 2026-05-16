import os
import requests
import json
import tempfile
from pydub import AudioSegment
from openai import OpenAI

# Configuración desde variables de entorno (Secretos de GitHub)
DJANGO_API_URL = os.environ.get('DJANGO_API_URL')  # Ej: https://tudominio.railway.app/meetings/api
INTERNAL_API_KEY = os.environ.get('INTERNAL_API_KEY')
DAILY_API_KEY = (os.environ.get('DAILY_API_KEY') or '').strip()
OPENAI_API_KEY = (os.environ.get('OPENAI_API_KEY') or '').strip()
DEEPSEEK_API_KEY = (os.environ.get('DEEPSEEK_API_KEY') or '').strip()
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

# Cloudflare R2 — usando nombres idénticos a settings.py
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL')
CLOUDFLARE_R2_PUBLIC_URL = os.environ.get('CLOUDFLARE_R2_PUBLIC_URL', '')

# Umbral de silencio: chunks más silenciosos que esto se omiten (evita costos innecesarios en Whisper)
SILENCE_THRESHOLD_DBFS = -40  # dB

client_openai = OpenAI(api_key=OPENAI_API_KEY)


def get_headers():
    return {
        "X-Internal-API-Key": INTERNAL_API_KEY,
        "Content-Type": "application/json"
    }


def upload_to_r2(local_path, booking_id):
    """
    Sube el archivo de grabación a Cloudflare R2 y retorna la URL pública permanente.
    Si las credenciales R2 no están configuradas, retorna None sin fallar.
    """
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_ENDPOINT_URL]):
        print("   ⚠️ Variables R2 no configuradas — se omite subida a R2")
        return None

    try:
        import boto3
        from botocore.config import Config

        s3 = boto3.client(
            's3',
            endpoint_url=AWS_S3_ENDPOINT_URL,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4'),
            region_name='auto',
        )

        key = f"recordings/{booking_id}/recording.mp4"
        print(f"   ☁️  Subiendo a R2: {AWS_STORAGE_BUCKET_NAME}/{key}")

        with open(local_path, 'rb') as f:
            s3.upload_fileobj(
                f,
                AWS_STORAGE_BUCKET_NAME,
                key,
                ExtraArgs={'ContentType': 'video/mp4'},
            )

        # Construir URL pública
        base = CLOUDFLARE_R2_PUBLIC_URL.rstrip('/')
        r2_url = f"{base}/{key}" if base else None

        print(f"   ✅ Subido a R2: {r2_url}")
        return r2_url

    except Exception as e:
        print(f"   ❌ Error al subir a R2: {e}")
        return None


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
    attendees = m.get('attendees', [])

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

            # 2b. Subir a Cloudflare R2 para almacenamiento permanente
            print("☁️  Subiendo grabación a Cloudflare R2...")
            r2_url = upload_to_r2(audio_path, booking_id)

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

            # 4. Acta = transcripción verbatim. Resumen con DeepSeek.
            participants_str = ", ".join(attendees) if attendees else "no registrados"
            print(f"👥 Participantes desde Django: {participants_str}")

            # El acta ES la transcripción — contraste con video para identificar hablantes
            acta = transcript

            print("📋 Generando resumen de la reunión...")
            acuerdos = generate_ai_content(
                transcript,
                "Genera un resumen ejecutivo de esta reunión escolar chilena. "
                "Incluye: (1) Temas principales tratados, (2) Decisiones tomadas, "
                "(3) Compromisos y responsables mencionados, (4) Próximos pasos si se mencionan. "
                "Sé conciso y claro. Usa lenguaje formal."
            )

            # 5. Enviar resultados a Django
            print("🚀 Enviando resultados al servidor...")
            participants_payload = [{"name": name} for name in attendees]
            payload = {
                "transcript": transcript,
                "acta": acta,
                "acuerdos_text": acuerdos,
                "participants": participants_payload,
                "status": "completed",
            }
            if r2_url:
                payload["r2_url"] = r2_url
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



if __name__ == "__main__":
    process_all_pending()
