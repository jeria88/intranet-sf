import os
import requests
from django.conf import settings
import django
from dotenv import load_dotenv

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def check():
    api_key = os.environ.get('DAILY_API_KEY')
    if not api_key:
        print("❌ Error: DAILY_API_KEY no encontrada.")
        return

    url = "https://api.daily.co/v1/recordings"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            recordings = response.json().get('data', [])
            if recordings:
                first = recordings[0]
                rec_id = first.get('id')
                print(f"✅ Grabación encontrada: {rec_id}")
                
                # Probar obtener Access Link
                access_url = f"https://api.daily.co/v1/recordings/{rec_id}/access-link"
                acc_resp = requests.get(access_url, headers=headers)
                if acc_resp.status_code == 200:
                    print(f"🔗 Access Link: {acc_resp.json().get('download_url')}")
                else:
                    print(f"❌ Error Access Link: {acc_resp.status_code} - {acc_resp.text}")
            else:
                print("📭 No hay grabaciones.")
    except Exception as e:
        print(f"❌ Excepción: {e}")

if __name__ == "__main__":
    check()
