# AI Summarization Feature - Ghana Hansards

## Overview

The AI Summarization feature provides intelligent, AI-powered summaries of parliamentary debate content using Hugging Face's **BART (Bidirectional and Auto-Regressive Transformers)** model. This feature is designed to help users quickly understand long parliamentary transcripts, debates, and motions without reading the entire content.

## Key Features

### 1. **AI-Powered Summarization**
- Uses state-of-the-art `facebook/bart-large-cnn` model from Hugging Face Transformers
- Generates concise, coherent summaries of long texts
- True abstractive summarization (not just truncation)
- Supports both GPU and CPU inference

### 2. **Structured Data Extraction**
Automatically extracts and presents:
- **Speakers Mentioned**: Lists all participants in the debate
- **Motions Discussed**: Identifies key motions and proposals
- **Outcomes/Decisions**: Extracts final decisions and resolutions

### 3. **Multiple Summarization Types**
- **Custom Text**: Summarize any parliamentary text you paste
- **Single Segment**: Summarize individual debate segments
- **Full Session**: Summarize entire parliamentary sessions
- **API Endpoint**: Programmatic access for integration

### 4. **Accessibility**
- No authentication required
- Available to all users
- Responsive design for mobile and desktop
- Clean, intuitive interface

### 5. **Summary History**
- All summaries are stored in the database
- Browse and filter previous summaries
- View detailed summary analysis
- Track reduction percentage and word counts

## Installation & Setup

### Prerequisites
```bash
# Required packages
pip install transformers torch
```

### Quick Start

1. **Ensure packages are installed**:
   ```bash
   cd backend
   pip install -r requirements.txt
   pip install transformers torch
   ```

2. **Run migrations** (for Summary model):
   ```bash
   python manage.py makemigrations app
   python manage.py migrate
   ```

3. **Start the development server**:
   ```bash
   python manage.py runserver
   ```

4. **Access the feature**:
   - Navigate to `/summarize/` in your browser
   - Or click "Summarize" in the navigation menu

## Usage

### Method 1: Web Interface - Summarize Custom Text

1. Go to `/summarize/`
2. Paste your parliamentary text
3. (Optional) Add a title
4. Click "Generate Summary"
5. View results with:
   - AI-generated summary
   - Speakers mentioned
   - Motions discussed
   - Outcomes/decisions
   - Word count reduction statistics

### Method 2: Summarize a Debate Segment

1. Navigate to any debate segment detail page
2. Click "Generate Summary" button
3. View the summary instantly

### Method 3: Summarize an Entire Session

1. Go to a session detail page
2. Click "Summarize Session" button
3. System combines all segments and generates a comprehensive summary

### Method 4: View Summary History

1. Go to `/summaries/` or click "View Previous Summaries"
2. Browse all generated summaries
3. Filter by:
   - Content type (Custom, Session, Segment)
   - Related session
4. Click on any summary to view full details

### Method 5: API Access

**Endpoint**: `POST /api/summarize/`

**Request**:
```bash
curl -X POST http://localhost:8000/api/summarize/ \
  -d "text=Your parliamentary text here..."
```

**Response**:
```json
{
  "success": true,
  "summary": "Concise summary of the text...",
  "speakers": ["Mr. Speaker", "Ms. Osei"],
  "motions": ["Motion to adjourn"],
  "outcomes": ["Motion was passed"],
  "word_count_original": 2500,
  "word_count_summary": 450,
  "reduction_percentage": 82
}
```

## Data Models

### Summary Model

```python
class Summary(models.Model):
    # Type of content
    content_type = CharField()  # 'session', 'topic', 'segment', 'custom'
    
    # Foreign Keys
    session = ForeignKey(Session)          # If related to a session
    topic = ForeignKey(Topic)              # If related to a topic
    debate_segment = ForeignKey(DebateSegment)  # If related to a segment
    
    # Content
    original_text = TextField()            # Original unmodified text
    summary_text = TextField()             # AI-generated summary
    
    # Structured Data (JSON arrays)
    speakers_mentioned = JSONField()       # List of speakers
    motions = JSONField()                  # List of motions
    outcomes = JSONField()                 # List of outcomes
    
    # Metadata
    original_word_count = IntegerField()   # Word count before
    summary_word_count = IntegerField()    # Word count after
    reduction_percentage = FloatField()    # % reduction
    created_by = CharField()               # User who created it
    created_at = DateTimeField()           # When it was created
    updated_at = DateTimeField()           # Last update
```

## Technical Architecture

### Summarization Pipeline

```
Input Text
    ↓
Chunk Text (if >1000 tokens)
    ↓
BART Summarization
    ↓
Entity Extraction (Speakers, Motions, Outcomes)
    ↓
Structured Summary Output
    ↓
Save to Database
```

### Key Components

1. **`app/utils/summarizer.py`**: Main summarization utility
   - `HansardSummarizer` class
   - `summarize_text()`: Basic summarization
   - `summarize_with_structure()`: Structured output
   - Entity extraction methods

