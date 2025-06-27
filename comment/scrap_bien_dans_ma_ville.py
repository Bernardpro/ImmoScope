import requests
import pandas as pd
from functools import lru_cache
from bs4 import BeautifulSoup as bs
from minio import Minio
import io
from dotenv import load_dotenv
import os
import urllib3
http_client = urllib3.PoolManager(
    cert_reqs="CERT_NONE",
    assert_hostname=False,
)
# ─────────────────── load env vars ────────────── #
load_dotenv()
access_key = os.getenv("MINIO_ACCESS_KEY")
secret_key = os.getenv("MINIO_SECRET_KEY")
# ─────────────────── utility: load the list of communes ────────────── #
minio_client = Minio(
    "35.241.212.205",                
    access_key=access_key,     
    secret_key=secret_key,     
    secure=True,
    http_client=http_client                  
)

def load_communes(path: str = "communes.csv") -> list[str]:
    """
    Return the 'libelle' column as a Python list.
    The CSV is expected to have this column; index col is ignored.
    """
    df = pd.read_csv(path, sep=",", header=0, encoding="utf-8")
    return df
def format_commune_name(name: str) -> str:
    """
    Format the commune name to match the expected format in the URL.
    """
    return name.replace(" ", "-").replace("'", "").lower().replace("é", "e").replace("è", "e").replace("ê", "e").replace("ë", "e").replace("ô", "o").replace("ç", "c").replace("à", "a").replace("â", "a").replace("î", "i").replace("ï", "i").replace("û", "u").replace("ü", "u").replace("ô", "o").replace("œ", "oe").replace("æ", "ae").replace("ÿ", "y")
def format_urls():
    
    communes = load_communes()
    communes["ville-code"] = communes['libelle'].apply(format_commune_name) + "-" + communes['code'].astype(str) 
    communes["url"] = "https://www.bien-dans-ma-ville.fr/" + communes["ville-code"]  + '/avis.html'

    communes.to_csv("url-bien-dans-ma-ville.csv", index=False, encoding="utf-8") 

# ─────────────────── utility: load the list of urls  ────────────── #
def load_urls(path: str = "url-bien-dans-ma-ville.csv") -> list[str]:
    """
    Return the 'url' column as a Python list.
    The CSV is expected to have this column; index col is ignored.
    """
    df = pd.read_csv(path, sep=",", index_col=0, encoding="utf-8")
    return df["url"].dropna().tolist()

def parse_html(html_content: str) -> str:
    """
    Parse the HTML content and extract the desired information.
    """
    soup = bs(html_content, 'html.parser')
    # Example: Extract the title of the page
    commentaires = soup.find_all('div', class_='commentaire')
    return commentaires

def upload_soup_to_minio(minio_client: Minio, object_name: str, soup: bs, bucket: str="comment"):
    """
    Upload le contenu HTML d'un objet BeautifulSoup dans MinIO.
    """
    html_str = str(soup)  # ou soup.prettify()
    data = io.BytesIO(html_str.encode("utf-8"))
    minio_client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=data,
        length=len(html_str.encode("utf-8")),
        content_type="text/html"
    )

def main():
    bucket = "comment"

    # 1. Vérifier s'il existe, sinon le créer
    if not minio_client.bucket_exists(bucket):
        print(f"Bucket '{bucket}' absent : je le crée.")
        minio_client.make_bucket(bucket)
    else:
        print(f"Bucket '{bucket}' déjà présent.")
    urls = load_urls()[107:]
    for url in urls:
        try:
            # Access the URL
            response = requests.get(url)
            # Check if the request was successful
            if response.status_code == 200:
                soup = bs(response.content, 'html.parser')
                pagination = soup.find_all('div', class_='pagination')
                upload_soup_to_minio(minio_client, url.split("/")[-2] + ".html" , soup)
                if pagination:
                    # Extract the number of pages
                    response2 = requests.get(f"{url}?page=2")
                    soup2 = bs(response2.content, 'html.parser')
                    upload_soup_to_minio(minio_client, url.split("/")[-2]+"-page=2.html" , soup2)
                else:
                    print(f"No pagination found for {url}")
                print(f"Successfully accessed {url}")
            else:
                print(f"Failed to access {url}")
        except Exception as e:
            print(f"Error occurred while accessing {url}: {e}")

if __name__ == "__main__":
    main()