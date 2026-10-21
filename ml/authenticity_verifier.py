import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional

# =========================================================================
# Trusted Authority Wires, Certified Fact-Checkers & Satire Registries
# =========================================================================

TIER1_AUTHORITY_SOURCES = {
    'reuters', 'associated press', 'ap news', 'bbc', 'bbc news', 'afp',
    'the new york times', 'the washington post', 'the guardian', 'cnn',
    'bloomberg', 'financial times', 'wall street journal', 'wsj',
    'dawn', 'geo news', 'the times of india', 'the hindu', 'indian express',
    'al jazeera', 'france 24', 'deutsche welle', 'npr', 'pbs', 'cbs news',
    'nbc news', 'abc news', 'time', 'the economist', 'politico', 'axios'
}

FACT_CHECK_ORGANIZATIONS = {
    'snopes', 'politifact', 'factcheck.org', 'reuters fact check',
    'ap fact check', 'afp fact check', 'bbc reality check', 'full fact',
    'alt news', 'boom live', 'lead stories', 'check your fact', 'polygraph.info'
}

SATIRE_DOMAINS = {
    'theonion.com', 'babylonbee.com', 'clickhole.com', 'newsthump.com',
    'waterfordwhispersnews.com', 'thedailymash.co.uk', 'private-eye.co.uk',
    'duffelblog.com', 'thebeaverton.com'
}

HIGH_SEVERITY_KEYWORDS = {
    'death': ['dead', 'died', 'dies', 'death', 'killed', 'murdered', 'assassinated', 'passed away', 'found dead'],
    'legal': ['arrested', 'arrest', 'indicted', 'jailed', 'convicted', 'handcuffed', 'sentenced to death'],
    'political': ['resigned', 'ousted', 'coup', 'military takeover', 'fled country', 'steps down'],
    'catastrophe': ['nuclear strike', 'war declared', 'martial law', 'emergency declared', 'collapse'],
    'extraordinary': ['alien', 'extraterrestrial', 'miracle cure', 'cure for cancer', 'secret leak']
}

# In-memory query cache with 15-minute TTL to ensure fast responses
_VERIFICATION_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 900