2. **`app/models.py`**: Summary database model

3. **`app/views.py`**: Summarization views
   - `summarize_text`: Custom text summarization
   - `summarize_segment`: Segment summarization
   - `summarize_session`: Full session summarization
   - `view_summary`: View stored summary
   - `summaries_list`: Browse summaries
   - `api_quick_summary`: REST API endpoint

4. **`app/forms.py`**: Summarization forms
   - `TextSummaryForm`: For custom text input
   - `SegmentSummaryForm`: For segment selection
   - `SessionSummaryForm`: For session selection

5. **Templates**:
   - `summarize_text.html`: Main summarization interface
   - `summary_result.html`: Results display
   - `summary_detail.html`: Detailed view
   - `summaries_list.html`: Summary history

## URL Routes

```
/summarize/                          - Summarize custom text
/summarize/segment/<id>/             - Summarize a segment
/summarize/session/<id>/             - Summarize a session
/summary/<id>/                       - View summary details
/summaries/                          - List all summaries
/api/summarize/                      - API endpoint
```

## Entity Extraction Details

### Speakers Extraction
Identifies patterns like:
- "Mr. Speaker:", "Ms. Osei:", "Hon. Dr. Smith:"
- ALL CAPS speaker labels
- Extracts full names and titles

### Motions Extraction
Detects:
- "Motion to...", "moved that..."
- "BE IT ENACTED", "BE IT RESOLVED"
- Extracts complete motion text

### Outcomes Extraction
Finds:
- "passed", "rejected", "withdrawn", "amended"
- "agreed to", "defeated", "approved"
- Voting records and decision statements

## Configuration

### Model Parameters

Edit `app/utils/summarizer.py` to adjust:

```python
# Maximum summary length (tokens)
max_length = 150

# Minimum summary length (tokens)
min_length = 50

# Text chunking size (characters)
max_chunk_length = 1000
```

### Device Configuration

The system automatically:
- Uses GPU if available (via CUDA)
- Falls back to CPU if GPU unavailable
- Uses CPU-specific optimizations

Check GPU availability:
```python
import torch
print(torch.cuda.is_available())  # True if GPU available
```

## Performance Considerations

### Typical Metrics
- **Small text** (500 words): ~2-5 seconds
- **Medium text** (2000 words): ~5-15 seconds
- **Large text** (5000+ words): ~20-60 seconds
- **GPU**: 3-5x faster than CPU

### Optimization Tips
1. First summarization downloads the model (~1.6GB) - subsequent calls are fast
2. Use GPU for production deployments
3. Implement caching for frequently summarized content
4. Consider async processing for very long texts

## Error Handling

The system gracefully handles:
- Missing transformers library (fallback to extractive summary)
- Model loading errors
- GPU memory issues
- Invalid input text
- Network interruptions (for model downloads)

## Fallback Behavior

If BART model fails to load:
- System uses **extractive summarization**
- Selects most important sentences based on word count
- Maintains original order of sentences
- Provides basic but functional summary

## Future Enhancements

Potential improvements:
- [ ] Support for other languages (e.g., Twi)
- [ ] Custom training on parliamentary data
- [ ] Real-time streaming summaries
- [ ] Batch processing for multiple documents
- [ ] Summary comparison tools
- [ ] Export summaries as PDF/Word
- [ ] Multi-language entity extraction
- [ ] Integration with notification system

## Troubleshooting

### Issue: BART model not loading
**Solution**: Install PyTorch and transformers
```bash
pip install torch transformers
```

### Issue: Out of memory errors
**Solution**: Reduce `max_chunk_length` or use CPU-only mode

### Issue: Slow summarization
**Solution**: 
- Ensure CUDA is installed for GPU acceleration
- Reduce input text size
- Check available system memory

### Issue: Poor summary quality
**Solution**:
- Check input text is properly formatted
- Ensure text is at least 20 words
- Review extracted entities for accuracy

## API Documentation

### POST `/api/summarize/`

Quickly summarize text without creating a database record.

**Parameters**:
- `text` (required): Text to summarize (min 20 words)

**Success Response**:
```json
{
  "success": true,
  "summary": "...",
  "speakers": [...],
  "motions": [...],
  "outcomes": [...],
  "word_count_original": 1000,
  "word_count_summary": 200,
  "reduction_percentage": 80.0
}
```

**Error Response**:
```json
{
  "error": "Text must be at least 20 words"
}
```

## Support & Feedback

For issues, feature requests, or questions:
1. Check the troubleshooting section
2. Review logs in Django console
3. Contact the development team

## References

- [Hugging Face Transformers](https://huggingface.co/transformers/)
- [BART Model](https://huggingface.co/facebook/bart-large-cnn)
- [PyTorch Documentation](https://pytorch.org/)
- [Django Documentation](https://docs.djangoproject.com/)

---

**Feature Added**: December 2025
**Version**: 1.0
**Status**: Production Ready
