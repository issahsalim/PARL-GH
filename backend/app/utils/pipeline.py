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

from app.utils.hansards_downloader import download_new_hansards

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

    topics.sort(key=lambda x: x[1])
    return topics


def create_topics_for_session(session, full_text):
    extracted = extract_topics(full_text)

    topics = []
    for name, _ in extracted:
        topic, _ = Topic.objects.get_or_create(
            session=session,
            name=name
        )
        topics.append(topic)

    return topics


# =========================================================
# 1. Extract text from PDF
# =========================================================
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



# =========================================================
# 2. Extract date from filename
# =========================================================
def extract_date_from_filename(filename):
    """
    Example:
    21st November, 2025.pdf → 2025-11-21
    """
    cleaned = filename.replace(".pdf", "").replace(",", "")
    cleaned = re.sub(r"(st|nd|rd|th)", "", cleaned)
    return datetime.strptime(cleaned, "%d %B %Y").date()


# =========================================================
# 3. Create or Get Session (SAFE)
# =========================================================
def get_or_create_session(hansard_file):
    sitting_date = extract_date_from_filename(hansard_file.file_name)
    title = hansard_file.file_name.replace(".pdf", "")

    session, created = Session.objects.get_or_create(
        sitting_date=sitting_date,
        defaults={
            "title": title,
            "pdf_file": hansard_file
        }
    )

    # Attach PDF if missing
    if not session.pdf_file:
        session.pdf_file = hansard_file
        session.save()

    return session


# =========================================================
# 4. Speaker & Segment Extraction (SAFE)
# =========================================================
def extract_speakers_and_segments(session, pages):

    WPM = 130  # analytics later

    def safe_word_count(text):
        return len(text.split()) if text else 0

    full_text = "\n".join(p["text"] for p in pages)

    # Page boundaries
    page_boundaries = []
    cursor = 0
    for p in pages:
        page_boundaries.append((p["page_number"], cursor))
        cursor += len(p["text"]) + 1

    speaker_patterns = [
        r"(Hon\.\s+[A-Z][A-Za-z\s\.-]+)\s*\((.*?)\):",
        r"(Mr\.|Ms\.|Mrs\.)\s+[A-Z][A-Za-z\s\.-]+:",
        r"(THE SPEAKER):",
        r"[A-Z][A-Za-z\s\.-]+ \(MP\):"
    ]

    combined_pattern = "(" + "|".join(speaker_patterns) + ")"
    matches = list(re.finditer(combined_pattern, full_text))

    if not matches:
        return

    default_topic = Topic.objects.filter(session=session).first()

    for i, match in enumerate(matches):
        speaker_name = match.group(1).strip() if match.group(1) else "Unknown"
        role = match.group(2).strip()[:100] if match.lastindex and match.lastindex >= 2 else ""

        seg_start = match.end()
        seg_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        segment_text = full_text[seg_start:seg_end].strip()

        if not segment_text:
            continue

        # Page detection
        start_page = None
        for page_num, pos in page_boundaries:
            if pos <= seg_start:
                start_page = page_num
            else:
                break

        speaker, _ = Speaker.objects.get_or_create(
            name=speaker_name,
            defaults={"role": role}
        )

        # 🔒 Prevent duplicate segments
        exists = DebateSegment.objects.filter(
            session=session,
            speaker=speaker,
            start_page=start_page,
            text__startswith=segment_text[:100]
        ).exists()

        if exists:
            continue

        DebateSegment.objects.create(
            session=session,
            speaker=speaker,
            topic=default_topic,
            text=segment_text,
            start_page=start_page,
            word_count=safe_word_count(segment_text)
        )


# =========================================================
# 5. Process ONE PDF (SAFE)
# =========================================================
def process_pdf(hansard_file):
    print(f"📄 Processing: {hansard_file.file_name}")

    if Session.objects.filter(pdf_file=hansard_file).exists():
        print("⏭️  Already processed, skipping")
        return

    pages = extract_text_from_pdf(hansard_file.file_path)
    session = get_or_create_session(hansard_file)

    full_text = "\n".join(p["text"] for p in pages)

    # ✅ 1. CREATE TOPICS FIRST
    create_topics_for_session(session, full_text)

    # ✅ 2. THEN extract speakers & segments
    extract_speakers_and_segments(session, pages)

    print(f"✅ Completed: {session.title}")


# =========================================================
# 6. MAIN PIPELINE (ENTRY POINT)
# =========================================================
def run_hansard_pipeline(folder_path="ghana_hansards"):
    """
    Run the hansard pipeline with error handling
    Returns: dict with status and message
    """ 

    try:
        print("\n🚀 Running Hansard Pipeline")

        # 🔽 AUTO DOWNLOAD FIRST
        download_result = download_new_hansards(limit=10)
        
        # Check if download was successful
        if not download_result.get('success', False) and download_result.get('downloaded', 0) == 0:
            error_msg = download_result.get('message', 'Unknown error during download')
            print(f"⚠️ Download Error: {error_msg}")
            return {
                'success': False,
                'error': download_result.get('error', 'Download Failed'),
                'message': error_msg
            }
        
        new_files = download_result.get('downloaded', 0)
        print(f"📥 New PDFs downloaded: {new_files}")

        files = HansardFile.objects.all().order_by("date_downloaded")

        processed = 0
        for hansard in files:
            if not os.path.exists(hansard.file_path):
                continue

            try:
                process_pdf(hansard)
                processed += 1
            except Exception as e:
                print(f"❌ Error processing {hansard.file_name}: {str(e)}")
                continue

        result_msg = f"\n🎉 Pipeline finished successfully\n✅ Files processed: {processed}\n📥 Files downloaded: {new_files}"
        print(result_msg)

        return {
            'success': True,
            'message': f'Pipeline completed! Downloaded {new_files} file(s) and processed {processed} file(s).',
            'downloaded': new_files,
            'processed': processed
        }
    
    except Exception as e:
        error_msg = f"Unexpected error in pipeline: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': 'Pipeline Error',
            'message': error_msg
        }

