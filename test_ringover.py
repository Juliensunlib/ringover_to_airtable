import os
import requests

# Charger la clé API depuis GitHub Secrets
API_KEY = os.getenv("RINGOVER_API_KEY")

# Vérifier si la clé API est bien récupérée
if not API_KEY:
    print("❌ Erreur : La clé API n'a pas été chargée. Vérifie ton Secret GitHub.")
    exit(1)

print(f"🔍 Clé API chargée : {API_KEY[:5]}... (longueur {len(API_KEY)})")

# Définition de l’URL de l’API Ringover
url = "https://public-api.ringover.com/v2/calls"

# Liste des formats d'authentification à tester
auth_headers = [
    {"Authorization": API_KEY, "Accept": "application/json"},  # Sans "Bearer"
    {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"},  # Avec "Bearer"
    {"X-API-KEY": API_KEY, "Accept": "application/json"}  # Avec "X-API-KEY"
]

# Test d'authentification avec plusieurs formats
for headers in auth_headers:
    print(f"🔍 Test avec l'en-tête : {list(headers.keys())[0]}")
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("✅ Succès ! Authentification réussie.")
        print("📊 Réponse API :", response.json())
        exit(0)
    elif response.status_code == 401:
        print(f"❌ Échec avec {list(headers.keys())[0]} (401 Unauthorized).")
    else:
        print(f"⚠️ Erreur {response.status_code} : {response.text}")

# Si aucun format ne fonctionne
print("❌ Aucun format d'authentification n'a fonctionné. Vérifie la clé API et les permissions.")
exit(1)
