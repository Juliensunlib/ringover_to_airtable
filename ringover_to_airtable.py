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
    try:
        records = airtable.get_all(fields=["ID Appel"])
        return {record["fields"].get("ID Appel") for record in records if "ID Appel" in record["fields"]}
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des appels existants : {e}")
        return set()

# Récupération des appels depuis Ringover
def get_ringover_calls():
    url = "https://public-api.ringover.com/v2/calls"
    headers = {"Authorization": f"Bearer {RINGOVER_API_KEY}", "Content-Type": "application/json"}
    calls = []
    offset = 0
    limit = 50
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    start_date_iso = start_date.isoformat() + "Z"
    end_date_iso = end_date.isoformat() + "Z"

    print(f"🔍 Recherche des appels entre {start_date_iso} et {end_date_iso}")

    try:
        payload = {"start_date": start_date_iso, "end_date": end_date_iso, "limit_count": 1, "limit_offset": 0}
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            total_calls = data.get("total_call_count", 0)
            print(f"📊 Total des appels disponibles: {total_calls}")
            if total_calls == 0:
                return []
            while offset < total_calls and offset < 9000:
                payload = {"start_date": start_date_iso, "end_date": end_date_iso, "limit_count": limit, "limit_offset": offset}
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    batch_calls = response.json().get("call_list", [])
                    if not batch_calls:
                        break
                    calls.extend(batch_calls)
                    offset += limit
                    time.sleep(0.5)
                else:
                    break
        else:
            print(f"❌ Erreur Ringover API: {response.status_code}")
    except Exception as e:
        print(f"❌ Exception lors de la récupération des appels: {str(e)}")
    print(f"✓ Récupération de {len(calls)} appels terminée")
    return calls

# Envoi des nouveaux appels à Airtable
def send_to_airtable(calls):
    count = 0
    existing_call_ids = get_existing_call_ids()
    print(f"🔄 Envoi de {len(calls)} appels vers Airtable...")
    
    for i, call in enumerate(calls):
        try:
            call_id = str(call.get("call_id", call.get("cdr_id", f"temp_id_{i+1}")))
            if call_id in existing_call_ids:
                print(f"⏩ Appel {call_id} déjà présent dans Airtable, ignoré.")
                continue
            record = {"ID Appel": call_id, "Date": call.get("start_time"), "Durée (s)": call.get("total_duration")}
            airtable.insert(record)
            count += 1
            if (i + 1) % 10 == 0 or i == len(calls) - 1:
                print(f"⏳ {i + 1}/{len(calls)} appels traités...")
            time.sleep(0.2)
        except Exception as e:
            print(f"❌ Erreur lors de l'insertion de l'appel {call_id}: {str(e)}")
    return count

# Exécution
if __name__ == "__main__":
    print("🚀 Démarrage de la synchronisation Ringover → Airtable...")
    calls = get_ringover_calls()
    if calls:
        nbr_synchronisés = send_to_airtable(calls)
        print(f"✅ Synchronisation terminée. {nbr_synchronisés}/{len(calls)} appels synchronisés.")
    else:
        print("⚠️ Aucun appel à synchroniser.")
