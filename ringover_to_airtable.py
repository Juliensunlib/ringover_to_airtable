def send_to_airtable(calls):
    count = 0
    print(f"🔄 Envoi de {len(calls)} appels vers Airtable...")
    
    for i, call in enumerate(calls):
        try:
            # Vérification des appels déjà existants pour éviter les doublons
            call_id = call.get("id")
            
            # Vérifier si l'ID est None ou vide avant de faire la recherche
            if not call_id:
                print(f"⚠️ Appel ignoré: ID manquant (position {i+1}/{len(calls)})")
                continue
                
            existing_records = airtable.search("ID Appel", call_id)
            
            if existing_records:
                print(f"⏩ Appel {call_id} déjà présent dans Airtable, ignoré.")
                continue
            
            # Traitement des dates
            start_time = call.get("start_time")
            if start_time:
                # Vérifier si la date est déjà au format ISO
                try:
                    start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # Si le format est différent, essayer d'autres formats
                    try:
                        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass  # Garder la valeur originale si on ne peut pas la convertir
            
            # Création d'un enregistrement plus complet en fonction des données disponibles
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
            print(f"❌ Erreur lors de l'insertion dans Airtable pour l'appel {call.get('id')}: {str(e)}")
    
    return count
