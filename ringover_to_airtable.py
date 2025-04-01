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
    
    # AMÉLIORATION: Test de plusieurs formats d'authentification
    auth_formats = [
        {"Authorization": RINGOVER_API_KEY},
        {"Authorization": f"Bearer {RINGOVER_API_KEY}"},
        {"X-API-KEY": RINGOVER_API_KEY},
        {"Api-Key": RINGOVER_API_KEY}
    ]
    
    headers = None
    
    print("🔍 Test des formats d'authentification à l'API Ringover...")
    for auth_format in auth_formats:
        test_headers = {**auth_format, "Content-Type": "application/json"}
        try:
            test_response = requests.get(url, headers=test_headers)
            print(f"Format testé: {auth_format} - Statut: {test_response.status_code}")
            
            if test_response.status_code != 401:
                headers = test_headers
                print(f"✅ Authentification réussie avec: {auth_format}")
                break
        except Exception as e:
            print(f"❌ Erreur lors du test d'authentification: {str(e)}")
    
    if headers is None:
        print("❌ Échec de l'authentification avec tous les formats testés.")
        print("👉 Vérifiez que votre clé API est correcte et a les droits nécessaires.")
        return []
    
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
        
        # DEBUG: Afficher la réponse complète pour la première requête
        print(f"👀 Réponse API pour la première requête (format): {response.status_code}")
        if response.status_code == 200:
            try:
                sample_data = response.json()
                print(f"📊 Exemple de structure de données reçue:")
                # Afficher la structure pour déboguer
                print(json.dumps(sample_data, indent=2)[:500] + "..." if len(json.dumps(sample_data)) > 500 else "")
                
                # Vérifier les champs disponibles dans un appel
                if "call_list" in sample_data and len(sample_data["call_list"]) > 0:
                    sample_call = sample_data["call_list"][0]
                    print(f"📞 Exemple de champs disponibles dans un appel:")
                    print(json.dumps(sample_call, indent=2))
                    
                total_calls = sample_data.get("total_call_count", 0)
                print(f"📊 Total des appels disponibles: {total_calls}")
                
                if total_calls == 0:
                    return []
            except Exception as e:
                print(f"⚠️ Erreur lors de l'analyse de la réponse: {str(e)}")
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
                    
                    # Vérifier la structure de la réponse pour s'adapter
                    if "call_list" in data:
                        batch_calls = data.get("call_list", [])
                    else:
                        # Structure alternative possible
                        batch_calls = data.get("calls", [])
                        if not batch_calls and isinstance(data, list):
                            batch_calls = data
                    
                    if not batch_calls:
                        print("⚠️ Aucun appel trouvé dans ce lot ou format de réponse non reconnu")
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
    
    # Si des appels ont été récupérés, afficher le premier pour vérifier la structure
    if calls and len(calls) > 0:
        print(f"📄 Structure du premier appel récupéré:")
        print(json.dumps(calls[0], indent=2))
        
    return calls

# Obtenir les champs disponibles dans Airtable
def get_airtable_fields():
    try:
        # Récupérer un enregistrement pour voir la structure
        records = airtable.get(maxRecords=1)
        if records and 'records' in records and len(records['records']) > 0:
            first_record = records['records'][0]
            if 'fields' in first_record:
                return set(first_record['fields'].keys())
        
        # Si aucun enregistrement n'existe, utiliser une liste de champs standard
        return {
            "ID Appel", "Date", "Durée (s)", "Numéro Source", "Numéro Destination",
            "Type d'appel", "Statut", "Notes Détaillées", "Direction", "Scénario",
            "User ID", "Channel ID", "Données brutes"
        }
    except Exception as e:
        print(f"⚠️ Impossible de récupérer les champs Airtable: {str(e)}")
        # Retourner une liste de champs de base
        return {
            "ID Appel", "Date", "Durée (s)", "Numéro Source", "Numéro Destination",
            "Type d'appel", "Statut", "Notes Détaillées", "Direction", "Scénario",
            "User ID", "Channel ID", "Données brutes"
        }

