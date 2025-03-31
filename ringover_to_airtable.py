import requests
import json
from datetime import datetime, timedelta
from airtable import Airtable
import os
from dotenv import load_dotenv
import time

# Charger les variables d'environnement
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

# 🔹 Fonction pour récupérer les appels de Ringover
def get_ringover_calls():
    url = "https://public-api.ringover.com/v2/calls"
    headers = {
        "Authorization": f"Bearer {RINGOVER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Définition de la plage de dates (max 15 jours)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=14)

    start_date_iso = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date_iso = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"🔍 Recherche des appels entre {start_date_iso} et {end_date_iso}")

    payload = {
        "start_date": start_date_iso,
        "end_date": end_date_iso,
        "limit_count": 10,  # On limite à 10 pour le test
        "limit_offset": 0,
        "note": True  # Récupérer uniquement les appels avec notes
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"📡 Statut API Ringover: {response.status_code}")

        if response.status_code != 200:
            print(f"❌ Erreur API: {response.text[:500]}")
            return []

        data = response.json()
        calls = data.get("call_list", [])

        # 🔹 Vérification des données reçues
        if not calls:
            print("⚠️ Aucun appel reçu. Vérifiez vos paramètres de requête.")
            return []

        print(f"✅ {len(calls)} appels récupérés.")

        # 🔍 Afficher un exemple d'appel pour debug
        print(json.dumps(calls[0], indent=2) if calls else "⚠️ Aucun appel disponible.")

        return calls

    except Exception as e:
        print(f"❌ Erreur lors de la requête Ringover: {str(e)}")
        return []

# 🔹 Fonction pour envoyer les appels vers Airtable
def send_to_airtable(calls):
    count = 0
    print(f"🔄 Envoi de {len(calls)} appels vers Airtable...")

    for i, call in enumerate(calls):
        try:
            call_id = call.get("id", f"temp_id_{i+1}")  # ID temporaire si absent
            start_time = call.get("start_time", "").replace("Z", "").replace("T", " ")

            record = {
                "ID Appel": call_id,
                "Date": start_time,
                "Durée (s)": call.get("duration", 0),
                "Numéro Source": call.get("from_number", ""),
                "Numéro Destination": call.get("to_number", ""),
                "Type d'appel": call.get("type", ""),
                "Statut": call.get("status", ""),
                "Notes Détaillées": call.get("notes", ""),
                "Direction": call.get("direction", ""),
                "Scénario": call.get("scenario_name", ""),
                "User ID": call.get("user_id", ""),
                "Channel ID": call.get("channel_id", "")
            }

            print(f"📤 Insertion de l'appel {call_id} dans Airtable...")
            airtable.insert(record)
            count += 1
            time.sleep(0.2)

        except Exception as e:
            print(f"❌ Erreur sur l'appel {call.get('id', 'Inconnu')}: {str(e)}")

    return count

# 🔹 Exécution du script
if __name__ == "__main__":
    print("🚀 Démarrage de la synchronisation Ringover → Airtable...")
    calls = get_ringover_calls()

    if calls:
        synced_count = send_to_airtable(calls)
        print(f"✅ Synchronisation terminée : {synced_count}/{len(calls)} appels envoyés.")
    else:
        print("⚠️ Aucun appel à synchroniser.")
