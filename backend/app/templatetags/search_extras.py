import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='highlight')
def highlight(text, search):
    if not search:
        return text
    
    # Case-insensitive replacement
    pattern = re.compile(re.escape(search), re.IGNORECASE)
    
    # Replace with <mark> tags
    highlighted = pattern.sub(lambda m: f'<mark>{m.group(0)}</mark>', text)
    
    return mark_safe(highlighted)

@register.filter(name='clean_text')
def clean_text(text):
    if not text:
        return text
    
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Replace double newlines (paragraphs) with a temporary placeholder
    text = text.replace('\n\n', '[[PARAGRAPH]]')
    
    # Replace remaining single newlines (hard breaks) with spaces
    text = text.replace('\n', ' ')
    
    # Restore paragraphs
    text = text.replace('[[PARAGRAPH]]', '\n\n')
    
    # Clean up multiple spaces
    text = re.sub(r' +', ' ', text)
    
    return text.strip()
