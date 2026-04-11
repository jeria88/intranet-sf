import os, requests, json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('DAILY_API_KEY')
REC_ID = "3bf06d10-8e84-494d-88d4-f2e953abd1da" # El ID del ejemplo anterior

headers = {"Authorization": f"Bearer {API_KEY}"}
url = f"https://api.daily.co/v1/recordings/{REC_ID}/access-link"

print(f"Checking access-link for {REC_ID}...")
response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
print(f"Body: {json.dumps(response.json(), indent=2)}")
