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
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import re
import os
from minio import Minio
from dotenv import load_dotenv
import pandas as pd

# Configuration navigateur
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-notifications')
options.add_argument('--disable-popup-blocking')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')

# Chargement .env
load_dotenv()

# Config MinIO
S3_ENDPOINT = 'http://localhost:9000'
S3_ACCESS_KEY = 'minioadmin'
S3_SECRET_KEY = 'minioadmin123'
S3_BUCKET = 'web-scraping'

# Client MinIO
s3_client = boto3.client('s3',
                         endpoint_url=S3_ENDPOINT,
                         aws_access_key_id=S3_ACCESS_KEY,
                         aws_secret_access_key=S3_SECRET_KEY,
                         config=Config(signature_version='s3v4'),
                         region_name='us-east-1')

# Création du bucket si besoin
try:
    s3_client.head_bucket(Bucket=S3_BUCKET)
    print(f"✅ Bucket '{S3_BUCKET}' existe déjà")
except:
    s3_client.create_bucket(Bucket=S3_BUCKET)
    print(f"✅ Bucket '{S3_BUCKET}' créé")

# Initialisation navigateur
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 15)

# Lecture CSV
csv_path = "villes_sans_doublons.csv"
df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip()

MAX_PAGES = 3

for _, city_data in df.iterrows():
    ville, seloger_url, code_commun = city_data
    logicimmo_url = seloger_url.replace("www.seloger.com", "www.logic-immo.com")
    
    print(f"\n🎯 Début du scraping pour {ville}")
    print(f"🔗 URL : {logicimmo_url}")
    print(f"📍 Code commune (depuis CSV) : {code_commun}")

    parsed_url = urlparse(logicimmo_url)
    query_params = parse_qs(parsed_url.query)
    location_code = query_params.get('locations', ['unknown'])[0]
    print(f"📦 Code location extrait : {location_code}")

    for page in range(1, MAX_PAGES + 1):
        try:
            full_url = f"{logicimmo_url}&page={page}"
            print(f"\n📌 Page {page} - Accès à l'URL : {full_url}")
            driver.get(full_url)
            time.sleep(5)

            if page == 1:
                try:
                    cookie_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
                    )
                    cookie_button.click()
                    print("✅ Cookies acceptés")
                    time.sleep(2)
                except:
                    print("ℹ️ Pas de popup cookies")

            try:
                titre_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1[data-testid='serp-title-variant-b-testid']"))
                )
                titre_texte = titre_element.get_attribute("textContent").strip()
                print(f"✅ Titre extrait : {titre_texte}")

                ville_scraped = "inconnue"

                if "–" in titre_texte:
                    match = re.search(r"–\s*(.*?),\s*(\d{5})", titre_texte)
                    if match:
                        ville_scraped = match.group(1).strip()
                    else:
                        match_ville = re.search(r"–\s*(.*?)$", titre_texte)
                        if match_ville:
                            ville_scraped = match_ville.group(1).strip()
                print(f"🏙️ Ville détectée (scraping) : {ville_scraped}")
            except Exception as e:
                print(f"❌ Erreur extraction titre : {e}")
                ville_scraped = "inconnue"

            # Sauvegarde HTML
            page_html = driver.page_source
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ville_slug = ville_scraped.replace(" ", "_")
            filename = f"{code_commun}_{ville_slug}_page{page}_{timestamp}.html"

            folder = "logicimmo"
            os.makedirs(folder, exist_ok=True)
            file_path = os.path.join(folder, filename)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(page_html)

            print(f"✅ HTML sauvegardé localement : {file_path}")

            try:
                s3_client.upload_file(file_path, S3_BUCKET, filename)
                print(f"✅ Upload MinIO : {filename}")
            except Exception as e:
                print(f"❌ Erreur upload S3 : {e}")

        except Exception as e:
            print(f"❌ Erreur sur la page {page} : {e}")

driver.quit()
print("\n✅ Tous les scrapes sont terminés.")
