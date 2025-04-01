import requests
import json
from datetime import datetime, timedelta
from airtable import Airtable
import os
from dotenv import load_dotenv
import time

# Charger les variables depuis le fichier .env
load_dotenv()

# Récupération des clés API
RINGOVER_API_KEY = os.getenv("RINGOVER_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")

# Vérification des clés API
if not all([RINGOVER_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME, AIRTABLE_API_KEY]):
    print("❌ Erreur : certaines variables API sont manquantes.")
    exit(1)

# Connexion à Airtable
airtable = Airtable(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME, AIRTABLE_API_KEY)

# Récupération des appels déjà enregistrés dans Airtable
def get_existing_call_ids():
    existing_call_ids = set()
    records = airtable.get_all(fields=["ID Appel"])
    for record in records:
        call_id = record['fields'].get("ID Appel")
        if call_id:
            existing_call_ids.add(call_id)
    return existing_call_ids

# Récupération des appels depuis Ringover
def get_ringover_calls():
    url = "https://public-api.ringover.com/v2/calls"
    headers = {
        "Authorization": f"Bearer {RINGOVER_API_KEY}",
        "Content-Type": "application/json"
    }
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    start_date_iso = start_date.isoformat() + "Z"
    end_date_iso = end_date.isoformat() + "Z"
    
    payload = {
        "start_date": start_date_iso,
        "end_date": end_date_iso,
        "limit_count": 50,
        "limit_offset": 0
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("call_list", [])
    else:
        print(f"❌ Erreur Ringover API: {response.status_code}")
        return []

# Envoi des appels vers Airtable
def send_to_airtable(calls):
    existing_call_ids = get_existing_call_ids()
    count = 0
    for call in calls:
        call_id = str(call.get("call_id"))
        if call_id in existing_call_ids:
            continue
        airtable.insert({"ID Appel": call_id})
        count += 1
        time.sleep(0.2)
    return count

if __name__ == "__main__":
    print("🚀 Démarrage de la synchronisation Ringover → Airtable...")
    calls = get_ringover_calls()
    if calls:
        synced_count = send_to_airtable(calls)
        print(f"✅ Synchronisation terminée. {synced_count}/{len(calls)} appels synchronisés.")
    else:
        print("⚠️ Aucun appel à synchroniser.")