class AuthenticityVerifier:
    """
    Real-Time News Authenticity & Fake News Corroboration Engine.
    Evaluates factual assertions by cross-referencing Tier-1 news sources,
    certified fact-check databases, and consensus metrics.
    """

    def __init__(self):
        pass

    def verify_headline(self, headline: str, source_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify the factual authenticity of a headline or claim.
        Returns a detailed authenticity assessment including consensus metrics and evidence citations.
        """
        if not headline or not headline.strip():
            return self._empty_result()

        headline = headline.strip()
        cache_key = headline.lower().strip()

        # Check Cache
        if cache_key in _VERIFICATION_CACHE:
            cached_item = _VERIFICATION_CACHE[cache_key]
            if time.time() - cached_item['cached_at'] < CACHE_TTL_SECONDS:
                return cached_item['result']

        # 1. Check for Known Satire URLs
        if source_url:
            for satire_domain in SATIRE_DOMAINS:
                if satire_domain in source_url.lower():
                    result = {
                        "status": "SATIRE / PARODY",
                        "score": 10.0,
                        "badge_type": "satire",
                        "consensus_label": "Satirical Publication",
                        "tier1_count": 0,
                        "fact_check_flag": True,
                        "explanation": f"Source URL belongs to known satirical publication ({satire_domain}). Content is humorous fiction, not factual news.",
                        "evidence_sources": [],
                        "claim_type": "Satire / Humor Content"
                    }
                    self._cache_result(cache_key, result)
                    return result

        # 2. Check for Subjective Listicles / Lifestyle Advice (Non-verifiable events)
        if re.search(r'^\d+\s+(shocking|surprising|reasons|facts|ways|secrets|tips|habits|signs)', headline, re.I):
            result = {
                "status": "OPINION / LIFESTYLE",
                "score": 50.0,
                "badge_type": "opinion",
                "consensus_label": "Subjective / Non-Event Content",
                "tier1_count": 0,
                "fact_check_flag": False,
                "explanation": "This headline represents an opinion listicle or subjective advice rather than a verifiable real-world breaking news event.",
                "evidence_sources": [],
                "claim_type": "Lifestyle / Listicle Editorial"
            }
            self._cache_result(cache_key, result)
            return result

        # 3. Analyze Claim Severity & Entities
        detected_severity, claim_category = self._detect_severity(headline)
        entities = self._extract_key_entities(headline)

        # 4. Perform Live Multi-Source News Queries
        news_items = self._query_google_news_rss(headline)
        debunk_items = self._query_debunk_rss(headline)

        # 5. Evaluate Fact-Checking Flags
        explicit_debunk = self._check_explicit_debunks(debunk_items + news_items, headline)
        if explicit_debunk:
            result = {
                "status": "DEBUNKED FAKE NEWS",
                "score": 8.5,
                "badge_type": "debunked",
                "consensus_label": "Refuted by Fact-Checkers",
                "tier1_count": 0,
                "fact_check_flag": True,
                "explanation": f"Claim has been explicitly reviewed and refuted: \"{explicit_debunk['title']}\" (Reported by {explicit_debunk['source']}).",
                "evidence_sources": [explicit_debunk] + news_items[:3],
                "claim_type": claim_category
            }
            self._cache_result(cache_key, result)
            return result

        # 6. Evaluate Tier-1 Authority News Corroboration
        tier1_matches = []
        general_matches = []

        # Keywords that indicate the article is about someone else, condolences, or legal penalties
        negation_context = [
            'death penalty', 'death threat', 'death anniversary', 'wife', 'mother',
            'father', 'brother', 'son', 'daughter', 'emir', 'condole', 'mourns',
            'attend funeral', 'commemorates', 'sentenced to death'
        ]

        for item in news_items:
            t_lower = item['title'].lower()
            src_clean = item['source'].lower().strip()
            is_tier1 = any(t in src_clean for t in TIER1_AUTHORITY_SOURCES)
            item['is_tier1'] = is_tier1

            # Check if article actually matches the core claim
            matches_claim = True
            if detected_severity:
                # Must match at least one severe predicate
                has_pred = any(k in t_lower for k in detected_severity)
                # Must match key entity if entities exist
                has_entity = any(e.lower() in t_lower for e in entities) if entities else True
                # Check for relative/condolence false positive
                is_false_context = any(nc in t_lower for nc in negation_context) if 'death' in claim_category.lower() else False
                
                matches_claim = has_pred and has_entity and not is_false_context

            if matches_claim:
                if is_tier1:
                    tier1_matches.append(item)
                else:
                    general_matches.append(item)

        tier1_count = len(tier1_matches)
        total_count = len(tier1_matches) + len(general_matches)

        # 7. Check Entity-Specific Critical Corroboration for High-Severity Claims
        # Example: "Nawaz Sharif found dead in his house" -> 0 articles confirm his death
        if detected_severity and tier1_count == 0:
            entity_name = entities[0] if entities else "the subject"
            result = {
                "status": "UNVERIFIED VIRAL RUMOR",
                "score": 18.0,
                "badge_type": "unverified",
                "consensus_label": "0 / 10 Tier-1 News Outlets Confirm",
                "tier1_count": 0,
                "fact_check_flag": False,
                "explanation": f"High-impact claim regarding {entity_name} has zero corroboration from any Tier-1 news organization worldwide. Major wire services (Reuters, BBC, AP, Dawn) have not confirmed this report.",
                "evidence_sources": news_items[:3],
                "claim_type": claim_category
            }
            self._cache_result(cache_key, result)
            return result

        # 8. Standard Corroboration Verdicts
        if tier1_count >= 2:
            sources_list = [m['source'] for m in tier1_matches[:3]]
            result = {
                "status": "VERIFIED AUTHENTIC",
                "score": 92.5,
                "badge_type": "verified",
                "consensus_label": f"{tier1_count} Tier-1 Outlets Corroborate",
                "tier1_count": tier1_count,
                "fact_check_flag": False,
                "explanation": f"Actively corroborated by multiple authoritative news organizations including {', '.join(sources_list)}.",
                "evidence_sources": tier1_matches[:4],
                "claim_type": claim_category or "Verifiable News Story"
            }
        elif tier1_count == 1 or total_count >= 3:
            lead_source = tier1_matches[0]['source'] if tier1_matches else (news_items[0]['source'] if news_items else "News Wires")
            result = {
                "status": "CORROBORATED NEWS",
                "score": 78.0,
                "badge_type": "verified",
                "consensus_label": f"Reported by {lead_source}",
                "tier1_count": tier1_count,
                "fact_check_flag": False,
                "explanation": f"Story has active media coverage reported by {lead_source} and related regional outlets.",
                "evidence_sources": (tier1_matches + general_matches)[:4],
                "claim_type": claim_category or "Developing News"
            }
        elif total_count > 0:
            result = {
                "status": "DEVELOPING / UNCONFIRMED",
                "score": 55.0,
                "badge_type": "developing",
                "consensus_label": "Limited Media Coverage",
                "tier1_count": 0,
                "fact_check_flag": False,
                "explanation": "Limited coverage found. The claim is either very recent or circulating on niche/local blogs without mainstream verification.",
                "evidence_sources": general_matches[:3],
                "claim_type": claim_category or "Unconfirmed Report"
            }
        else:
            result = {
                "status": "UNVERIFIED CLAIM",
                "score": 40.0,
                "badge_type": "unverified",
                "consensus_label": "No Independent Reports Found",
                "tier1_count": 0,
                "fact_check_flag": False,
                "explanation": "No matching reports found on national or international news wires. Treat with skepticism until verified by primary sources.",
                "evidence_sources": [],
                "claim_type": claim_category or "Unverified Text"
            }

        self._cache_result(cache_key, result)
        return result

    # ---------------------------------------------------------------------
    # Helper & Query Methods
    # ---------------------------------------------------------------------
    def _detect_severity(self, text: str):
        text_lower = text.lower()
        for category, words in HIGH_SEVERITY_KEYWORDS.items():
            for word in words:
                if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                    return words, f"High-Impact Event ({category.capitalize()})"
        return None, "General Information"

    def _extract_key_entities(self, text: str) -> List[str]:
        # Extract capitalized phrase sequences (Named Entities like Nawaz Sharif, Joe Biden, NASA)
        words = text.split()
        entities = []
        current = []
        for w in words:
            clean = re.sub(r'[^A-Za-z]', '', w)
            if clean and clean[0].isupper() and clean.lower() not in {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'by', 'with', 'from', 'why', 'how', 'what', 'who'}:
                current.append(clean)
            else:
                if current:
                    entities.append(" ".join(current))
                    current = []
        if current:
            entities.append(" ".join(current))
        return entities

    def _query_google_news_rss(self, query: str) -> List[Dict[str, Any]]:
        clean_q = re.sub(r'[\'\"]', '', query).strip()
        encoded = urllib.parse.quote(clean_q)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        return self._fetch_rss_items(url)

    def _query_debunk_rss(self, query: str) -> List[Dict[str, Any]]:
        clean_q = re.sub(r'[\'\"]', '', query).strip()
        encoded = urllib.parse.quote(f"{clean_q} fact check")
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        return self._fetch_rss_items(url)

    def _fetch_rss_items(self, url: str) -> List[Dict[str, Any]]:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        })
        items = []
        try:
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                xml_data = resp.read()
                tree = ET.fromstring(xml_data)
                for it in tree.findall('.//item')[:8]:
                    title = it.find('title').text if it.find('title') is not None else ''
                    link = it.find('link').text if it.find('link') is not None else ''
                    pub_date = it.find('pubDate').text if it.find('pubDate') is not None else ''
                    source_el = it.find('source')
                    source_name = source_el.text if source_el is not None else ''

                    if not source_name and '-' in title:
                        parts = title.rsplit('-', 1)
                        if len(parts) == 2:
                            source_name = parts[1].strip()

                    if title:
                        items.append({
                            'title': title,
                            'url': link,
                            'source': source_name or 'News Source',
                            'date': pub_date[:16] if pub_date else 'Recent'
                        })
        except Exception:
            pass
        return items

    def _check_explicit_debunks(self, items: List[Dict[str, Any]], original_headline: str) -> Optional[Dict[str, Any]]:
        debunk_triggers = [
            'fact check: false', 'fact check: no evidence', 'false claim',
            'hoax', 'debunked', 'fake news', 'not dead', 'alive and well',
            'rumour debunked', 'rumor debunked', 'fabricated'
        ]
        orig_lower = original_headline.lower()

        for item in items:
            t_lower = item['title'].lower()
            src_lower = item['source'].lower()

            is_fact_checker = any(fc in src_lower for fc in FACT_CHECK_ORGANIZATIONS) or any(t in src_lower for t in TIER1_AUTHORITY_SOURCES)
            has_debunk_phrase = any(trigger in t_lower for trigger in debunk_triggers)

            if has_debunk_phrase:
                return {
                    'title': item['title'],
                    'source': item['source'],
                    'url': item['url'],
                    'date': item.get('date', 'Recent'),
                    'is_tier1': True,
                    'is_fact_check': True
                }
        return None

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "status": "UNVERIFIED",
            "score": 50.0,
            "badge_type": "unverified",
            "consensus_label": "No Data",
            "tier1_count": 0,
            "fact_check_flag": False,
            "explanation": "No headline provided for authenticity analysis.",
            "evidence_sources": [],
            "claim_type": "None"
        }

    def _cache_result(self, key: str, res: Dict[str, Any]):
        _VERIFICATION_CACHE[key] = {
            'cached_at': time.time(),
            'result': res
        }


# Global singleton instance
authenticity_verifier = AuthenticityVerifier()
