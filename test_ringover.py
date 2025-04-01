import requests
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# Récupérer la clé API
api_key = os.getenv("RINGOVER_API_KEY")

if not api_key:
    print("Erreur : la clé API Ringover n'est pas définie dans le fichier .env")
    exit(1)

# URL de l'API Ringover
url = "https://public-api.ringover.com/v2/calls?limit_count=5"
headers = {
    "Authorization": f"Bearer {api_key}"
}

# Faire la requête
response = requests.get(url, headers=headers)

# Afficher la réponse
print(f"Statut: {response.status_code}")
print(response.text)
