import requests
import json
from datetime import datetime
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
    headers = {"Authorization": f"Bearer {RINGOVER_API_KEY}"}
    
    calls = []
    offset = 0
    limit = 50  # Exemple, tu peux ajuster cette valeur
    
    while True:
        try:
            response = requests.get(url, headers=headers, params={"limit_offset": offset, "limit_count": limit})
            
            if response.status_code == 200:
                data = response.json().get("data", [])
                if not data:
                    break  # Si aucun appel n'est retourné, on sort de la boucle
                
                calls.extend(data)
                offset += limit  # On passe au prochain lot de résultats
                time.sleep(0.5)  # Respecte la limite de taux de l'API (2 appels/sec)
            else:
                print(f"❌ Erreur Ringover API : {response.status_code} - {response.text}")
                break
        except Exception as e:
            print(f"❌ Exception lors de la récupération des appels: {str(e)}")
            break
            
    return calls

# Envoi des données à Airtable
def send_to_airtable(calls):
    count = 0
    for call in calls:
        try:
            # Assure-toi que "start_time" est dans le bon format
            start_time = call.get("start_time")
            if start_time:
                start_time = datetime.fromisoformat(start_time).strftime("%Y-%m-%d %H:%M:%S")
            
            record = {
                "ID Appel": call.get("id"),
                "Date": start_time,
                "Durée (s)": call.get("duration"),
                "Numéro Source": call.get("from_number"),
                "Numéro Destination": call.get("to_number"),
                "Type d'appel": call.get("type"),
                "Statut": call.get("status"),
                "Notes Détaillées": call.get("notes", "")
            }
            airtable.insert(record)
            count += 1
        except Exception as e:
            print(f"❌ Erreur lors de l'insertion dans Airtable: {str(e)}")
    
    return count

# Exécution
if __name__ == "__main__":
    print("🔄 Démarrage de la synchronisation Ringover → Airtable...")
    calls = get_ringover_calls()
    if calls:
        nbr_synchronisés = send_to_airtable(calls)
        print(f"✅ Synchronisation terminée. {nbr_synchronisés}/{len(calls)} appels synchronisés.")
    else:
        print("⚠️ Aucun appel à synchroniser.")
