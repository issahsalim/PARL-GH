import os
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup

from app.models import HansardFile


PAGE_URL = "https://www.parliament.gh/docs?type=HS&P=0"
BASE_DOWNLOAD = "https://www.parliament.gh/epanel/docs/"
DOWNLOAD_FOLDER = "ghana_hansards"


def download_new_hansards(limit=10, delay=1):
    """
    Download new hansard PDFs from parliament.gh
    Returns: dict with status, message, and downloaded count
    """
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    try:
        # Try to connect to parliament.gh with timeout
        response = requests.get(PAGE_URL, timeout=30)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': 'Connection Timeout',
            'message': 'The Parliament website is taking too long to respond. Please try again in a few moments.',
            'downloaded': 0
        }
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'error': 'Connection Error',
            'message': 'Unable to connect to parliament.gh. Please check your internet connection or try again later.',
            'downloaded': 0
        }
    except requests.exceptions.HTTPError as e:
        return {
            'success': False,
            'error': 'HTTP Error',
            'message': f'Parliament website returned an error (HTTP {response.status_code}). Please try again later.',
            'downloaded': 0
        }
    except Exception as e:
        return {
            'success': False,
            'error': 'Unexpected Error',
            'message': f'An unexpected error occurred: {str(e)}',
            'downloaded': 0
        }

    try:
        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.find_all("tr")

        downloaded = 0

        for row in rows:
            if downloaded >= limit:
                break

            onclick = row.get("onclick")
            if not onclick or "showPDF" not in onclick:
                continue

            try:
                pdf_path = onclick.split("'")[1]
            except IndexError:
                continue

            file_name = pdf_path.split("/")[-1]

            # 🔒 Skip if already in DB
            if HansardFile.objects.filter(file_name=file_name).exists():
                continue

            encoded = urllib.parse.quote(pdf_path)
            pdf_url = BASE_DOWNLOAD + encoded

            local_path = os.path.join(DOWNLOAD_FOLDER, file_name)

            try:
                r = requests.get(pdf_url, timeout=60)
                if r.content[:4] != b"%PDF":
                    continue

                with open(local_path, "wb") as f:
                    f.write(r.content)

                HansardFile.objects.create(
                    file_name=file_name,
                    file_path=local_path.replace("\\", "/"),
                    file_size=len(r.content),
                )

                downloaded += 1
                time.sleep(delay)
            except requests.exceptions.RequestException as e:
                # Log individual file download errors but continue with others
                print(f"Error downloading {file_name}: {str(e)}")
                continue

        return {
            'success': True,
            'message': f'Successfully downloaded {downloaded} hansard file(s).',
            'downloaded': downloaded
        }
    except Exception as e:
        return {
            'success': False,
            'error': 'Processing Error',
            'message': f'Error processing hansard files: {str(e)}',
            'downloaded': 0
        }
