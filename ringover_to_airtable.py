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

# Récupération des appels depuis Ringover
def get_ringover_calls():
    url = "https://public-api.ringover.com/v2/calls"
    headers = {
        "Authorization": f"Bearer {RINGOVER_API_KEY}",
        "Content-Type": "application/json"
    }

    calls = []
    offset = 0
    limit = 50  # Nombre d'appels à récupérer par requête
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)  # 14 jours pour être sûr
    start_date_iso = start_date.isoformat() + "Z"
    end_date_iso = end_date.isoformat() + "Z"

    print(f"🔍 Recherche des appels entre {start_date_iso} et {end_date_iso}")

    try:
        payload = {
            "start_date": start_date_iso,
            "end_date": end_date_iso,
            "limit_count": limit,
            "limit_offset": offset
        }

        while True:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                batch_calls = data.get("call_list", [])
                if not batch_calls:
                    break

                calls.extend(batch_calls)
                offset += limit
                payload["limit_offset"] = offset
                time.sleep(0.5)
            else:
                print(f"❌ Erreur API: {response.status_code} - {response.text[:200]}...")
                break
                
    except Exception as e:
        print(f"❌ Exception lors de la récupération des appels: {str(e)}")

    print(f"✓ {len(calls)} appels récupérés.")
    return calls

# Envoi des données à Airtable
def send_to_airtable(calls):
    count = 0
    print(f"🔄 Envoi de {len(calls)} appels vers Airtable...")

    for i, call in enumerate(calls):
        try:
            call_id = call.get("id", f"temp_id_{i+1}")

            existing_records = airtable.search("ID Appel", call_id)
            if existing_records:
                print(f"⏩ Appel {call_id} déjà présent dans Airtable, ignoré.")
                continue

            start_time = call.get("start_time")
            if start_time:
                try:
                    start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass  

            # Vérification des champs de transcription potentiels
            transcription = call.get("transcription") or call.get("notes_ai") or "Aucune transcription disponible"

            record = {
                "ID Appel": call_id,
                "Date": start_time,
                "Durée (s)": call.get("duration"),
                "Numéro Source": call.get("from_number"),
                "Numéro Destination": call.get("to_number"),
                "Type d'appel": call.get("type"),
                "Statut": call.get("status"),
                "Notes Détaillées": call.get("notes", ""),
                "Direction": call.get("direction"),
                "Scénario": call.get("scenario_name"),
                "User ID": call.get("user_id"),
                "Channel ID": call.get("channel_id"),
                "Transcription": transcription  # Ajout de la transcription
            }

            airtable.insert(record)
            count += 1

            if (i + 1) % 10 == 0 or i == len(calls) - 1:
                print(f"⏳ {i + 1}/{len(calls)} appels traités...")

            time.sleep(0.2)

        except Exception as e:
            print(f"❌ Erreur lors de l'insertion dans Airtable pour l'appel {call.get('id')}: {str(e)}")

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
