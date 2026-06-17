from django import forms
from .models import Summary

class PDFUploadForm(forms.Form):
    pdf_file = forms.FileField()


class TextSummaryForm(forms.Form):
    """Form for summarizing custom text"""
    text = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 10,
            'placeholder': 'Paste the debate text, transcript, or any content you want to summarize...',
            'class': 'form-control'
        }),
        label='Content to Summarize',
        help_text='Enter at least 100 characters'
    )
    
    title = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Optional title for this summary',
            'class': 'form-control'
        })
    )


class SegmentSummaryForm(forms.Form):
    """Form for summarizing a debate segment"""
    segment_id = forms.IntegerField(widget=forms.HiddenInput())
    include_speakers = forms.BooleanField(required=False, initial=True, label='Include speaker information')
    include_motions = forms.BooleanField(required=False, initial=True, label='Include motions')
    include_outcomes = forms.BooleanField(required=False, initial=True, label='Include outcomes')


class SessionSummaryForm(forms.Form):
    """Form for summarizing entire session"""
    session_id = forms.IntegerField(widget=forms.HiddenInput())
    include_all_topics = forms.BooleanField(required=False, initial=True, label='Summarize all topics')
    topic_id = forms.IntegerField(required=False, widget=forms.HiddenInput(), label='Specific topic (optional)')
