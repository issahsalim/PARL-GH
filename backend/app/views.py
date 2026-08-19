from django.shortcuts import render, get_object_or_404, redirect
from .models import Session, DebateSegment, Speaker, Topic, Summary, ParliamentaryLeadership
from .utils.progress import PipelineProgress

# app/views.py (add these imports at top)
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render
from django.db.models import Q
import re
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from .forms import TextSummaryForm, SegmentSummaryForm, SessionSummaryForm
from .utils.summarizer import get_summarizer
import logging
import csv
from django.template.loader import render_to_string
from django.core import serializers
import json

logger = logging.getLogger(__name__)


def home(request):
    """Home page view with statistics"""
    total_segments = DebateSegment.objects.count()
    total_sessions = Session.objects.count()
    total_speakers = Speaker.objects.count()
    total_topics = Topic.objects.count()
    
    # Get leadership images as a dictionary: {role: image_url}
    leadership_qs = ParliamentaryLeadership.objects.all()
    leadership_map = {l.role: l.image.url for l in leadership_qs if l.image}
    
    context = {
        'total_segments': total_segments,
        'total_sessions': total_sessions,
        'total_speakers': total_speakers,
        'total_topics': total_topics,
        'leadership_map': leadership_map,
    }
    return render(request, 'index.html', context)


def session_list(request):
    sessions = Session.objects.all().order_by('-sitting_date')
    sessions_qs = Session.objects.all().order_by('-sitting_date')
    # pagination
    page = request.GET.get('page', 1)
    per_page = 12
    paginator = Paginator(sessions_qs, per_page)
    try:
        sessions = paginator.page(page)
    except PageNotAnInteger:
        sessions = paginator.page(1)
    except EmptyPage:
        sessions = paginator.page(paginator.num_pages)
    context = {
        'sessions': sessions,
        'paginator': paginator,
    }
    return render(request, 'session_list.html', context)

def session_detail(request, session_id):
    session = get_object_or_404(Session, pk=session_id)
    segments = DebateSegment.objects.filter(session=session).select_related('speaker')
    return render(request, 'session_detail.html', {'session': session, 'segments': segments})


def highlight(text, term):
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)


def search(request):
    query = request.GET.get("q", "").strip()
    speaker_id = request.GET.get("speaker")
    topic_id = request.GET.get("topic")
    session_id = request.GET.get("session")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    sort_order = request.GET.get("sort", "desc") # Default to newest first

    segments = DebateSegment.objects.all().select_related('speaker', 'session', 'topic')

    # ADVANCED FILTERS
    if speaker_id and speaker_id.isdigit():
        segments = segments.filter(speaker_id=speaker_id)

    if topic_id and topic_id.isdigit():
        segments = segments.filter(topic_id=topic_id)

    if session_id and session_id.isdigit():
        segments = segments.filter(session_id=session_id)

    if start_date:
        try:
            segments = segments.filter(session__sitting_date__gte=start_date)
        except (ValueError, TypeError):
            pass
    
    if end_date:
        try:
            segments = segments.filter(session__sitting_date__lte=end_date)
        except (ValueError, TypeError):
            pass

    # MULTI-FIELD KEYWORD SEARCH
    if query:
        # Search in segment text, speaker name, speaker party, speaker constituency, or topic name
        segments = segments.filter(
            Q(text__icontains=query) |
            Q(speaker__name__icontains=query) |
            Q(speaker__party__icontains=query) |
            Q(speaker__constituency__icontains=query) |
            Q(topic__name__icontains=query)
        )

    # SORTING
    if sort_order == "asc":
        segments = segments.order_by('session__sitting_date', 'id')
    else:
        segments = segments.order_by('-session__sitting_date', '-id')

    # SUMMARY RESULTS (for sidebars/extra info)
    session_results = Session.objects.filter(title__icontains=query) if query else []
    topic_results = Topic.objects.filter(name__icontains=query) if query else []
    speaker_results = Speaker.objects.filter(
        Q(name__icontains=query) | Q(party__icontains=query) | Q(constituency__icontains=query)
    ) if query else []

    context = {
        "query": query,
        "segments": segments[:100],  # Limit to 100 for performance
        "session_results": session_results,
        "topic_results": topic_results,
        "speaker_results": speaker_results,
        "start_date": start_date,
        "end_date": end_date,
        "selected_speaker": speaker_id,
        "selected_topic": topic_id,
        "selected_session": session_id,
        "sort_order": sort_order,

        # Filter dropdown values
        "speakers": Speaker.objects.all().order_by('name'),
        "topics": Topic.objects.all().order_by('name'),
        "sessions": Session.objects.all().order_by('-sitting_date'),
    }
    return render(request, "search.html", context)




