import os
import requests

# Récupérer la clé API depuis les variables d'environnement GitHub
api_key = os.getenv("RINGOVER_API_KEY")

if not api_key:
    print("❌ Erreur : Clé API introuvable. Assure-toi qu'elle est bien définie dans les Secrets GitHub.")
    exit(1)

# URL de l'API Ringover
url = "https://public-api.ringover.com/v2/calls"

# Headers
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Exécuter la requête
response = requests.get(url, headers=headers)

# Vérifier le statut HTTP
print(f"Statut de la requête : {response.status_code}")

if response.status_code == 200:
    print("✅ Succès ! L'API Ringover a répondu correctement.")
    print(response.json())
    exit(0)
elif response.status_code == 401:
    print("❌ Erreur 401 : Accès non autorisé. Vérifie ta clé API dans les Secrets GitHub.")
    exit(1)
elif response.status_code == 403:
    print("❌ Erreur 403 : Accès refusé. Vérifie les permissions de ta clé API.")
    exit(1)
else:
    print(f"❌ Erreur {response.status_code} : {response.text}")
    exit(1)
