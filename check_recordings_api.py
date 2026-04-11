import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('DAILY_API_KEY')
headers = {"Authorization": f"Bearer {api_key}"}
url = "https://api.daily.co/v1/recordings"

print("🔍 Consultando lista de grabaciones en Daily.co...")
response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    recordings = data.get('data', [])
    print(f"✅ Se encontraron {len(recordings)} grabaciones.")
    
    if recordings:
        # Mostrar el primer objeto para ver su estructura real
        rec = recordings[0]
        rec_id = rec.get('id')
        print(f"\n📄 Estructura del primer objeto de grabación ({rec_id}):")
        print(json.dumps(rec, indent=2))
        
        # Probar endpoint de access-link
        print(f"\n🔗 Probando obtención de link de descarga para {rec_id}...")
        access_url = f"https://api.daily.co/v1/recordings/{rec_id}/access-link"
        access_response = requests.get(access_url, headers=headers)
        
        if access_response.status_code == 200:
            access_data = access_response.json()
            download_url = access_data.get('download_url')
            print(f"✅ Link de descarga obtenido: {download_url[:60]}...")
        else:
            print(f"❌ Error al obtener link: {access_response.status_code} - {access_response.text}")
        
        # Verificar si existe download_url en alguno
        has_download = any('download_url' in r for r in recordings)
        print(f"\n❓ ¿Alguna tiene 'download_url' en la lista original?: {has_download}")
else:
    print(f"❌ Error API: {response.status_code} - {response.text}")
