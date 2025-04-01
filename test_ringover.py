import os
import requests

# Récupérer la clé API depuis les variables d'environnement GitHub Actions
api_key = os.getenv("RINGOVER_API_KEY")

if not api_key:
    print("❌ Erreur : Clé API introuvable. Assure-toi qu'elle est bien définie dans les Secrets GitHub.")
    exit(1)

# URL de test de l'API Ringover
url = "https://public-api.ringover.com/v2/calls"

# Headers avec la clé API
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "User-Agent": "GitHubActionsTest/1.0"
}

# Exécuter la requête
response = requests.get(url, headers=headers)

# Vérifier le statut de la requête
print(f"Statut de la requête : {response.status_code}")

if response.status_code == 200:
    print("✅ Succès ! Réponse de l'API Ringover :")
    print(response.json())
elif response.status_code == 401:
    print("❌ Erreur 401 : Accès non autorisé. Vérifie ta clé API dans les Secrets GitHub.")
elif response.status_code == 403:
    print("❌ Erreur 403 : Accès refusé. Vérifie les permissions de ta clé API.")
else:
    print(f"❌ Erreur {response.status_code} : {response.text}")
