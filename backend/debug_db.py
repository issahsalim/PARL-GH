import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from app.models import DebateSegment, Session, Speaker

print(f"Total Sessions: {Session.objects.count()}")
print(f"Total Speakers: {Speaker.objects.count()}")
print(f"Total Segments: {DebateSegment.objects.count()}")

if DebateSegment.objects.exists():
    print("\nSample Segment Data:")
    seg = DebateSegment.objects.first()
    print(f"Speaker: {seg.speaker.name}")
    print(f"Text length: {len(seg.text)}")
    print(f"Word count: {seg.word_count}")
    print(f"Session date: {seg.session.sitting_date}")
else:
    print("\nNo segments found in database.")
