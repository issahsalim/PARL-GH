import pdfplumber
import re

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts and cleans text from a PDF file.
    """
    text_chunks = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)

    text = "\n".join(text_chunks)

    # Clean text: remove multiple line breaks, page numbers, hyphen breaks
    text = re.sub(r"-\n", "", text)          # fix broken words
    text = re.sub(r"\n{2,}", "\n\n", text)  # collapse multiple line breaks
    text = re.sub(r"\bPage\s+\d+\b", "", text, flags=re.IGNORECASE)  # remove page numbers

    return text.strip()

from datetime import datetime
from app.models import Session, HansardFile

def create_session_from_hansardfile(hf: HansardFile):
    """
    Create a Session record from a HansardFile.
    Tries to parse date from filename like '21st November, 2025.pdf'.
    """
    # Remove file extension
    base_name = hf.file_name.rsplit(".", 1)[0]

    # Clean ordinal suffixes (st, nd, rd, th)
    cleaned = base_name.replace(",", "").replace("st", "").replace("nd", "").replace("rd", "").replace("th", "")

    # Try common date formats
    parsed_date = None
    for fmt in ("%d %B %Y", "%d %b %Y", "%Y-%m-%d"):
        try:
            parsed_date = datetime.strptime(cleaned.strip(), fmt).date()
            break
        except ValueError:
            continue

    # Fallback to today if date cannot be parsed
    if not parsed_date:
        parsed_date = datetime.today().date()

    # Create Session if it doesn't exist
    session, created = Session.objects.get_or_create(
        sitting_date=parsed_date,
        defaults={
            "title": base_name,
            "pdf_file": hf
        }
    )

    return session, created


 
import re
from app.models import Speaker, DebateSegment

def extract_speakers_and_segments(session, text):
    """
    Extracts speakers and debate segments from Hansard text.
    Saves segments into DebateSegment model.
    
    Args:
        session: Session object (already created)
        text: Full text from PDF
    """
    
    MAX_NAME_LENGTH = 255  # truncate speaker names to fit DB

    # Regex pattern for Ghana Parliament speaker lines
    speaker_pattern = r'((?:Hon\.|Mr\.|Mrs\.|Ms\.|Madam|Mr Speaker|Madam Speaker)[^\n:]{0,500}):'
    
    # Split text based on speaker lines
    splits = re.split(speaker_pattern, text)
    
    # Skip first empty item if exists
    if not splits[0].strip():
        splits = splits[1:]
    
    # Process in pairs: speaker -> text
    for i in range(0, len(splits)-1, 2):
        speaker_name = splits[i].strip()[:MAX_NAME_LENGTH]  # truncate
        segment_text = splits[i+1].strip()
        
        if not segment_text:
            continue
        
        # Get or create Speaker object
        speaker_obj, _ = Speaker.objects.get_or_create(name=speaker_name)
        
        # Save DebateSegment
        DebateSegment.objects.create(
            session=session,
            speaker=speaker_obj,
            text=segment_text,
        )
