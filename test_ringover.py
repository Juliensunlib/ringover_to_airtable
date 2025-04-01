import os
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement depuis un fichier .env
load_dotenv()

# Récupérer la clé API depuis les variables d'environnement
api_key = os.getenv("RINGOVER_API_KEY")

# Vérifier si la clé API est bien récupérée
if not api_key:
    print("❌ Erreur : Clé API Ringover non trouvée. Vérifie ton fichier .env ou tes secrets GitHub.")
    exit(1)

# URL de l'API Ringover
url = "https://public-api.ringover.com/v2/calls"

# En-têtes de la requête
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Effectuer la requête GET
response = requests.get(url, headers=headers)

# Afficher les résultats
print(f"Statut de la requête : {response.status_code}")

if response.status_code == 200:
    print("✅ Succès ! Voici la réponse de l'API Ringover :")
    print(response.json())
elif response.status_code == 401:
    print("❌ Erreur 401 : Accès non autorisé. Vérifie ta clé API.")
elif response.status_code == 403:
    print("❌ Erreur 403 : Accès interdit. Vérifie tes permissions sur l'API.")
else:
    print(f"❌ Erreur inconnue : {response.status_code}")
    print(response.text)
