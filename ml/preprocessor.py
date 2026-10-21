import re
import string

# Standard English stop words
STOP_WORDS = set([
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he",
    "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's",
    "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll",
    "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs",
    "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll",
    "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while",
    "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
    "you're", "you've", "your", "yours", "yourself", "yourselves"
])

# Clickbait trigger indicators (for linguistic feature scoring)
SENSATIONAL_WORDS = set([
    "shocking", "unbelievable", "mind-blowing", "insane", "crazy", "speechless", "miracle", "secret",
    "secrets", "incredible", "impossible", "stunning", "furious", "obsessed", "dropout", "hiding"
])

HYPERBOLIC_PHRASES = [
    "you won't believe", "will change your life", "don't want you to know", "leave you in tears",
    "will blow your mind", "left everyone speechless", "restore your faith", "impossible trivia"
]

AI_WRITING_MARKERS = [
    "delve into", "testament to", "in the realm of", "game-changer", "brings to the table",
    "tapestry of", "beacon of", "multifaceted", "nestled in", "in conclusion", "furthermore",
    "it is worth noting", "serves as a reminder", "undeniable proof", "unraveling the", "evolving landscape"
]

WEBPAGE_UI_NOISE_PATTERNS = [
    r'\b\d+\s+(?:hours?|days?|mins?|minutes?|secs?|seconds?)\s+ago\b',
    r'\b(?:AFP|AP|Reuters|BBC|Dawn|CNN)?\s*Published\s+[A-Za-z]+\s+\d{1,2}(?:,\s*\d{4})?(?:\s*Updated[^\.\n]*)?\b',
    r'\bshare\s+on\s+(?:facebook|twitter|x|whatsapp|linkedin|reddit|social)\b',
    r'\badd as preferred on google\b',
    r'\b\d+:\d+\s+watch:?\b',
    r'\bwatch:?\b',
    r'\bsenior \w+ reporter\b',
    r'\b reporter\b',
    r'\bfollow us on\b',
    r'\bsubscribe to notifications?\b',
    r'\baccept cookies?\b'
]

def clean_webpage_text_artifacts(text):
    """
    Strips out webpage UI toolbar noise (e.g. '7 hours ago', 'Share', 'Save', 'Add as preferred on Google', 'Watch:')
    when copied directly from browser windows.
    """
    if not text or not isinstance(text, str):
        return ""
    cleaned = text
    for pattern in WEBPAGE_UI_NOISE_PATTERNS:
        cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def preprocess_text(text, keep_stop_words=False):
    """
    Cleans raw input text:
    1. Lowercase conversion
    2. Punctuation removal
    3. Tokenization & optional stop word removal
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Lowercase
    clean = text.lower()
    
    # Remove special punctuation but preserve word tokens
    clean = re.sub(r'[^\w\s]', '', clean)
    
    # Tokenize
    tokens = clean.split()
    
    if not keep_stop_words:
        tokens = [t for t in tokens if t not in STOP_WORDS]
        
    return " ".join(tokens)

def extract_linguistic_features(raw_text):
    """
    Extracts high-level linguistic signals matching SRS rules:
    - Sensational words count
    - Hyperbolic expressions check
    - Question marks / Exclamation count
    - AI-Generated writing markers check
    """
    raw_lower = raw_text.lower()
    
    sensational_found = [w for w in SENSATIONAL_WORDS if w in raw_lower]
    hyperbolic_found = [p for p in HYPERBOLIC_PHRASES if p in raw_lower]
    ai_markers_found = [m for m in AI_WRITING_MARKERS if m in raw_lower]
    
    has_exclamation = '!' in raw_text
    has_question = '?' in raw_text
    
    return {
        "sensational_words": sensational_found,
        "hyperbolic_expressions": hyperbolic_found,
        "ai_markers_found": ai_markers_found,
        "has_ai_signal": len(ai_markers_found) > 0,
        "has_exclamation": has_exclamation,
        "has_question": has_question
    }
