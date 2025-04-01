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
    # Utilisation de la méthode POST qui offre plus de flexibilité selon la documentation
    url = "https://public-api.ringover.com/v2/calls"
    
    # CORRECTION: Modification du format d'authentification
    # Essayer plusieurs formats possibles d'authentification
    headers = {
        "Authorization": RINGOVER_API_KEY,  # Format sans "Bearer"
        "Content-Type": "application/json"
    }
    
    # Test initial pour vérifier le format d'authentification
    print("🔍 Test de l'authentification à l'API Ringover...")
    test_response = requests.get(url, headers=headers)
    
    if test_response.status_code == 401:
        # Essayer avec le format Bearer
        headers["Authorization"] = f"Bearer {RINGOVER_API_KEY}"
        test_response = requests.get(url, headers=headers)
        
        if test_response.status_code == 401:
            # Essayer avec X-API-KEY
            headers = {
                "X-API-KEY": RINGOVER_API_KEY,
                "Content-Type": "application/json"
            }
            test_response = requests.get(url, headers=headers)
    
    if test_response.status_code == 401:
        print("❌ Échec de l'authentification avec tous les formats testés.")
        print("👉 Vérifiez que votre clé API est correcte et a les droits nécessaires.")
        return []
    else:
        print(f"✅ Authentification réussie avec le format: {headers}")
    
    calls = []
    offset = 0
    limit = 50  # Nombre d'appels à récupérer par requête
    
    # Calcul des dates (limité à 15 jours selon la documentation)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)  # 14 jours pour être sûr
    
    # Formatage des dates au format ISO
    start_date_iso = start_date.isoformat() + "Z"
    end_date_iso = end_date.isoformat() + "Z"
    
    print(f"🔍 Recherche des appels entre {start_date_iso} et {end_date_iso}")
    
    try:
        # Première requête pour obtenir le nombre total d'appels
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
            print(f"📊 Total des appels disponibles: {total_calls}")
            
            if total_calls == 0:
                return []
            
            # Récupération par lots
            while offset < total_calls and offset < 9000:  # Limite max de offset selon doc
                payload = {
                    "start_date": start_date_iso,
                    "end_date": end_date_iso,
                    "limit_count": limit,
                    "limit_offset": offset
                }
                
                print(f"📥 Récupération du lot {offset+1}-{min(offset+limit, total_calls)} sur {total_calls}")
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    batch_calls = data.get("call_list", [])
                    
                    if not batch_calls:
                        break
                    
                    calls.extend(batch_calls)
                    offset += limit
                    
                    # Respecter les limites de l'API
                    time.sleep(0.5)
                elif response.status_code == 204:
                    print("⚠️ Aucun appel trouvé dans ce lot")
                    break
                else:
                    print(f"❌ Erreur Ringover API: {response.status_code}")
                    print(f"📄 Réponse: {response.text[:200]}...")
                    break
                
        elif response.status_code == 204:
            print("⚠️ Aucun appel à synchroniser")
        else:
            print(f"❌ Erreur Ringover API: {response.status_code}")
            print(f"📄 Réponse: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Exception lors de la récupération des appels: {str(e)}")
    
    print(f"✓ Récupération de {len(calls)} appels terminée")
    return calls

# Envoi des données à Airtable
def send_to_airtable(calls):
    count = 0
    print(f"🔄 Envoi de {len(calls)} appels vers Airtable...")

    for i, call in enumerate(calls):
        try:
            # Extraction de call_id (ID de l'appel)
            call_id = call.get("call_id")
            
            # Si l'ID est manquant, on utilise cdr_id ou on génère un ID temporaire
            if not call_id:
                call_id = call.get("cdr_id") or f"temp_id_{i+1}"
                print(f"⚠️ Appel sans ID (création d'ID temporaire {call_id})")

            # Vérification des appels déjà existants pour éviter les doublons
            existing_records = airtable.search("ID Appel", str(call_id))

            if existing_records:
                print(f"⏩ Appel {call_id} déjà présent dans Airtable, ignoré.")
                continue

            # Extraction des informations de l'utilisateur, y compris les initiales
            user_info = call.get("user", {})
            user_id = user_info.get("initial", "")  # Récupération des initiales
            user_name = user_info.get("concat_name", "")
            
            # Extraction des notes d'appel (saisies par les agents)
            agent_notes = call.get("note", "")
            
            # Récupération des informations de contact
            contact_info = call.get("contact", {})
            contact_name = ""
            contact_details = ""
            
            if contact_info:
                # Récupération du nom du contact
                contact_name = contact_info.get("concat_name", "")
                
                # Construction des détails du contact
                contact_details_list = []
                
                # Ajout du nom
                if contact_name:
                    contact_details_list.append(f"Nom: {contact_name}")
                
                # Ajout de l'entreprise
                company = contact_info.get("company")
                if company:
                    contact_details_list.append(f"Entreprise: {company}")
                
                # Ajout des emails
                emails = contact_info.get("emails", [])
                if emails:
                    email_str = ", ".join([e.get("email") for e in emails if e.get("email")])
                    if email_str:
                        contact_details_list.append(f"Email: {email_str}")
                
                # Ajout des numéros de téléphone
                numbers = contact_info.get("numbers", [])
                if numbers:
                    for num in numbers:
                        num_format = num.get("format", {})
                        if num_format:
                            number_str = num_format.get("national", "")
                            number_type = num.get("type", "")
                            if number_str and number_type:
                                contact_details_list.append(f"Tél ({number_type}): {number_str}")
                
                # Formatage final des détails
                contact_details = "\n".join(contact_details_list)
                
            # Traitement des dates
            start_time = call.get("start_time")
            if start_time:
                try:
                    start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass  # Garder la valeur originale si on ne peut pas la convertir

            # Récupération de la durée (priorité à total_duration puis incall_duration)
            duration = call.get("total_duration") or call.get("incall_duration") or call.get("duration")

            # Création d'un enregistrement plus complet en fonction des données disponibles
            record = {
                "ID Appel": str(call_id),  # Conversion en string pour assurer la compatibilité
                "Date": start_time,
                "Durée (s)": duration,
                "Numéro Source": call.get("from_number"),
                "Numéro Destination": call.get("to_number"),
                "Type d'appel": call.get("type"),
                "Statut": call.get("last_state") or call.get("status"),
                "Notes Détaillées": agent_notes,  # Uniquement les notes saisies par l'agent
                "Contact": contact_details,  # Nouvelle colonne pour les informations de contact
                "Nom du Contact": contact_name,  # Juste le nom du contact
                "Direction": call.get("direction"),
                "Scénario": call.get("scenario_name"),
                "User ID": user_id,  # Utilisation des initiales comme User ID
                "Channel ID": call.get("channel_id")
            }

            # Insérer dans Airtable
            airtable.insert(record)
            count += 1

            # Afficher la progression
            if (i + 1) % 10 == 0 or i == len(calls) - 1:
                print(f"⏳ {i + 1}/{len(calls)} appels traités...")

            # Respecter les limites de l'API Airtable (5 requêtes/seconde)
            time.sleep(0.2)

        except Exception as e:
            print(f"❌ Erreur lors de l'insertion dans Airtable pour l'appel {call.get('call_id')}: {str(e)}")

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