def segment_detail(request, id):
    seg = DebateSegment.objects.get(pk=id)

    # Chart data: topics count
    # topic_stats = (
    #     DebateSegment.objects
    #     .filter(session=seg.session)
    #     .values('topic__name')
    #     .annotate(count=Count('id'))
    # )

    return render(request, "segment_detail.html", {
        "seg": seg,
    })

 

def analytics_dashboard(request):
    # Get Filter Parameters
    session_id = request.GET.get('session')
    mp_id = request.GET.get('mp')
    party = request.GET.get('party')
    date_filter = request.GET.get('date_range', 'all')

    # Base Querysets
    segments = DebateSegment.objects.all()
    topics = Topic.objects.all()
    sessions_qs = Session.objects.all()
    
    # Apply Filters
    if session_id:
        segments = segments.filter(session_id=session_id)
        topics = topics.filter(session_id=session_id)
        sessions_qs = sessions_qs.filter(id=session_id)
    
    if mp_id:
        segments = segments.filter(speaker_id=mp_id)
    
    if party:
        segments = segments.filter(speaker__party=party)
        
    if date_filter == 'last12':
        one_year_ago = timezone.now() - timedelta(days=365)
        segments = segments.filter(session__sitting_date__gte=one_year_ago)
        topics = topics.filter(session__sitting_date__gte=one_year_ago)
        sessions_qs = sessions_qs.filter(sitting_date__gte=one_year_ago)
    elif date_filter == 'ytd':
        start_of_year = timezone.now().replace(month=1, day=1)
        segments = segments.filter(session__sitting_date__gte=start_of_year)
        topics = topics.filter(session__sitting_date__gte=start_of_year)
        sessions_qs = sessions_qs.filter(sitting_date__gte=start_of_year)

    # ---- MP Participation ----
    mp_stats = (
        segments
        .values('speaker__name')
        .annotate(total_words=Sum('word_count'))
        .order_by('-total_words')[:10]
    )
    
    # ---- Topic Trends ----
    topic_trends = (
        topics
        .annotate(month=TruncMonth('session__sitting_date'))
        .values('month', 'name')
        .annotate(total_words=Sum('session__debatesegment__word_count'))
        .order_by('month')
    )
    
    # ---- Participation by Party ----
    party_participation = (
        Speaker.objects
        .exclude(party__isnull=True)
        .exclude(party='')
        .values('party')
        .annotate(count=Count('debatesegment'))
    )
    if party:
        party_participation = party_participation.filter(party=party)
    
    party_participation = party_participation.order_by('-count')
    
    # ---- Sentiment Analysis ----
    latest_summaries = Summary.objects.exclude(sentiment_data={}).order_by('-created_at')
    if session_id:
        latest_summaries = latest_summaries.filter(session_id=session_id)
    
    latest_summaries = latest_summaries[:20]
    
    sentiment_agg = {'positive': 0, 'neutral': 0, 'negative': 0}
    if latest_summaries.exists():
        count = latest_summaries.count()
        for s in latest_summaries:
            sentiment_agg['positive'] += s.sentiment_data.get('positive', 0)
            sentiment_agg['neutral'] += s.sentiment_data.get('neutral', 0)
            sentiment_agg['negative'] += s.sentiment_data.get('negative', 0)
        
        sentiment_agg = {k: v/count for k, v in sentiment_agg.items()}
    else:
        sentiment_agg = {'positive': 35, 'neutral': 45, 'negative': 20}

    # ---- Expected vs Actual ----
    total_sessions = Session.objects.count() or 1
    total_segments = DebateSegment.objects.count()
    overall_avg = total_segments / total_sessions
    
    expected_vs_actual = []
    recent_sessions = sessions_qs.order_by('-sitting_date')[:5]
    for s in recent_sessions:
        actual = segments.filter(session=s).count()
        expected_vs_actual.append({
            'label': s.title[:15],
            'actual': actual,
            'expected': int(overall_avg)
        })
    
    from django.core.serializers.json import DjangoJSONEncoder
    context = {
        "mp_stats": json.dumps(list(mp_stats), cls=DjangoJSONEncoder),
        "topic_trends": json.dumps(list(topic_trends), cls=DjangoJSONEncoder),
        "party_participation": json.dumps(list(party_participation), cls=DjangoJSONEncoder),
        "sentiment_overview": json.dumps(sentiment_agg),
        "expected_vs_actual": json.dumps(expected_vs_actual),
        "sessions": Session.objects.all().order_by('-sitting_date')[:50],
        "speakers": Speaker.objects.all().order_by('name'),
        "selected_filters": {
            "session": session_id,
            "mp": mp_id,
            "party": party,
            "date_range": date_filter
        }
    }
    return render(request, "analytic_dashboard.html", context)


