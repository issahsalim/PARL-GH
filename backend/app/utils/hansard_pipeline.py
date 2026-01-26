import os
import re
import pdfplumber
from datetime import datetime
from app.models import (
    HansardFile,
    Session,
    Speaker,
    Topic,
    DebateSegment
)

# ------------------------------------------
# 1. Extract text from PDF
# ------------------------------------------

def extract_text_from_pdf(path):
    pages = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            pages.append({
                "page_number": i + 1,
                "text": text
            })
    return pages



# ------------------------------------------
# 2. Extract date from filename
# ------------------------------------------
def extract_date_from_filename(filename):
    """
    Example filename:
    21st November, 2025.pdf → 2025-11-21
    """
    cleaned = filename.replace(".pdf", "").replace(",", "")

    # Remove suffix: "st", "nd", "rd", "th"
    cleaned = re.sub(r"(st|nd|rd|th)", "", cleaned)

    return datetime.strptime(cleaned, "%d %B %Y").date()


# ------------------------------------------
# 3. Create HansardFile + Session
# ------------------------------------------
def create_session_from_pdf(path):
    file_name = os.path.basename(path)
    sitting_date = extract_date_from_filename(file_name)

    # Save HansardFile
    hansard = HansardFile.objects.create(
        file_name=file_name,
        file_path=path
    )

    # Session title = filename without .pdf
    title = file_name.replace(".pdf", "")

    session = Session.objects.create(
        title=title,
        sitting_date=sitting_date,
        pdf_file=hansard
    )

    return session

# extract topics 
def extract_topics(text):
    """
    Detect major debate headings in the Hansard.
    Returns a list of (topic_name, start_index)
    """

    topic_patterns = [
        r"STATEMENTS",
        r"MINISTERIAL STATEMENTS",
        r"QUESTIONS",
        r"URGENT QUESTIONS",
        r"PUBLIC BUSINESS",
        r"PAPERS",
        r"MOTIONS",
        r"COMMITTEE REPORTS",
        r"RESOLUTIONS",
    ]

    topics = []
    for pattern in topic_patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            topics.append((match.group().upper(), match.start()))

    # Sort by where they appear in the text
    topics.sort(key=lambda x: x[1])

    return topics

# ------------------------------------------
# 4. Extract Speakers + Debate Segments
# ------------------------------------------

def extract_speakers_and_segments(session, pages):

    # Estimated Words Per Minute for analytics later
    WPM = 130  

    # Safe word counter
    def safe_word_count(text):
        if not text:
            return 0
        return len(text.split())

    # Merge pages into full text
    full_text = "\n".join(p["text"] for p in pages)

    # Track where each page starts
    page_boundaries = []
    cursor = 0
    for p in pages:
        page_boundaries.append((p["page_number"], cursor))
        cursor += len(p["text"]) + 1

    # Speaker pattern 
    speaker_patterns = [
        r"(Hon\.\s+[A-Z][A-Za-z\s\.-]+)\s*\((.*?)\):",
        r"(Mr\.|Ms\.|Mrs\.)\s+[A-Z][A-Za-z\s\.-]+:",
        r"(THE SPEAKER):",
        r"[A-Z][A-Za-z\s\.-]+ \(MP\):"
    ]

    combined_pattern = "(" + "|".join(speaker_patterns) + ")"

    matches = list(re.finditer(combined_pattern, full_text))
    
    # Assignment: currently no NLP topics → placeholder
    default_topic = None
    if Topic.objects.filter(session=session).exists():
        default_topic = Topic.objects.filter(session=session).first()

    for i, match in enumerate(matches):
        speaker_name = match.group(1).strip() if match.group(1) else "Unknown"
        role = match.group(2).strip() if match.group(2) else ""

        seg_start = match.end()

        if i + 1 < len(matches):
            seg_end = matches[i + 1].start()
        else:
            seg_end = len(full_text)

        segment_text = full_text[seg_start:seg_end].strip()

        # Determine page number
        segment_page = None
        for page_num, start_pos in page_boundaries:
            if start_pos <= seg_start:
                segment_page = page_num
            else:
                break

        # Safe word count
        wc = safe_word_count(segment_text)

        # Create Speaker
        speaker, _ = Speaker.objects.get_or_create(
            name=speaker_name,
            defaults={"role": role[:100]}
        )

        # Create DebateSegment
        DebateSegment.objects.create(
            session=session,
            speaker=speaker,
            topic=default_topic,   
            text=segment_text,
            start_page=segment_page,
            word_count=wc
        )

# ------------------------------------------
# 5. FULL PIPELINE — Run on a single PDF
# ------------------------------------------
def process_pdf(path):
    print(f"\n📄 Processing PDF: {path}")

    session = create_session_from_pdf(path)
    text = extract_text_from_pdf(path)

    extract_speakers_and_segments(session, text)

    print(f"✅ Completed: {session.title}")
    return session


# ------------------------------------------
# 6. Run pipeline on an entire folder
# ------------------------------------------
folder_name="ghana_hansards" 
def process_folder(folder_path):
    print(f"\n📁 Running pipeline on folder: {folder_path}")

    for file in os.listdir(folder_path):
        if file.lower().endswith(".pdf"):
            full_path = os.path.join(folder_path, file)
            process_pdf(full_path)

    print("\n🎉 ALL PDFS PROCESSED SUCCESSFULLY!")


