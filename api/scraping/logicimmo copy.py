import time
import os
import re
import argparse
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import boto3
from botocore.client import Config
import sys

def configure_console_encoding():
    """Fix Windows console encoding issues"""
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

def scrape_logicimmo(base_url, max_pages=5):
    configure_console_encoding()
    
    # ───── Browser Setup ─────
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 15)

    # ───── MinIO/S3 Setup ─────
    S3_ENDPOINT = 'http://localhost:9000'
    S3_ACCESS_KEY = 'minioadmin'
    S3_SECRET_KEY = 'minioadmin123'
    S3_BUCKET = 'web-scraping'

    s3_client = boto3.client('s3',
                          endpoint_url=S3_ENDPOINT,
                          aws_access_key_id=S3_ACCESS_KEY,
                          aws_secret_access_key=S3_SECRET_KEY,
                          config=Config(signature_version='s3v4'),
                          region_name='us-east-1')

    try:
        s3_client.head_bucket(Bucket=S3_BUCKET)
    except Exception as e:
        print(f"Bucket check failed: {e}")
        try:
            s3_client.create_bucket(Bucket=S3_BUCKET)
            print(f"Created bucket: {S3_BUCKET}")
        except Exception as create_error:
            print(f"Failed to create bucket: {create_error}")
            return

    # ───── Extract Location Code ─────
    try:
        parsed_url = urlparse(base_url)
        query_params = parse_qs(parsed_url.query)
        location_code = query_params.get('locations', ['unknown'])[0]
        print(f"Location code extracted: {location_code}")
    except Exception as e:
        print(f"Failed to parse URL: {e}")
        location_code = "unknown"

    for page in range(1, max_pages + 1):
        try:
            # Build URL with page parameter
            full_url = f"{base_url}&page={page}" if "?" in base_url else f"{base_url}?page={page}"
            print(f"\nPage {page} - URL: {full_url}")
            
            driver.get(full_url)
            time.sleep(5)

            # Close cookie banner (only on first page)
            if page == 1:
                try:
                    cookie_button = wait.until(
                        EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button")))
                    cookie_button.click()
                    time.sleep(2)
                except Exception:
                    pass

            # Extract city name from title
            try:
                title_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1[data-testid='serp-title-variant-b-testid']")))
                title_text = title_element.text.strip()
                city = "unknown"
                if "–" in title_text:
                    match = re.search(r"–\s*(.*?),", title_text)
                    if match:
                        city = match.group(1).strip()
            except Exception:
                city = "unknown"

            # Save HTML
            page_html = driver.page_source
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{location_code}_{city.replace(' ', '_')}_page{page}_{timestamp}.html"
            folder = "logicimmo"
            os.makedirs(folder, exist_ok=True)
            file_path = os.path.join(folder, filename)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(page_html)

            # Upload to S3
            try:
                s3_client.upload_file(file_path, S3_BUCKET, filename)
                print(f"File uploaded to S3: {filename}")
            except Exception as s3_error:
                print(f"S3 upload error (saved locally): {str(s3_error)[:200]}")

        except Exception as e:
            print(f"Error on page {page}: {str(e)[:200]}")
            continue

    driver.quit()
    print("\nScraping completed.")

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description='LogicImmo Scraper')
        parser.add_argument('url', help='Base URL to scrape')
        parser.add_argument('--pages', type=int, default=2, help='Number of pages to scrape')
        
        args = parser.parse_args()
        
        print(f"Starting scraping: {args.url}")
        print(f"Pages to scrape: {args.pages}")
        
        scrape_logicimmo(args.url, args.pages)
    except Exception as e:
        print(f"Fatal error: {str(e)[:200]}")
        sys.exit(1)