def export_summary_json(request, summary_id):
    summary = get_object_or_404(Summary, id=summary_id)
    data = {
        "id": summary.id,
        "type": summary.get_content_type_display(),
        "date": summary.created_at.isoformat(),
        "original_words": summary.original_word_count,
        "summary_words": summary.summary_word_count,
        "reduction": f"{summary.reduction_percentage}%",
        "text": summary.summary_text,
        "speakers": summary.speakers_mentioned,
        "motions": summary.motions,
        "outcomes": summary.outcomes,
        "action_items": summary.action_items,
        "sentiment": summary.sentiment_data
    }
    response = HttpResponse(json.dumps(data, indent=4), content_type="application/json")
    response['Content-Disposition'] = f'attachment; filename="summary_{summary_id}.json"'
    return response


def export_summary_csv(request, summary_id):
    summary = get_object_or_404(Summary, id=summary_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="summary_{summary_id}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Field', 'Value'])
    writer.writerow(['ID', summary.id])
    writer.writerow(['Type', summary.get_content_type_display()])
    writer.writerow(['Date', summary.created_at])
    writer.writerow(['Original Words', summary.original_word_count])
    writer.writerow(['Summary Words', summary.summary_word_count])
    writer.writerow(['Summary Text', summary.summary_text])
    writer.writerow(['Speakers', ", ".join(summary.speakers_mentioned or [])])
    writer.writerow(['Action Items', ", ".join(summary.action_items or [])])
    
    return response


# ============ SUMMARIZATION VIEWS ============

def summarize_text(request):
    """
    View for summarizing custom text content.
    GET: Show form
    POST: Process summary and display results
    """
    if request.method == 'POST':
        form = TextSummaryForm(request.POST)
        if form.is_valid():
            text = form.cleaned_data['text']
            title = form.cleaned_data.get('title', 'Custom Text Summary')
            
            if len(text.split()) < 20:
                messages.error(request, 'Text must be at least 20 words long.')
                return render(request, 'summarize_text.html', {'form': form})
            
            try:
                # Get summarizer
                summarizer = get_summarizer()
                
                # Generate structured summary
                summary_data = summarizer.summarize_with_structure(text)
                
                # Save to database
                summary = Summary.objects.create(
                    content_type='custom',
                    original_text=text,
                    summary_text=summary_data['summary'],
                    speakers_mentioned=summary_data['speakers'],
                    motions=summary_data['motions'],
                    outcomes=summary_data['outcomes'],
                    sentiment_data=summary_data['sentiment'],
                    action_items=summary_data['action_items'],
                    speaker_stats=summary_data['speaker_stats'],
                    debate_timeline=summary_data['timeline'],
                    original_word_count=summary_data['word_count_original'],
                    summary_word_count=summary_data['word_count_summary'],
                    reduction_percentage=summary_data['reduction_percentage'],
                    created_by=request.user.username if request.user.is_authenticated else 'anonymous'
                )
                
                messages.success(request, 'Summary generated successfully!')
                return render(request, 'summary_result.html', {
                    'summary': summary,
                    'title': title
                })
            
            except Exception as e:
                logger.error(f"Summarization error: {e}")
                messages.error(request, f'Error generating summary: {str(e)}')
                return render(request, 'summarize_text.html', {'form': form})
    else:
        form = TextSummaryForm()
    
    return render(request, 'summarize_text.html', {'form': form})


def summarize_segment(request, segment_id):
    """
    View for summarizing a single debate segment.
    """
    segment = get_object_or_404(DebateSegment, pk=segment_id)
    
    try:
        # Get summarizer
        summarizer = get_summarizer()
        
        # Generate structured summary
        summary_data = summarizer.summarize_with_structure(segment.text)
        
        # --- ENRICHMENT WITH DB METADATA ---
        # Add the known speaker if not identified
        final_speakers = list(set(summary_data['speakers']))
        if segment.speaker and segment.speaker.name not in final_speakers:
            final_speakers.append(segment.speaker.name)
            
        # Add topics as fallback for motions
        final_motions = list(set(summary_data['motions']))
        if not final_motions:
            db_topics = Topic.objects.filter(session=segment.session).values_list('name', flat=True)
            final_motions = list(db_topics)[:3]
            
        # Refine speaker stats if empty
        final_stats = summary_data['speaker_stats']
        if not final_stats and segment.speaker:
            final_stats = {segment.speaker.name: {'word_count': len(segment.text.split()), 'percentage': 100.0}}
        
        # Save to database
        summary = Summary.objects.create(
            content_type='segment',
            debate_segment=segment,
            session=segment.session,
            original_text=segment.text,
            summary_text=summary_data['summary'],
            speakers_mentioned=final_speakers,
            motions=final_motions,
            outcomes=summary_data['outcomes'],
            sentiment_data=summary_data['sentiment'],
            action_items=summary_data['action_items'],
            speaker_stats=final_stats,
            debate_timeline=summary_data['timeline'],
            original_word_count=summary_data['word_count_original'],
            summary_word_count=summary_data['word_count_summary'],
            reduction_percentage=summary_data['reduction_percentage'],
            created_by=request.user.username if request.user.is_authenticated else 'anonymous'
        )
        
        # If request is AJAX, return JSON with rendered modal HTML
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            html = render_to_string('partials/summary_modal.html', {'summary': summary, 'segment': segment}, request=request)
            return JsonResponse({'success': True, 'html': html})

        messages.success(request, 'Segment summary generated successfully!')
        return render(request, 'summary_result.html', {
            'summary': summary,
            'segment': segment,
        })
    
    except Exception as e:
        logger.error(f"Segment summarization error: {e}")
        messages.error(request, f'Error generating summary: {str(e)}')
        return redirect('segment_detail', id=segment_id)


def summarize_session(request, session_id):
    """
    View for summarizing an entire parliamentary session.
    """
    session = get_object_or_404(Session, pk=session_id)
    
    try:
        # Collect all debate text from the session
        segments = DebateSegment.objects.filter(session=session)
        
        if not segments.exists():
            messages.error(request, 'No debate segments found for this session.')
            return redirect('session_detail', session_id=session_id)
        
        # Combine all segment texts
        combined_text = "\n\n".join([seg.text for seg in segments])
        
        # Get summarizer
        summarizer = get_summarizer()
        
        # Generate structured summary
        summary_data = summarizer.summarize_with_structure(combined_text)
        
        # --- ENRICHMENT WITH DB METADATA ---
        # Get all known speakers for this session
        db_speakers = list(segments.values_list('speaker__name', flat=True).distinct())
        final_speakers = list(set(summary_data['speakers'] + db_speakers))
        
        # Use DB Topics as fallback for motions
        final_motions = list(set(summary_data['motions']))
        if not final_motions:
            db_topics = list(Topic.objects.filter(session=session).values_list('name', flat=True))
            final_motions = db_topics[:5]
            
        # Recalculate stats using DB speakers if AI stats are weak
        final_stats = summary_data['speaker_stats']
        if len(final_stats) < 2 and len(final_speakers) > 1:
            # Re-run stats calculation with full speaker list
            final_stats = summarizer._calculate_speaker_stats(combined_text, final_speakers)
        
        # Save to database
        summary = Summary.objects.create(
            content_type='session',
            session=session,
            original_text=combined_text,
            summary_text=summary_data['summary'],
            speakers_mentioned=final_speakers,
            motions=final_motions,
            outcomes=summary_data['outcomes'],
            sentiment_data=summary_data['sentiment'],
            action_items=summary_data['action_items'],
            speaker_stats=final_stats,
            debate_timeline=summary_data['timeline'],
            original_word_count=summary_data['word_count_original'],
            summary_word_count=summary_data['word_count_summary'],
            reduction_percentage=summary_data['reduction_percentage'],
            created_by=request.user.username if request.user.is_authenticated else 'anonymous'
        )
        
        # If AJAX request, return partial HTML for modal injection
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            html = render_to_string('partials/summary_modal.html', {'summary': summary, 'session': session}, request=request)
            return JsonResponse({'success': True, 'html': html})

        messages.success(request, f'Session summary generated! Reduced by {summary_data["reduction_percentage"]}%')
        return render(request, 'summary_result.html', {
            'summary': summary,
            'session': session,
        })
    
    except Exception as e:
        logger.error(f"Session summarization error: {e}")
        messages.error(request, f'Error generating session summary: {str(e)}')
        return redirect('session_detail', session_id=session_id)


def view_summary(request, summary_id):
    """
    View a previously generated summary with all details.
    """
    summary = get_object_or_404(Summary, pk=summary_id)
    return render(request, 'summary_detail.html', {'summary': summary})


def summaries_list(request):
    """
    List all generated summaries with filtering options.
    """
    summaries = Summary.objects.all().order_by('-created_at')
    
    # Filter by content type
    content_type = request.GET.get('type')
    if content_type in [choice[0] for choice in Summary.CONTENT_TYPE_CHOICES]:
        summaries = summaries.filter(content_type=content_type)
    
    # Filter by session
    session_id = request.GET.get('session')
    if session_id:
        summaries = summaries.filter(session_id=session_id)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(summaries, 10)
    try:
        summaries = paginator.page(page)
    except PageNotAnInteger:
        summaries = paginator.page(1)
    except EmptyPage:
        summaries = paginator.page(paginator.num_pages)
    
    context = {
        'summaries': summaries,
        'paginator': paginator,
        'content_types': Summary.CONTENT_TYPE_CHOICES,
        'sessions': Session.objects.all().order_by('-sitting_date'),
    }
    return render(request, 'summaries_list.html', context)


def api_quick_summary(request):
    """
    API endpoint for quick summarization without storing in DB.
    POST with 'text' parameter returns JSON summary.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    text = request.POST.get('text') or request.GET.get('text', '').strip()
    
    if not text:
        return JsonResponse({'error': 'No text provided'}, status=400)
    
    if len(text.split()) < 20:
        return JsonResponse({'error': 'Text must be at least 20 words'}, status=400)
    
    try:
        summarizer = get_summarizer()
        summary_data = summarizer.summarize_with_structure(text)
        
        return JsonResponse({
            'success': True,
            'summary': summary_data['summary'],
            'speakers': summary_data['speakers'],
            'motions': summary_data['motions'],
            'outcomes': summary_data['outcomes'],
            'word_count_original': summary_data['word_count_original'],
            'word_count_summary': summary_data['word_count_summary'],
            'reduction_percentage': summary_data['reduction_percentage'],
        })
    
    except Exception as e:
        logger.error(f"API summarization error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def api_pipeline_status(request):
    """
    Returns the current status of the pipeline stored in cache.
    """
    progress = PipelineProgress.get()
    if progress:
        return JsonResponse(progress)
    return JsonResponse({'message': 'Idle'})




