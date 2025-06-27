from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import re

# Configuration du navigateur
options = Options()
options.add_argument('--headless')  
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-notifications')
options.add_argument('--disable-popup-blocking')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')

try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 15)
    print("✅ Driver initialisé avec succès")
except Exception as e:
    print(f"❌ Erreur lors de l'initialisation du driver: {e}")
    exit(1)

url = "https://www.logic-immo.com/classified-search?distributionTypes=Buy,Buy_Auction,Compulsory_Auction&estateTypes=House,Apartment&locations=AD08FR28950&order=Default&m=homepage_new_search_classified_search_result"
print(f"📌 Accès à l'URL: {url}")

try:
    driver.get(url)
    print("✅ Page chargée")
except Exception as e:
    print(f"❌ Erreur lors du chargement de la page: {e}")
    driver.quit()
    exit(1)

# Attendre que la page soit complètement chargée
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

all_properties = []

try:
    ads = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='serp-core-classified-card-testid']")
    if not ads:
        print("❌ Aucune annonce trouvée")
    else:
        print(f"✅ {len(ads)} annonces trouvées")
        for i, ad in enumerate(ads[:15]):  
            try:
                button = ad.find_element(By.CSS_SELECTOR, '[data-testid="card-mfe-covering-link-testid"]')
                info = button.get_attribute("title")
             
                
                property_data = {
                    "raw_title": info,
                  
                }

                match = re.match(r"(.*?) - (.*?) - ([\d\s]+€) - (.*)", info)
                if match:
                    property_data["type"] = match.group(1).strip()
                    property_data["ville"] = match.group(2).strip()
                    property_data["prix"] = match.group(3).strip()
                    property_data["details"] = match.group(4).strip()
                else:
                    print(f"⚠️ Format inattendu pour le titre: {info}")

                all_properties.append(property_data)

                print(f"\n🏡 Annonce #{i+1}")
                print(json.dumps(property_data, indent=4, ensure_ascii=False))
                print("-" * 50)

            except Exception as e:
                print(f"❌ Erreur lors de l'extraction de l'annonce #{i+1}: {e}")

    # Sauvegarde dans un fichier JSON
    with open("logic_immo_properties.json", "w", encoding="utf-8") as f:
        json.dump(all_properties, f, ensure_ascii=False, indent=4)
    print(f"✅ {len(all_properties)} annonces sauvegardées dans logic_immo_properties.json")

except Exception as e:
    print(f"❌ Erreur principale: {e}")

# Capture d’écran finale pour debug
try:
    driver.save_screenshot("logic_immo_debug_final.png")
    print("✅ Capture d’écran finale enregistrée")
except Exception as e:
    print(f"❌ Erreur lors de la capture finale: {e}")

# Fermeture du navigateur
driver.quit()
print("✅ Navigateur fermé")
