from django.shortcuts import render, get_object_or_404, redirect
from .models import Session, DebateSegment, Speaker, Topic, Summary, ParliamentaryLeadership
from .utils.progress import PipelineProgress

# app/views.py (add these imports at top)
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone
from django.shortcuts import render
from django.db.models import Q
import re
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.http import JsonResponse
from .forms import TextSummaryForm, SegmentSummaryForm, SessionSummaryForm
from .utils.summarizer import get_summarizer
import logging
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
    # ---- MP of the Month ----
    monthly_stats = (
        DebateSegment.objects
        .annotate(month=TruncMonth('session__sitting_date'))
        .values('month', 'speaker__id', 'speaker__name')
        .annotate(total_words=Sum('word_count'))
        .order_by('-month', '-total_words')
    )
    # Convert QuerySet to list for JSON serialization
    monthly_stats = list(monthly_stats)

    # ---- Total Debates per Session ----
    session_counts = (
        Session.objects
        .annotate(segment_count=Sum('debatesegment__word_count'))
        .order_by('-sitting_date')
        .values('id', 'title', 'sitting_date', 'segment_count')
    )
    
    session_counts = list(session_counts)

    # ---- Topic popularity ----
    topic_counts = (
        Topic.objects
        .annotate(total_words=Sum('session__debatesegment__word_count'))
        .order_by('-total_words')
        .values('id', 'name', 'total_words')
    )
    topic_counts = list(topic_counts)

    # Serialize dates to strings for JSON
    for stat in monthly_stats:
        if stat['month']:
            stat['month'] = stat['month'].isoformat()
    
    for session in session_counts:
        if session['sitting_date']:
            session['sitting_date'] = session['sitting_date'].isoformat()

    context = {
        "monthly_stats": json.dumps(monthly_stats, default=str),
        "session_counts": json.dumps(session_counts, default=str),
        "topic_counts": json.dumps(topic_counts, default=str),
    }

    return render(request, "analytic_dashboard.html", context)


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
        
        # Save to database
        summary = Summary.objects.create(
            content_type='segment',
            debate_segment=segment,
            session=segment.session,
            original_text=segment.text,
            summary_text=summary_data['summary'],
            speakers_mentioned=summary_data['speakers'],
            motions=summary_data['motions'],
            outcomes=summary_data['outcomes'],
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
        
        # Save to database
        summary = Summary.objects.create(
            content_type='session',
            session=session,
            original_text=combined_text,
            summary_text=summary_data['summary'],
            speakers_mentioned=summary_data['speakers'],
            motions=summary_data['motions'],
            outcomes=summary_data['outcomes'],
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




