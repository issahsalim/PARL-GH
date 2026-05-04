import pdfplumber
import os

pdf_path = "ghana_hansards/9th March, 2026.pdf"
if os.path.exists(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        # Extract first 3 pages
        text = ""
        for i in range(min(3, len(pdf.pages))):
            text += pdf.pages[i].extract_text() + "\n\n"
        print(text[:2000])
else:
    print("PDF not found")
