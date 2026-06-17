from django.db import models
import os 
# Create your models here.
class HansardFile(models.Model):
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.BigIntegerField(null=True, blank=True)
    date_downloaded = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.file_name
    
    def save(self, *args, **kwargs):
        # Try to infer file size if path is local and file exists
        try:
            if self.file_path and os.path.exists(self.file_path):
                self.file_size = os.path.getsize(self.file_path)
        except Exception:
            pass
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-date_downloaded']
    
class Session(models.Model):
    parliament_number = models.IntegerField(null=True, blank=True)
    meeting_number = models.IntegerField(null=True, blank=True)
    sitting_date = models.DateField()
    
    title = models.CharField(max_length=255)  # e.g. "21 November, 2025"
    pdf_file = models.ForeignKey(HansardFile, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.title} ({self.sitting_date})"

class Topic(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="topics")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.session.title}"


class Speaker(models.Model):
    name = models.CharField(max_length=500)
    role = models.CharField(max_length=500, blank=True)  # MP, Minister, Speaker
    party = models.CharField(max_length=100, blank=True, null=True)
    constituency = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.party or 'No Party'})"

    

class DebateSegment(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True)
    speaker = models.ForeignKey(Speaker, on_delete=models.SET_NULL, null=True)

    text = models.TextField()
    start_page = models.IntegerField(null=True, blank=True)
    end_page = models.IntegerField(null=True, blank=True)
    word_count = models.IntegerField(default=0, null=True, blank=True)    

    def __str__(self):
        return f"{self.speaker} - {self.session.title}"


class Summary(models.Model):
    """
    Stores AI-generated summaries of debate content.
    Can be associated with Session, Topic, DebateSegment, or custom text.
    """
    CONTENT_TYPE_CHOICES = [
        ('session', 'Full Session'),
        ('topic', 'Topic Discussion'),
        ('segment', 'Single Segment'),
        ('custom', 'Custom Text'),
    ]
    
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, default='custom')
    
    # Foreign keys (optional, depends on content_type)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True, blank=True, related_name='summaries')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True, blank=True, related_name='summaries')
    debate_segment = models.ForeignKey(DebateSegment, on_delete=models.CASCADE, null=True, blank=True, related_name='summaries')
    
    # Content
    original_text = models.TextField()
    summary_text = models.TextField()
    
    # Structured data
    speakers_mentioned = models.JSONField(default=list, blank=True, help_text="List of speakers mentioned")
    motions = models.JSONField(default=list, blank=True, help_text="List of motions discussed")
    outcomes = models.JSONField(default=list, blank=True, help_text="List of outcomes/decisions")
    
    # Advanced analytics data
    sentiment_data = models.JSONField(default=dict, blank=True, help_text="Sentiment analysis scores")
    action_items = models.JSONField(default=list, blank=True, help_text="List of identified action items")
    speaker_stats = models.JSONField(default=dict, blank=True, help_text="Word count and time distribution")
    debate_timeline = models.JSONField(default=list, blank=True, help_text="Sequence of events for visualization")
    
    # Metadata
    original_word_count = models.IntegerField()
    summary_word_count = models.IntegerField()
    reduction_percentage = models.FloatField(default=0)
    
    created_by = models.CharField(max_length=100, default='system', help_text="User who requested the summary")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Summary of {self.get_content_type_display()} ({self.created_at.strftime('%Y-%m-%d')})"
    
class ParliamentaryLeadership(models.Model):
    role = models.CharField(max_length=100, unique=True) # e.g. "president", "speaker"
    image = models.ImageField(upload_to='leadership/')

    class Meta:
        verbose_name_plural = "Parliamentary Leadership"

    def __str__(self):
        return self.role

    