# Envoi des données à Airtable
def send_to_airtable(calls):
    count = 0
    print(f"🔄 Envoi de {len(calls)} appels vers Airtable...")
    
    # Récupérer les champs disponibles dans Airtable
    available_fields = get_airtable_fields()
    print(f"📋 Champs disponibles dans Airtable: {available_fields}")

    for i, call in enumerate(calls):
        try:
            # Recherche de champs d'ID avec plusieurs variations possibles
            call_id = None
            id_field_variations = ["id", "call_id", "callId", "uid", "uniqueId"]
            for field in id_field_variations:
                if field in call and call[field]:
                    call_id = call[field]
                    print(f"✓ ID d'appel trouvé sous le champ '{field}': {call_id}")
                    break
            
            # Si l'ID est toujours manquant, on génère un ID temporaire
            if not call_id:
                call_id = f"temp_id_{i+1}"
                print(f"⚠️ Appel sans ID (création d'ID temporaire {call_id})")

            # Vérification des appels déjà existants pour éviter les doublons
            existing_records = airtable.search("ID Appel", call_id)

            if existing_records:
                print(f"⏩ Appel {call_id} déjà présent dans Airtable, ignoré.")
                continue

            # Recherche de variations pour les champs importants
            notes = None
            notes_field_variations = ["notes", "note", "comment", "comments", "description"]
            for field in notes_field_variations:
                if field in call and call[field]:
                    notes = call[field]
                    print(f"✓ Notes trouvées sous le champ '{field}'")
                    break
            
            # Recherche de variations pour le champ durée
            duration = None
            duration_field_variations = ["duration", "call_duration", "callDuration", "length", "time"]
            for field in duration_field_variations:
                if field in call and call[field] is not None:
                    duration = call[field]
                    print(f"✓ Durée trouvée sous le champ '{field}': {duration}")
                    break
            
            # Recherche de variations pour le champ user_id
            user_id = None
            user_id_field_variations = ["user_id", "userId", "operator_id", "operatorId", "agent_id", "agentId"]
            for field in user_id_field_variations:
                if field in call and call[field]:
                    user_id = call[field]
                    print(f"✓ User ID trouvé sous le champ '{field}': {user_id}")
                    break

            # Traitement des dates
            start_time = None
            start_time_field_variations = ["start_time", "startTime", "start_date", "startDate", "date", "timestamp"]
            for field in start_time_field_variations:
                if field in call and call[field]:
                    start_time = call[field]
                    print(f"✓ Date de début trouvée sous le champ '{field}': {start_time}")
                    break
            
            # Conversion de la date si nécessaire
            if start_time:
                try:
                    start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            # Essai de conversion d'un timestamp Unix
                            if isinstance(start_time, (int, float)):
                                start_time = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            pass  # Garder la valeur originale si on ne peut pas la convertir

            # Construction d'un record avec uniquement les champs qui existent dans Airtable
            record = {}
            
            # Ajouter les champs standard s'ils existent dans Airtable
            standard_fields = {
                "ID Appel": call_id,
                "Date": start_time,
                "Durée (s)": duration,
                "Numéro Source": call.get("from_number") or call.get("from") or call.get("source"),
                "Numéro Destination": call.get("to_number") or call.get("to") or call.get("destination"),
                "Type d'appel": call.get("type") or call.get("call_type"),
                "Statut": call.get("status") or call.get("call_status"),
                "Notes Détaillées": notes or "",
                "Direction": call.get("direction"),
                "Scénario": call.get("scenario_name") or call.get("scenario"),
                "User ID": user_id,
                "Channel ID": call.get("channel_id") or call.get("channelId")
            }
            
            for field, value in standard_fields.items():
                if field in available_fields and value is not None:
                    record[field] = value
            
            # Stocker toutes les données brutes dans un champ JSON si disponible
            if "Données brutes" in available_fields:
                record["Données brutes"] = json.dumps(call)
            
            # Insérer dans Airtable
            airtable.insert(record)
            count += 1

            # Afficher la progression
            if (i + 1) % 10 == 0 or i == len(calls) - 1:
                print(f"⏳ {i + 1}/{len(calls)} appels traités...")

            # Respecter les limites de l'API Airtable (5 requêtes/seconde)
            time.sleep(0.2)

        except Exception as e:
            print(f"❌ Erreur lors de l'insertion dans Airtable pour l'appel {i}: {str(e)}")

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
