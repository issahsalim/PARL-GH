"""
AI-powered summarization utility using Hugging Face BART model
"""
import re
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

try:
    from transformers import pipeline
    SUMMARIZER_AVAILABLE = True
except ImportError:
    SUMMARIZER_AVAILABLE = False
    logger.warning("Transformers library not installed. Install with: pip install transformers torch")


class HansardSummarizer:
    """
    Summarizes parliamentary debate content using BART model.
    Provides structured output with speakers, motions, and outcomes.
    """
    
    def __init__(self):
        self.summarizer = None
        if SUMMARIZER_AVAILABLE:
            try:
                self.summarizer = pipeline(
                    "summarization", 
                    model="facebook/bart-large-cnn",
                    device=0 if self._has_gpu() else -1  # -1 for CPU, 0 for GPU
                )
                logger.info("BART summarizer initialized successfully")
            except Exception as e:
                logger.error(f"Error loading BART model: {e}")
                self.summarizer = None
    
    @staticmethod
    def _has_gpu():
        """Check if GPU is available"""
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False
    
    def summarize_text(self, text: str, max_length: int = 150, min_length: int = 50) -> str:
        """
        Generate a summary of the input text using BART model.
        
        Args:
            text: The text to summarize
            max_length: Maximum length of summary (in tokens)
            min_length: Minimum length of summary (in tokens)
        
        Returns:
            Summarized text
        """
        if not SUMMARIZER_AVAILABLE or not self.summarizer:
            return self._fallback_summary(text)
        
        if not text or len(text.strip()) < 50:
            return text
        
        try:
            # Split into chunks if text is too long (BART has token limits)
            chunks = self._chunk_text(text, max_chunk_length=1000)
            summaries = []
            
            for chunk in chunks:
                summary = self.summarizer(
                    chunk,
                    max_length=max_length,
                    min_length=min_length,
                    do_sample=False
                )   
                summaries.append(summary[0]['summary_text'])
            
            return " ".join(summaries)
        
        except Exception as e:
            logger.error(f"Error during summarization: {e}")
            return self._fallback_summary(text)
    
    def summarize_with_structure(self, text: str) -> Dict[str, Any]:
        """
        Generate a structured summary with extracted entities and analytics.
        """ 
        # Generate summary
        summary = self.summarize_text(text)
        
        # Extract structured information
        speakers = self._extract_speakers(text)
        motions = self._extract_motions(text)
        outcomes = self._extract_outcomes(text)
        
        # Advanced analytics
        sentiment = self._extract_sentiment(text)
        action_items = self._extract_action_items(text)
        speaker_stats = self._calculate_speaker_stats(text, speakers)
        timeline = self._generate_timeline(text, speakers, motions)
        
        return {
            'summary': summary,
            'speakers': list(set(speakers)),
            'motions': list(set(motions)),
            'outcomes': list(set(outcomes)),
            'sentiment': sentiment,
            'action_items': action_items,
            'speaker_stats': speaker_stats,
            'timeline': timeline,
            'word_count_original': len(text.split()),
            'word_count_summary': len(summary.split()),
            'reduction_percentage': round((1 - len(summary.split()) / len(text.split())) * 100, 2)
        }

    def _extract_sentiment(self, text: str) -> Dict[str, float]:
        """Simple heuristic for sentiment analysis"""
        pos_words = ['agree', 'support', 'favor', 'passed', 'excellent', 'progress', 'benefit', 'good', 'success', 'approved']
        neg_words = ['disagree', 'object', 'reject', 'oppose', 'failed', 'problem', 'concern', 'negative', 'poor', 'danger']
        
        text_lower = text.lower()
        pos_count = sum(text_lower.count(word) for word in pos_words)
        neg_count = sum(text_lower.count(word) for word in neg_words)
        total = pos_count + neg_count + 10 # Buffer to avoid empty bias
        
        return {
            'positive': round((pos_count / total) * 100, 1),
            'negative': round((neg_count / total) * 100, 1),
            'neutral': round(((total - pos_count - neg_count) / total) * 100, 1)
        }

    def _extract_action_items(self, text: str) -> List[str]:
        """Extract tasks and follow-ups"""
        actions = []
        patterns = [
            r'(?:will|must|should|agreed to)\s+(?:submit|meet|investigate|report|review|organize|create|form)\s+([^.!?\n]+[.!?])',
            r'(?:deadline|by the end of|no later than)\s+([^.!?\n]+[.!?])',
            r'(?:Committee|Task Force)\s+(?:to|will)\s+([^.!?\n]+[.!?])'
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                action = match.group(1).strip()
                if 10 < len(action) < 200:
                    actions.append(action)
        return list(set(actions))[:5]

    def _calculate_speaker_stats(self, text: str, speakers: List[str]) -> Dict[str, Any]:
        """Calculate word count distribution per speaker"""
        stats = {}
        total_words = len(text.split())
        
        # This is a simplification: split text by speaker names to estimate their portions
        for speaker in speakers:
            # Look for appearances of this speaker and count words until next speaker
            pattern = re.escape(speaker) + r'\s*:(.*?)(?=' + '|'.join([re.escape(s) for s in speakers if s != speaker]) + r'|$)'
            fragments = re.findall(pattern, text, re.DOTALL)
            words = sum(len(f.split()) for f in fragments)
            if words > 0:
                stats[speaker] = {
                    'word_count': words,
                    'percentage': round((words / total_words) * 100, 1)
                }
        return stats

    def _generate_timeline(self, text: str, speakers: List[str], motions: List[str]) -> List[Dict[str, Any]]:
        """Generate sequential events for the Gantt chart"""
        timeline = []
        # Find positions of speakers and motions to create a sequence
        events = []
        for speaker in set(speakers):
            for m in re.finditer(re.escape(speaker) + r'\s*:', text):
                events.append({'type': 'speaker', 'label': speaker, 'pos': m.start()})
        
        for motion in motions:
            # Just take a snippet of the motion for the label
            label = (motion[:30] + '...') if len(motion) > 30 else motion
            for m in re.finditer(re.escape(motion), text):
                events.append({'type': 'motion', 'label': label, 'pos': m.start()})
                
        # Sort by position
        events.sort(key=lambda x: x['pos'])
        
        # Convert to relative time/offset for the chart
        text_len = len(text)
        for i, event in enumerate(events):
            start_offset = round((event['pos'] / text_len) * 100)
            end_offset = round((events[i+1]['pos'] / text_len) * 100) if i+1 < len(events) else 100
            
            timeline.append({
                'type': event['type'],
                'label': event['label'],
                'start': start_offset,
                'end': end_offset if end_offset > start_offset else start_offset + 5
            })
            
        return timeline[:15] # Limit for display
    
    @staticmethod
    def _chunk_text(text: str, max_chunk_length: int = 1000) -> List[str]:
        """Split text into chunks based on sentence boundaries"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length > max_chunk_length and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    @staticmethod
    def _extract_speakers(text: str) -> List[str]:
        """
        Extract speaker names from debate text.
        Looks for patterns like "Mr. Speaker:", "Ms. Osei:", etc.
        """
        speakers = []
        
        # Pattern 1: "Mr./Ms./Hon. [Name]:" at start of line
        pattern1 = r'(?:^|\n)((?:Mr|Ms|Mrs|Hon|Dr|Prof|Sir|Madam)\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*):.*?(?=(?:(?:Mr|Ms|Mrs|Hon|Dr|Prof|Sir|Madam)\.|$))'
        
        for match in re.finditer(pattern1, text, re.MULTILINE):
            speaker = match.group(1).strip()
            if speaker and len(speaker) < 100:  # Reasonable length check
                speakers.append(speaker)
        
        # Pattern 2: All caps at start of line (common in hansards)
        pattern2 = r'(?:^|\n)([A-Z]{2,}(?:\s+[A-Z]{2,})*)\s*:'
        for match in re.finditer(pattern2, text, re.MULTILINE):
            name = match.group(1).strip()
            if len(name) > 3 and len(name) < 60:
                speakers.append(name)
        
        return speakers
    
    @staticmethod
    def _extract_motions(text: str) -> List[str]:
        """
        Extract motions from debate text.
        Looks for patterns like "Motion to...", "moved that...", etc.
        """
        motions = []
        
        patterns = [
            r'(?:Motion to|moved that|I move that)\s+([^.!?\n]+[.!?])',
            r'(?:BE IT ENACTED|BE IT RESOLVED)\s+([^.!?\n]+[.!?])',
            r'(?:The motion is|This motion)\s+([^.!?\n]+[.!?])',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                motion = match.group(1).strip()
                if motion and 20 < len(motion) < 500:
                    motions.append(motion)
        
        return motions
    
    @staticmethod
    def _extract_outcomes(text: str) -> List[str]:
        """
        Extract outcomes/decisions from debate text.
        Looks for patterns like "agreed to", "rejected", "passed", etc.
        """
        outcomes = []
        
        patterns = [
            r'(?:The motion is|Motion was)\s+(?:unanimously\s+)?(passed|rejected|withdrawn|modified|amended|agreed to|carried)',
            r'(?:approved|adopted|accepted|dismissed|defeated|lost)\s+by?\s+(?:the|a)?\s+(?:House|Parliament)',
            r'(?:Ayes|Noes)\s+\d+.*?(?:Ayes|Noes)\s+\d+',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                outcome = match.group(0).strip()
                if outcome and len(outcome) < 300:
                    outcomes.append(outcome)
        
        return outcomes
        
    @staticmethod
    def _fallback_summary(text: str, sentences_count: int = 5) -> str:
        """
        Fallback summarization when BART is not available.
        Uses extractive summarization (sentence ranking).
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        if len(sentences) <= sentences_count:
            return text
        
        # Simple scoring: prioritize sentences with more content words
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            words = sentence.split()
            score = len([w for w in words if len(w) > 3])  # Count substantial words
            scored_sentences.append((i, sentence, score))
        
        # Sort by score but maintain original order
        top_sentences = sorted(scored_sentences, key=lambda x: x[2], reverse=True)[:sentences_count]
        top_sentences = sorted(top_sentences, key=lambda x: x[0])  # Restore order
        
        return " ".join([sent for _, sent, _ in top_sentences])


# Global instance
_summarizer_instance = None

def get_summarizer() -> HansardSummarizer:
    """Get or create the global summarizer instance"""
    global _summarizer_instance
    if _summarizer_instance is None:
        _summarizer_instance = HansardSummarizer()
    return _summarizer_instance


