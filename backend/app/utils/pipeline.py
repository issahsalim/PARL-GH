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
from app.utils.progress import PipelineProgress


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
    def safe_word_count(text):
        return len(text.split()) if text else 0

    full_text = "\n".join(p["text"] for p in pages)

    # Page boundaries
    page_boundaries = []
    cursor = 0
    for p in pages:
        page_boundaries.append((p["page_number"], cursor))
        cursor += len(p["text"]) + 1

    # Improved speaker patterns for Ghana Hansards - More flexible
    # Matches: Hon. Name:, Mr. Name:, THE SPEAKER:, Mr. Speaker:, Name (NDC - Const):, etc.
    speaker_patterns = [
        # Pattern for "Title Name (Info):" or "Name (Info):" or "Title Name:"
        r"(?:(Hon\.|Mr\.|Ms\.|Mrs\.|THE\s+SPEAKER|Minister\s+for\s+[A-Za-z\s]+)\s+)?([A-Z][A-Za-z\s\.-]+)(?:\s*\((.*?)\))?\s*:",
        # Pattern for specific roles like "Mr First Deputy Speaker:"
        r"((?:Mr\.|Hon\.)?\s*(?:First|Second)?\s*(?:Deputy)?\s*Speaker)\s*:",
    ]

    combined_pattern = "(" + "|".join(speaker_patterns) + ")"
    matches = list(re.finditer(combined_pattern, full_text))

    if not matches:
        print("⚠️ No speakers found in text.")
        return

    default_topic = Topic.objects.filter(session=session).first()
    
    segments_created = 0

    for i, match in enumerate(matches):
        full_match = match.group(1).strip()
        
        name = "Unknown"
        role = ""
        party = ""
        constituency = ""

        # Using the flexible Pattern 1
        if match.group(2) or match.group(3):
            title = match.group(2).strip() if match.group(2) else ""
            raw_name = match.group(3).strip() if match.group(3) else ""
            extra_info = match.group(4).strip() if match.group(4) else ""
            
            name = raw_name
            if "Minister" in title:
                role = title
            elif "Speaker" in raw_name or "Speaker" in title:
                role = "Speaker"
                name = "THE SPEAKER"
            elif "MP" in extra_info:
                role = "MP"
            
            # Try to parse party and constituency from extra_info (NDC - Zabzugu or NDC ? Zabzugu)
            if extra_info:
                # Split by common separators (-, ?, , |)
                parts = re.split(r'[-\?|]', extra_info)
                if len(parts) >= 1:
                    party = parts[0].strip()
                if len(parts) >= 2:
                    constituency = parts[1].strip()

        # Specific role match
        elif match.group(5):
            name = "THE SPEAKER"
            role = match.group(5).strip()

        # Clean up
        if name == "Unknown" and full_match:
            name = full_match.replace(":", "").strip()

        seg_start = match.end()
        seg_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        segment_text = full_text[seg_start:seg_end].strip()

        if not segment_text or len(segment_text) < 10:
            continue

        start_page = 1
        for page_num, pos in page_boundaries:
            if pos <= seg_start:
                start_page = page_num
            else:
                break

        speaker, _ = Speaker.objects.get_or_create(
            name=name,
            defaults={
                "role": role,
                "party": party,
                "constituency": constituency
            }
        )
        
        # Prevent duplicate segments
        exists = DebateSegment.objects.filter(
            session=session,
            speaker=speaker,
            start_page=start_page,
            text__startswith=segment_text[:100]
        ).exists()

        if not exists:
            DebateSegment.objects.create(
                session=session,
                speaker=speaker,
                topic=default_topic,
                text=segment_text,
                start_page=start_page,
                word_count=safe_word_count(segment_text)
            )
            segments_created += 1

    print(f"✅ Extracted {segments_created} segments and {Speaker.objects.filter(debatesegment__session=session).distinct().count()} unique speakers.")




# =========================================================
# 5. Process ONE PDF (SAFE)
# =========================================================
def process_pdf(hansard_file):
    print(f"📄 Processing: {hansard_file.file_name}")

    if Session.objects.filter(pdf_file=hansard_file).exists():
        print("⏭️  Already processed, skipping")
        return

    PipelineProgress.update(f"Extracting text from: {hansard_file.file_name}")
    pages = extract_text_from_pdf(hansard_file.file_path)
    session = get_or_create_session(hansard_file)

    full_text = "\n".join(p["text"] for p in pages)

    # ✅ 1. CREATE TOPICS FIRST
    PipelineProgress.update(f"Identifying topics in: {hansard_file.file_name}")
    create_topics_for_session(session, full_text)

    # ✅ 2. THEN extract speakers & segments
    PipelineProgress.update(f"Extracting speakers and debate segments...")
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

        PipelineProgress.update("Processing downloaded files...")
        processed = 0
        total_files = files.count()
        
        for i, hansard in enumerate(files):
            if not os.path.exists(hansard.file_path):
                continue

            try:
                PipelineProgress.update(f"Processing ({i+1}/{total_files}): {hansard.file_name}", current=i+1, total=total_files)
                process_pdf(hansard)
                processed += 1
            except Exception as e:
                print(f"❌ Error processing {hansard.file_name}: {str(e)}")
                continue

        PipelineProgress.clear()


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

