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
    print("\u274c Erreur : certaines variables API sont manquantes.")
    exit(1)

# Connexion à Airtable
airtable = Airtable(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME, AIRTABLE_API_KEY)

# Fonction de traduction des valeurs en français
def traduire_valeurs(call):
    direction_map = {"in": "Entrant", "out": "Sortant"}
    type_appel_map = {"IVR": "SVI", "PHONE": "Téléphone"}

    call["direction"] = direction_map.get(call.get("direction"), call.get("direction"))
    call["type"] = type_appel_map.get(call.get("type"), call.get("type"))
    
    return call

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

    payload = {"start_date": start_date_iso, "end_date": end_date_iso, "limit_count": limit, "limit_offset": offset}
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        total_calls = data.get("total_call_count", 0)
        
        while offset < total_calls:
            payload["limit_offset"] = offset
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                calls.extend(data.get("call_list", []))
                offset += limit
                time.sleep(0.5)
            else:
                break
    
    return calls

# Envoi des données à Airtable
def send_to_airtable(calls):
    count = 0
    print(f"\U0001F504 Envoi de {len(calls)} appels vers Airtable...")

    for call in calls:
        try:
            call = traduire_valeurs(call)
            call_id = call.get("id")
            if not call_id:
                continue

            existing_records = airtable.search("ID Appel", call_id)
            if existing_records:
                continue

            record = {
                "ID Appel": call_id,
                "Date": call.get("start_time"),
                "Durée (s)": call.get("duration"),
                "Numéro Source": call.get("from_number"),
                "Numéro Destination": call.get("to_number"),
                "Type d'appel": call.get("type"),
                "Statut": call.get("status"),
                "Notes Détaillées": call.get("notes", ""),
                "Direction": call.get("direction"),
                "Scénario": call.get("scenario_name"),
                "User ID": call.get("user_id")
            }

            airtable.insert(record)
            count += 1
            time.sleep(0.2)
        except Exception as e:
            print(f"❌ Erreur lors de l'insertion pour {call_id}: {str(e)}")
    
    return count

# Exécution
if __name__ == "__main__":
    print("\U0001F680 Démarrage de la synchronisation Ringover → Airtable...")
    calls = get_ringover_calls()
    
    if calls:
        nbr_synchronisés = send_to_airtable(calls)
        print(f"✅ Synchronisation terminée. {nbr_synchronisés}/{len(calls)} appels synchronisés.")
    else:
        print("⚠️ Aucun appel à synchroniser.")
