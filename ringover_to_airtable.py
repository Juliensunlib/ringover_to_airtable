import requests
import json
from datetime import datetime, timedelta, timezone
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
    
    # Vérification de l'authentification
    headers = {
        "Authorization": f"Bearer {RINGOVER_API_KEY}",
        "Content-Type": "application/json"
    }

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=14)

    start_date_iso = start_date.isoformat()
    end_date_iso = end_date.isoformat()

    print(f"🔍 Recherche des appels entre {start_date_iso} et {end_date_iso}")

    payload = {
        "start_date": start_date_iso,
        "end_date": end_date_iso,
        "limit_count": 50,
        "limit_offset": 0
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        print(f"❌ Erreur Ringover API: {response.status_code}")
        print(f"📄 Réponse: {response.text[:500]}")
        return []

    data = response.json()
    calls = data.get("call_list", [])

    if not calls:
        print("⚠️ Aucun appel trouvé.")
        return []

    # 🛠️ Affichage des 3 premiers appels pour débogage
    print("🔍 Aperçu des premiers appels reçus :")
    for i, call in enumerate(calls[:3]):
        print(f"📞 Appel {i+1}: {json.dumps(call, indent=2)}")

    return calls

# Envoi des données à Airtable
def send_to_airtable(calls):
    print(f"🔄 Envoi de {len(calls)} appels vers Airtable...")

    for i, call in enumerate(calls):
        call_id = call.get("id", f"temp_id_{i+1}")
        start_time = call.get("start_time")
        duration = call.get("duration")
        from_number = call.get("from_number")
        to_number = call.get("to_number")
        call_type = call.get("type")
        status = call.get("status")
        notes = call.get("notes", "")
        direction = call.get("direction")
        scenario = call.get("scenario_name")
        user_id = call.get("user_id")
        channel_id = call.get("channel_id")

        # ✅ Vérification et logs si une donnée manque
        if not call_id:
            print(f"⚠️ L'ID de l'appel est manquant pour {call}")
        if status is None:
            print(f"⚠️ Statut absent pour l'appel {call_id}")
        if user_id is None:
            print(f"⚠️ User ID absent pour l'appel {call_id}")
        if not notes:
            print(f"⚠️ Notes absentes pour l'appel {call_id}")

        # Conversion de la date
        if start_time:
            try:
                start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass  # Garder la valeur originale si on ne peut pas la convertir

        record = {
            "ID Appel": call_id,
            "Date": start_time,
            "Durée (s)": duration,
            "Numéro Source": from_number,
            "Numéro Destination": to_number,
            "Type d'appel": call_type,
            "Statut": status,
            "Notes Détaillées": notes,
            "Direction": direction,
            "Scénario": scenario,
            "User ID": user_id,
            "Channel ID": channel_id
        }

        # Vérification avant insertion
        existing_records = airtable.search("ID Appel", call_id)
        if existing_records:
            print(f"⏩ Appel {call_id} déjà présent dans Airtable, ignoré.")
            continue

        try:
            airtable.insert(record)
            print(f"✅ Appel {call_id} ajouté.")
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de {call_id} : {str(e)}")

        # Respecter les limites de l'API Airtable
        time.sleep(0.2)

# Exécution
if __name__ == "__main__":
    print("🚀 Démarrage de la synchronisation Ringover → Airtable...")
    calls = get_ringover_calls()

    if calls:
        send_to_airtable(calls)
        print(f"✅ Synchronisation terminée.")
    else:
        print("⚠️ Aucun appel à synchroniser.")
