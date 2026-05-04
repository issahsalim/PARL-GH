import pdfplumber
import os

pdf_path = "ghana_hansards/9th March, 2026.pdf"
if os.path.exists(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        # Pages 4 to 6
        for i in range(3, min(6, len(pdf.pages))):
            text += f"--- PAGE {i+1} ---\n"
            text += pdf.pages[i].extract_text() + "\n\n"
        print(text)
else:
    print("PDF not found")
