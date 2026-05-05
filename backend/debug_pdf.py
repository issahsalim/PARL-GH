import os
import django
import pdfplumber
import sys

# Set up Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from app.models import HansardFile

h = HansardFile.objects.first()
if h:
    print(f"Checking file: {h.file_name}")
    print(f"Path: {h.file_path}")
    if os.path.exists(h.file_path):
        with pdfplumber.open(h.file_path) as pdf:
            # Check a few pages
            for i in range(min(10, len(pdf.pages))):
                text = pdf.pages[i].extract_text()
                if text:
                    print(f"--- PAGE {i+1} ---")
                    print(text[:800])
                    print("------------------")
    else:
        print("File path does not exist!")
else:
    print("No HansardFile found in DB.")
