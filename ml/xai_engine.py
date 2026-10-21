import numpy as np

STOP_WORDS = set([
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren\'t', 'as', 'at', 
    'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can\'t', 'cannot', 'could', 
    'couldn\'t', 'did', 'didn\'t', 'do', 'does', 'doesn\'t', 'doing', 'don\'t', 'down', 'during', 'each', 'few', 'for', 
    'from', 'further', 'had', 'hadn\'t', 'has', 'hasn\'t', 'have', 'haven\'t', 'having', 'he', 'he\'d', 'he\'ll', 'he\'s', 
    'her', 'here', 'here\'s', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'how\'s', 'i', 'i\'d', 'i\'ll', 'i\'m', 
    'i\'ve', 'if', 'in', 'into', 'is', 'isn\'t', 'it', 'it\'s', 'its', 'itself', 'let\'s', 'me', 'more', 'most', 'mustn\'t', 
    'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours', 'ourselves', 
    'out', 'over', 'own', 'same', 'shan\'t', 'she', 'she\'d', 'she\'ll', 'she\'s', 'should', 'shouldn\'t', 'so', 'some', 'such', 
    'than', 'that', 'that\'s', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'there\'s', 'these', 'they', 
    'they\'d', 'they\'ll', 'they\'re', 'they\'ve', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 
    'was', 'wasn\'t', 'we', 'we\'d', 'we\'ll', 'we\'re', 'we\'ve', 'were', 'weren\'t', 'what', 'what\'s', 'when', 'when\'s', 
    'where', 'where\'s', 'which', 'while', 'who', 'who\'s', 'whom', 'why', 'why\'s', 'with', 'won\'t', 'would', 'wouldn\'t', 
    'you', 'you\'d', 'you\'ll', 'you\'re', 'you\'ve', 'your', 'yours', 'yourself', 'yourselves'
])

def explain_prediction(headline, vectorizer, model, top_n=50, filter_stop_words=True):
    """
    Calculates feature importance weights for words in the input headline
    to explain WHY the model classified it as Clickbait vs Non-Clickbait.
    
    Returns a list of dicts: [{'word': str, 'weight': float, 'impact': 'Clickbait'|'Non-Clickbait'}]
    """
    if not headline or not vectorizer or not model:
        return []

    # Transform headline using vectorizer
    X_sample = vectorizer.transform([headline])
    feature_names = np.array(vectorizer.get_feature_names_out())
    
    # Non-zero feature indices in this sample
    sample_indices = X_sample.nonzero()[1]
    
    if len(sample_indices) == 0:
        # Fallback to simple token split if vocabulary match is sparse
        tokens = [t for t in headline.lower().split() if not filter_stop_words or t not in STOP_WORDS]
        return [{"word": t, "weight": 0.5, "impact": "Neutral"} for t in tokens[:top_n]]

    # Get model weights (coefficients for Logistic Regression or log prob diff for Naive Bayes)
    if hasattr(model, 'coef_'):
        coefficients = model.coef_[0]
    elif hasattr(model, 'feature_log_prob_'):
        # For Naive Bayes, take difference between log-probabilities
        coefficients = model.feature_log_prob_[1] - model.feature_log_prob_[0]
    else:
        return []

    results = []
    for idx in sample_indices:
        word = feature_names[idx].lower()

        # Filter out common stop words if requested
        if filter_stop_words and word in STOP_WORDS:
            continue

        tfidf_val = X_sample[0, idx]
        weight = coefficients[idx] * tfidf_val
        
        impact = "Clickbait" if weight > 0 else "Non-Clickbait"
        results.append({
            "word": word,
            "weight": round(float(abs(weight)), 4),
            "raw_score": round(float(weight), 4),
            "impact": impact
        })

    # Sort by absolute weight magnitude
    results.sort(key=lambda x: x["weight"], reverse=True)
    return results[:top_n]
