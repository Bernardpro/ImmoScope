import pandas as pd
import subprocess
import os
import sys
from multiprocessing import Pool

def scrape_city(city_data):
    """
    Fonction pour scraper une ville individuelle
    """
    try:
        ville, seloger_url, code_commun = city_data
        logicimmo_url = seloger_url.replace("www.seloger.com", "www.logic-immo.com")
        
        print(f"\n🎯 Début du scraping pour {ville}")
        print(f"🔗 URL : {logicimmo_url}")
        print(f"📍 Code commune : {code_commun}")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logicimmo_path = os.path.join(current_dir, "logicimmo.py")
        
        result = subprocess.run(
            [sys.executable, logicimmo_path, logicimmo_url, "--pages", "1"],
            capture_output=True,
            text=True,
            cwd=current_dir
        )
        
        if result.returncode == 0:
            print(f"✅ Succès pour {ville}")
            return True
        else:
            print(f"❌ Échec pour {ville}")
            print(f"Erreurs : {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur majeure pour {ville}: {e}")
        return False

def main():
    try:
        # Charger le CSV
        csv_path = os.path.join("api", "scraping", "villes.csv")
        if not os.path.exists(csv_path):
            print(f"❌ Fichier CSV non trouvé : {csv_path}")
            return
            
        df = pd.read_csv(csv_path)
        print(f"📊 CSV chargé avec {len(df)} villes")
        
        # Prendre les 10 premières villes
        top_10 = df.head(10)
        cities_data = [(row["libelle"], row["url"], row["code"]) for _, row in top_10.iterrows()]
        
        # Configurer le pool de workers
        num_workers = min(4, len(cities_data))  # 4 workers max pour éviter le surchargement
        print(f"\n🚀 Lancement du scraping avec {num_workers} workers...")
        
        with Pool(num_workers) as pool:
            results = pool.map(scrape_city, cities_data)
        
        success_rate = sum(results) / len(results) * 100
        print(f"\n📊 Résumé : {success_rate:.2f}% de réussite")
        print("✅ Tâches terminées")
        
    except Exception as e:
        print(f"❌ Erreur dans main() : {e}")

if __name__ == "__main__":
    print(f"🐍 Python : {sys.executable}")
    print(f"📁 Répertoire : {os.getcwd()}")
    main()