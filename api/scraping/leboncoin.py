from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import boto3
from botocore.client import Config
import os
from datetime import datetime

# Configuration du navigateur
options = Options()
options.add_argument('--headless')  # Enlève ça si tu veux voir le navigateur
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-notifications')
options.add_argument('--disable-popup-blocking')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')

# Configuration MinIO S3
# Remplacer par vos propres valeurs si nécessaire
# S3_ENDPOINT = 'http://localhost:9000'  # URL de votre serveur MinIO
# S3_ACCESS_KEY = 'minioadmin'           # Clé d'accès par défaut
# S3_SECRET_KEY = 'minioadmin123'           # Clé secrète par défaut
# S3_BUCKET = 'web-scraping'             # Nom du bucket

# Initialisation du client S3
# try:
    # s3_client = boto3.client('s3',
    #                       endpoint_url=S3_ENDPOINT,
    #                       aws_access_key_id=S3_ACCESS_KEY,
    #                       aws_secret_access_key=S3_SECRET_KEY,
    #                       config=Config(signature_version='s3v4'),
    #                       region_name='us-east-1')
    
    # Vérifier si le bucket existe, sinon le créer
# try:
#         s3_client.head_bucket(Bucket=S3_BUCKET)
#         print(f"✅ Bucket '{S3_BUCKET}' existe déjà")
# except:
#         s3_client.create_bucket(Bucket=S3_BUCKET)
#         print(f"✅ Bucket '{S3_BUCKET}' créé")
        
# print("✅ Connexion à MinIO S3 établie")
# except Exception as e:
#     print(f"❌ Erreur lors de la connexion à MinIO S3: {e}")
#     exit(1)

# Initialisation du navigateur
try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 15)
    print("✅ Driver initialisé avec succès")
except Exception as e:
    print(f"❌ Erreur lors de l'initialisation du driver: {e}")
    exit(1)

url = "https://www.leboncoin.fr/recherche?category=9&locations=Villeurbanne_69100__45.76962_4.87898_3820_10000&real_estate_type=2"
print(f"📌 Accès à l'URL: {url}")

try:
    driver.get(url)
    print("✅ Page chargée")
except Exception as e:
    print(f"❌ Erreur lors du chargement de la page: {e}")
    driver.quit()
    exit(1)

time.sleep(5)

# Accepter les cookies si popup présente
try:
    cookie_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
    )
    cookie_button.click()
    print("✅ Cookies acceptés")
    time.sleep(2)
except Exception as e:
    print(f"ℹ️ Pas de popup de cookies ou déjà acceptée: {e}")

# Récupérer tout le code HTML de la page
try:
    page_html = driver.page_source
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"LeBonCoin{timestamp}.html"
    # sauvgarde dans le dossier courant
    local_file_path = os.path.join(os.getcwd(), filename)
    
    with open(local_file_path, "w", encoding="utf-8") as f:
        f.write(page_html)
    
    print(f"✅ Code HTML complet sauvegardé dans {local_file_path}")
    print(f"✅ Taille du HTML: {len(page_html)} caractères")
    
    # Envoi du fichier vers MinIO S3
    # try:
    #     s3_client.upload_file(local_file_path, S3_BUCKET, filename)
    #     print(f"✅ Fichier '{filename}' envoyé avec succès vers MinIO S3 dans le bucket '{S3_BUCKET}'")
    # except Exception as e:
    #     print(f"❌ Erreur lors de l'envoi vers MinIO S3: {e}")
    
except Exception as e:
    print(f"❌ Erreur lors de la récupération du HTML: {e}")

# Capture ecran pour debug
screenshot_filename = f"leboncoin_{timestamp}.png"
try:
    driver.save_screenshot(screenshot_filename)
    print(f"Capture d'écran finale enregistrée dans {screenshot_filename}")
#     try:
#         s3_client.upload_file(screenshot_filename, S3_BUCKET, screenshot_filename)
#         print(f" Capture d'écran envoyée avec succès vers MinIO S3")
#     except Exception as e:
#         print(f" Erreur lors de l'envoi de la capture d'écran vers MinIO S3: {e}")     
except Exception as e:
    print(f" Erreur lors de la capture finale: {e}")

driver.quit()
print("✅ Navigateur fermé")