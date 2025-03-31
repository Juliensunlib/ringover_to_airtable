import requests
import json
from datetime import datetime
from airtable import Airtable
import os
from dotenv import load_dotenv

# Charger les variables depuis le fichier .env
load_dotenv()
print("RINGOVER_API_KEY:", os.getenv("RINGOVER_API_KEY"))
print("AIRTABLE_BASE_ID:", os.getenv("AIRTABLE_BASE_ID"))
print("AIRTABLE_TABLE_NAME:", os.getenv("AIRTABLE_TABLE_NAME"))
print("AIRTABLE_API_KEY:", os.getenv("AIRTABLE_API_KEY"))

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
    headers = {"Authorization": f"Bearer {RINGOVER_API_KEY}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Erreur Ringover API : {response.status_code}")
        return []

# Envoi des données à Airtable
def send_to_airtable(calls):
    for call in calls:
        record = {
            "ID Appel": call.get("id"),
            "Date": datetime.fromtimestamp(call.get("start_time")).strftime("%Y-%m-%d %H:%M:%S"),
            "Durée (s)": call.get("duration"),
            "Numéro Source": call.get("from_number"),
            "Numéro Destination": call.get("to_number"),
            "Type d'appel": call.get("type"),
            "Statut": call.get("status"),
            "Notes Détaillées": call.get("notes")
        }
        airtable.insert(record)

# Exécution
if __name__ == "__main__":
    calls = get_ringover_calls()
    if calls:
        send_to_airtable(calls)
        print("✅ Synchronisation Ringover → Airtable terminée.")
    else:
        print("⚠️ Aucun appel à synchroniser.")
