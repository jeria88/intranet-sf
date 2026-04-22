import os
import requests
import json
import tempfile
from pydub import AudioSegment
from openai import OpenAI

# Configuración desde variables de entorno (Secretos de GitHub)
DJANGO_API_URL = os.environ.get('DJANGO_API_URL') # Ej: https://tudominio.railway.app/meetings/api
INTERNAL_API_KEY = os.environ.get('INTERNAL_API_KEY')
DAILY_API_KEY = os.environ.get('DAILY_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

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
    
    print(f"--- Procesando Reunión {booking_id} ---")
    
    # 1. Marcar como iniciado
    requests.post(f"{DJANGO_API_URL}/start/{booking_id}/", headers=get_headers())
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 2. Descargar audio
            print("Downloading audio...")
            audio_path = os.path.join(tmpdir, "recording.mp4")
            
            final_download_url = download_url
            if download_url.startswith('daily_id:'):
                daily_id = download_url.replace('daily_id:', '')
                print(f"Fetching fresh access link for Daily ID: {daily_id}")
                access_url = f"https://api.daily.co/v1/recordings/{daily_id}/access-link"
                headers = {"Authorization": f"Bearer {DAILY_API_KEY}"}
                acc_res = requests.get(access_url, headers=headers, timeout=10)
                if acc_res.status_code == 200:
                    final_download_url = acc_res.json().get('download_link')
                else:
                    raise Exception(f"Could not get access link: {acc_res.status_code}")

            resp = requests.get(final_download_url, stream=True)
            with open(audio_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 3. Transcribir con Whisper (Chunking)
            print("Transcribing...")
            transcript = transcribe_audio(audio_path, tmpdir)
            
            # 4. Acta y Acuerdos con DeepSeek
            print("Generating minutes with DeepSeek...")
            acta = generate_ai_content(transcript, "Redacta un acta formal de esta reunión escolar.")
            acuerdos = generate_ai_content(transcript, "Extrae los acuerdos como una lista numerada.")
            
            # 5. Obtener participantes de Daily
            print("Fetching participants from Daily...")
            participants = fetch_daily_participants(recording_id)
            
            # 6. Enviar resultados
            print("Sending results to Django...")
            payload = {
                "transcript": transcript,
                "acta": acta,
                "acuerdos_text": acuerdos,
                "participants": participants,
                "status": "completed"
            }
            res = requests.post(f"{DJANGO_API_URL}/update/{booking_id}/", headers=get_headers(), json=payload)
            print(f"Done! Status: {res.status_code}")

    except Exception as e:
        print(f"❌ Error en reunión {booking_id}: {e}")
        requests.post(f"{DJANGO_API_URL}/update/{booking_id}/", headers=get_headers(), json={"status": "failed"})

def transcribe_audio(path, tmpdir):
    audio = AudioSegment.from_file(path)
    ten_minutes = 10 * 60 * 1000
    chunks = [audio[i:i + ten_minutes] for i in range(0, len(audio), ten_minutes)]
    
    texts = []
    for i, chunk in enumerate(chunks):
        c_path = os.path.join(tmpdir, f"c_{i}.mp3")
        chunk.export(c_path, format="mp3")
        with open(c_path, "rb") as f:
            res = client_openai.audio.transcriptions.create(model="whisper-1", file=f)
            texts.append(res.text)
    return " ".join(texts)

def generate_ai_content(transcript, prompt):
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Eres un asistente administrativo experto."},
            {"role": "user", "content": f"{prompt}\n\nTranscripción: {transcript}"}
        ]
    }
    res = requests.post(f"{DEEPSEEK_BASE_URL}/chat/completions", headers=headers, json=payload)
    if res.status_code == 200:
        return res.json()['choices'][0]['message']['content']
    return f"Error IA: {res.status_code}"

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
            print(f"⚠️ No se pudo obtener info de grabación {recording_id}: {res.status_code}")
            return []
        
        session_id = res.json().get('session_id')
        if not session_id:
            print(f"⚠️ No se encontró session_id para la grabación {recording_id}")
            return []
        
        # 2. Obtener presencia de la sesión (quién estuvo y cuánto tiempo)
        pres_url = f"https://api.daily.co/v1/sessions/{session_id}/presence"
        res = requests.get(pres_url, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"⚠️ No se pudo obtener presencia de sesión {session_id}: {res.status_code}")
            return []
        
        data = res.json()
        participants = []
        # Daily devuelve una lista de presencias por usuario
        for p in data.get('data', []):
            participants.append({
                "name": p.get('user_name') or p.get('user_id') or "Participante Anónimo",
                "joined_at": p.get('join_time'), 
                "left_at": p.get('leave_time'),
                "duration_seconds": p.get('duration', 0)
            })
        return participants
    except Exception as e:
        print(f"❌ Error al consultar participantes en Daily: {e}")
        return []

if __name__ == "__main__":
    process_all_pending()
