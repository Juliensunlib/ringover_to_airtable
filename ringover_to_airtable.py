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

# Fonction pour récupérer tous les ID Appel déjà enregistrés dans Airtable
def get_existing_call_ids():
    print("📥 Récupération des appels déjà enregistrés dans Airtable...")
    existing_ids = set()
    offset = None

    while True:
        params = {"view": "Grid view"}
        if offset:
            params["offset"] = offset

        response = airtable.get_all(fields=["ID Appel"], offset=offset)
        
        for record in response:
            call_id = record["fields"].get("ID Appel")
            if call_id:
                existing_ids.add(str(call_id))

        # Vérification s'il reste encore des pages à récupérer
        offset = response[-1].get("offset") if response else None
        if not offset:
            break

    print(f"✅ {len(existing_ids)} appels existants récupérés.")
    return existing_ids

# Fonction pour récupérer les appels depuis Ringover
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

    try:
        # Vérification du nombre total d'appels
        payload = {
            "start_date": start_date_iso,
            "end_date": end_date_iso,
            "limit_count": 1,
            "limit_offset": 0
        }
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            total_calls = data.get("total_call_count", 0)
            print(f"📊 Total des appels disponibles : {total_calls}")

            if total_calls == 0:
                return []

            while offset < total_calls:
                payload["limit_count"] = limit
                payload["limit_offset"] = offset
                response = requests.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    batch_calls = data.get("call_list", [])

                    if not batch_calls:
                        break

                    calls.extend(batch_calls)
                    offset += limit
                    time.sleep(0.5)
                else:
                    print(f"❌ Erreur Ringover API: {response.status_code} - {response.text}")
                    break

        else:
            print(f"❌ Erreur Ringover API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception lors de la récupération des appels : {str(e)}")

    print(f"✓ Récupération de {len(calls)} appels terminée")
    return calls

# Envoi des nouveaux appels à Airtable
def send_to_airtable(calls, existing_ids):
    count = 0
    print(f"🔄 Envoi des nouveaux appels vers Airtable...")

    for i, call in enumerate(calls):
        try:
            call_id = call.get("call_id") or call.get("cdr_id")
            if not call_id:
                continue

            call_id = str(call_id)  # Assurer la conversion en string

            # Vérification : si l'ID existe déjà, on l'ignore
            if call_id in existing_ids:
                print(f"⏩ Appel {call_id} déjà présent, ignoré.")
                continue

            # Extraction des informations
            start_time = call.get("start_time")
            if start_time:
                try:
                    start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    start_time = None

            duration = call.get("total_duration") or call.get("incall_duration") or call.get("duration")
            record = {
                "ID Appel": call_id,
                "Date": start_time,
                "Durée (s)": duration,
                "Numéro Source": call.get("from_number"),
                "Numéro Destination": call.get("to_number"),
                "Type d'appel": call.get("type"),
                "Statut": call.get("last_state") or call.get("status"),
                "Direction": call.get("direction"),
                "Scénario": call.get("scenario_name"),
            }

            # Insérer dans Airtable
            airtable.insert(record)
            count += 1
            existing_ids.add(call_id)  # Ajouter l'ID à la liste existante

            # Afficher la progression
            if (i + 1) % 10 == 0 or i == len(calls) - 1:
                print(f"⏳ {i + 1}/{len(calls)} appels traités...")

            # Respect des limites de l'API Airtable
            time.sleep(0.2)

        except Exception as e:
            print(f"❌ Erreur lors de l'insertion de l'appel {call.get('call_id')} : {str(e)}")

    return count

# Exécution principale
if __name__ == "__main__":
    print("🚀 Démarrage de la synchronisation Ringover → Airtable...")

    existing_call_ids = get_existing_call_ids()  # Récupération des ID déjà en base
    calls = get_ringover_calls()  # Récupération des appels depuis Ringover

    if calls:
        nbr_synchronisés = send_to_airtable(calls, existing_call_ids)
        print(f"✅ Synchronisation terminée. {nbr_synchronisés}/{len(calls)} nouveaux appels synchronisés.")
    else:
        print("⚠️ Aucun appel à synchroniser.")
