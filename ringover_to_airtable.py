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

# Fonction pour récupérer les ID des appels déjà enregistrés dans Airtable
def get_existing_call_ids():
    print("📥 Récupération des appels déjà enregistrés dans Airtable...")
    existing_ids = set()
    records = airtable.get_all(fields=["ID Appel"])
    for record in records:
        existing_ids.add(record['fields'].get("ID Appel"))
    print(f"🔍 {len(existing_ids)} appels déjà présents dans Airtable.")
    return existing_ids

# Récupération des appels depuis Ringover
def get_ringover_calls():
    url = "https://public-api.ringover.com/v2/calls"
    headers = {
        "Authorization": f"Bearer {RINGOVER_API_KEY}",
        "Content-Type": "application/json"
    }
    calls = []
    offset = 0
    limit = 50

    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    start_date_iso = start_date.isoformat() + "Z"
    end_date_iso = end_date.isoformat() + "Z"
    print(f"🔍 Recherche des appels entre {start_date_iso} et {end_date_iso}")

    payload = {
        "start_date": start_date_iso,
        "end_date": end_date_iso,
        "limit_count": limit,
        "limit_offset": offset
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        calls = data.get("call_list", [])
    else:
        print(f"❌ Erreur Ringover API: {response.status_code}")

    print(f"✓ Récupération de {len(calls)} appels terminée")
    return calls

# Envoi des nouveaux appels à Airtable
def send_to_airtable(calls, existing_call_ids):
    count = 0
    print(f"🔄 Envoi de {len(calls)} nouveaux appels vers Airtable...")

    for i, call in enumerate(calls):
        call_id = str(call.get("call_id"))
        if call_id in existing_call_ids:
            print(f"⏩ Appel {call_id} déjà présent dans Airtable, ignoré.")
            continue

        record = {
            "ID Appel": call_id,
            "Date": call.get("start_time"),
            "Durée (s)": call.get("total_duration"),
            "Numéro Source": call.get("from_number"),
            "Numéro Destination": call.get("to_number"),
            "Type d'appel": call.get("type"),
            "Statut": call.get("last_state"),
        }

        airtable.insert(record)
        count += 1
        time.sleep(0.2)
    return count

# Exécution
if __name__ == "__main__":
    print("🚀 Démarrage de la synchronisation Ringover → Airtable...")
    existing_call_ids = get_existing_call_ids()
    calls = get_ringover_calls()
    
    if calls:
        nbr_synchronisés = send_to_airtable(calls, existing_call_ids)
        print(f"✅ Synchronisation terminée. {nbr_synchronisés}/{len(calls)} nouveaux appels ajoutés.")
    else:
        print("⚠️ Aucun appel à synchroniser.")
