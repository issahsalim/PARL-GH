# AI Summarization Feature - Quick Setup Guide

## Installation Steps

### Step 1: Install Required Packages

```bash
cd backend
pip install transformers torch
```

Or if using pip with constraints:
```bash
pip install -r requirements.txt
pip install transformers torch --no-cache-dir
```

### Step 2: Update Database

Create and run migrations for the new Summary model:

```bash
python manage.py makemigrations app
python manage.py migrate
```

### Step 3: Verify Installation

Test that the summarizer works:

```bash
python manage.py shell
>>> from app.utils.summarizer import get_summarizer
>>> summarizer = get_summarizer()
>>> result = summarizer.summarize_text("This is a test sentence. Another sentence here.")
>>> print(result)
```

### Step 4: Start the Server

```bash
python manage.py runserver
```

## Accessing the Feature

### Web Interface
- **Main summarization page**: `http://localhost:8000/summarize/`
- **Summary history**: `http://localhost:8000/summaries/`
- **View a summary**: `http://localhost:8000/summary/<id>/`

### Navigation
- Look for "Summarize" button in the top navigation bar
- Click any "Summarize" button on session or segment pages

### Admin Panel
- View all summaries: `http://localhost:8000/admin/app/summary/`
- Filter by type, date, or session
- Search by content

## First Run

**Note**: The first time you run the summarizer, it will download the BART model (~1.6GB). This may take a few minutes depending on your internet speed.

```
Downloading model... (this happens only once)
Model loaded successfully
Summary generated!
```

## Features at a Glance

| Feature | Access Point | Use Case |
|---------|-------------|----------|
| **Summarize Custom Text** | `/summarize/` | Summarize any parliamentary text |
| **Summarize Segment** | Segment detail page | Quick summary of one speaker's contribution |
| **Summarize Session** | Session detail page | Overview of entire parliamentary sitting |
| **View History** | `/summaries/` | Browse all generated summaries |
| **API Access** | `POST /api/summarize/` | Programmatic access |

## Configuration

### Adjust Summarization Parameters

Edit `app/utils/summarizer.py`:

```python
# Shorter summaries
max_length = 75
min_length = 25

# Longer summaries
max_length = 250
min_length = 100
```

### Use CPU if GPU Not Available

The system auto-detects GPU. To force CPU:

Edit `app/utils/summarizer.py` in the `__init__` method:
```python
# Replace: device=0 if self._has_gpu() else -1
# With:
device = -1  # Force CPU
```

## Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'transformers'"

**Solution**:
```bash
pip install transformers torch
```

### Problem: "CUDA out of memory"

**Solution**: Reduce text chunk size in `summarizer.py`:
```python
max_chunk_length = 500  # Instead of 1000
```

### Problem: Slow summarization (takes minutes)

**Solution**: Install GPU support for faster processing
```bash
# For NVIDIA GPUs
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Problem: Model download fails

**Solution**: Pre-download the model:
```bash
python manage.py shell
>>> from transformers import pipeline
>>> pipeline("summarization", model="facebook/bart-large-cnn")
```

## Testing the API

```bash
# Test with curl
curl -X POST http://localhost:8000/api/summarize/ \
  -d "text=Mr. Speaker said the motion to adjourn is carried. Ms. Osei moved that the House reconvenes tomorrow. The motion was unanimously approved."

# Response:
# {
#   "success": true,
#   "summary": "...",
#   "speakers": ["Mr. Speaker", "Ms. Osei"],
#   "motions": ["motion to adjourn", "motion to reconvene"],
#   "outcomes": ["motion was unanimously approved"],
#   ...
# }
```

## Database Schema

### Summary Table Fields

```
- id: Primary key
- content_type: 'session', 'topic', 'segment', or 'custom'
- session_id: Foreign key to Session (nullable)
- topic_id: Foreign key to Topic (nullable)
- debate_segment_id: Foreign key to DebateSegment (nullable)
- original_text: Full original text
- summary_text: Generated summary
- speakers_mentioned: JSON array of speakers
- motions: JSON array of motions
- outcomes: JSON array of outcomes
- original_word_count: Integer
- summary_word_count: Integer
- reduction_percentage: Float
- created_by: Username or 'anonymous'
- created_at: Timestamp
- updated_at: Timestamp
```

## File Structure

```
backend/
├── app/
│   ├── utils/
│   │   ├── summarizer.py          ← Main summarization logic
│   │   ├── pipeline.py
│   │   └── ...
│   ├── models.py                  ← Summary model
│   ├── views.py                   ← Summarization views
│   ├── forms.py                   ← Summarization forms
│   ├── urls.py                    ← Routes (updated)
│   ├── admin.py                   ← Admin configuration
│   └── templates/
│       ├── summarize_text.html    ← Main interface
│       ├── summary_result.html    ← Results page
│       ├── summary_detail.html    ← Detailed view
│       └── summaries_list.html    ← History/browse
└── SUMMARIZATION_FEATURE.md       ← Full documentation
```

## Performance Tips

1. **First Run**: Allow extra time for model download
2. **GPU Usage**: Enables 3-5x faster summarization
3. **Batch Processing**: Can process multiple texts via API
4. **Caching**: Previous summaries load instantly
5. **Optimize**: Reduce `max_chunk_length` for memory constraints

## Next Steps

After setup:

1. ✅ **Test the feature**: Create your first summary
2. 📖 **Read full docs**: See `SUMMARIZATION_FEATURE.md`
3. 🔧 **Customize**: Adjust parameters for your needs
4. 🔗 **Integrate**: Use API for your applications
5. 📊 **Monitor**: Check admin panel for usage stats

## Support

For detailed information:
- See `SUMMARIZATION_FEATURE.md` for comprehensive documentation
- Check Django logs for error messages
- Review `app/utils/summarizer.py` for implementation details
- Test with sample parliament data first

## Quick Commands Reference

```bash
# Run migrations
python manage.py migrate

# Start server
python manage.py runserver

# Access shell
python manage.py shell

# Test summarizer
python manage.py shell
>>> from app.utils.summarizer import get_summarizer
>>> summarizer = get_summarizer()
>>> summarizer.summarize_text("Your text here")

# Create superuser (if needed)
python manage.py createsuperuser

# View logs
tail -f logs/django.log
```

## Enjoy! 🎉

Your AI summarization system is now ready. Start summarizing parliamentary content!
