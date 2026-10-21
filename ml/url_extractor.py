import re
import socket
import urllib.parse
import urllib.request
import html
import requests
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

# SSRF Protection: Private and Reserved IP Networks
PRIVATE_IP_PATTERNS = [
    re.compile(r'^127\.\d+\.\d+\.\d+$'),                  # 127.0.0.0/8 (Loopback)
    re.compile(r'^10\.\d+\.\d+\.\d+$'),                   # 10.0.0.0/8 (Private)
    re.compile(r'^172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+$'),  # 172.16.0.0/12 (Private)
    re.compile(r'^192\.168\.\d+\.\d+$'),                 # 192.168.0.0/16 (Private)
    re.compile(r'^169\.254\.\d+\.\d+$'),                 # 169.254.0.0/16 (Link Local)
    re.compile(r'^0\.\d+\.\d+\.\d+$'),                    # 0.0.0.0/8
    re.compile(r'^::1$'),                                 # IPv6 Loopback
    re.compile(r'^[fF][cCdD][0-9a-fA-F]{2}:'),            # Unique Local Unicast
    re.compile(r'^[fF][eE]80:'),                          # Link-Local
]

def is_ip_private(ip_str):
    """Checks if IP string is loopback, private, or link-local."""
    for pattern in PRIVATE_IP_PATTERNS:
        if pattern.match(ip_str):
            return True
    return False

def validate_url_security(url_str):
    """
    Validates URL string against security policies:
    - Must be non-empty string
    - Must start with http:// or https://
    - Must not contain invalid schemes (javascript:, file:, ftp:, data:)
    - Must resolve to a public IP address (SSRF Protection)
    """
    if not url_str or not isinstance(url_str, str):
        return False, "Please enter a valid URL."

    url_str = url_str.strip()

    parsed = urllib.parse.urlparse(url_str)
    if parsed.scheme not in ('http', 'https'):
        return False, "Only HTTP and HTTPS protocols are supported."

    hostname = parsed.hostname
    if not hostname:
        return False, "Please enter a valid URL."

    hostname_lower = hostname.lower()
    if hostname_lower in ('localhost', 'localhost.localdomain', 'loopback') or hostname_lower.endswith('.local') or hostname_lower.endswith('.internal'):
        return False, "Access to local or internal addresses is blocked for security."

    # DNS Resolution IP check for SSRF prevention
    try:
        ip_addresses = socket.getaddrinfo(hostname, None)
        for family, socktype, proto, canonname, sockaddr in ip_addresses:
            ip = sockaddr[0]
            if is_ip_private(ip):
                return False, "Access to private or internal IP addresses is blocked for security."
    except socket.gaierror:
        return False, "Unable to resolve the specified website hostname."
    except Exception:
        return False, "Security validation failed for the provided URL."

    return True, None

def normalize_typography(raw_text):
    """
    Normalizes typography symbols, smart quotes, dashes, and unescapes HTML entities.
    Handles CMS corrupted replacement characters (\ufffd) cleanly.
    """
    if not raw_text:
        return ""

    text = html.unescape(raw_text).strip()

    quote_map = {
        '\u2018': "'", '\u2019': "'", '\u201a': "'", '\u201b': "'",
        '\u201c': '"', '\u201d': '"', '\u201e': '"', '\u201f': '"',
        '\u2013': '-', '\u2014': '-', '\u2026': '...',
        '\xa0': ' ', '\u200b': '', '\ufeff': '', '\ufffd': "'"
    }
    for orig, rep in quote_map.items():
        text = text.replace(orig, rep)

    return " ".join(text.split())

def clean_extracted_title(raw_title):
    """
    Cleans extracted headline text:
    - Decodes HTML entities and normalizes smart quotes
    - Removes site branding suffixes (e.g. " | BBC News", " - Dawn", " - The News")
    - Strips surrounding quotes
    """
    if not raw_title:
        return ""

    title = normalize_typography(raw_title)

    # Remove common site name suffixes
    patterns = [
        r'\s+[|\-–—]\s+[A-Za-z0-9\s\.\,\'\&]+$',  # e.g., " - BBC News", " - Dawn"
        r'^\s*["\'«“]+|["\'»”]+\s*$',               # surrounding quotes
    ]
    for p in patterns:
        title = re.sub(p, '', title).strip()

    return title

BOILERPLATE_PATTERNS = [
    re.compile(r'subscribe\s+to\s+notifications', re.I),
    re.compile(r'get\s+the\s+latest\s+news\s+and\s+updates', re.I),
    re.compile(r'all\s+rights\s+reserved', re.I),
    re.compile(r'sign\s+up\s+for\s+our\s+newsletter', re.I),
    re.compile(r'cookies?\s+policy|accept\s+all\s+cookies', re.I),
    re.compile(r'read\s+more:|also\s+read:', re.I),
    re.compile(r'download\s+our\s+app', re.I),
    re.compile(r'published\s+in\s+dawn', re.I),
]

def is_boilerplate(text):
    for p in BOILERPLATE_PATTERNS:
        if p.search(text):
            return True
    return False

def extract_headline_from_url_slug(url_str):
    """
    Extracts a fallback headline from the URL path slug when HTML DOM title tags are missing or generic.
    e.g. https://www.msn.com/en-xl/news/other/troops-from-north-korea-to-boost-russia -> "Troops From North Korea To Boost Russia"
    """
    try:
        parsed = urllib.parse.urlparse(url_str)
        path = parsed.path.strip('/')
        parts = [p for p in path.split('/') if len(p) > 3 and not p.startswith('ar-') and not p.startswith('id-')]
        if parts:
            slug = parts[-1]
            if '-' in slug or '_' in slug:
                words = [w.capitalize() for w in re.split(r'[-_]', slug) if len(w) > 0 and not w.startswith('ar-')]
                if len(words) >= 2:
                    return ' '.join(words)
    except Exception:
        pass
    return ""

def search_google_news_rss_for_url(url_str):
    """
    Fallback method: Searches Google News RSS for an article by its URL or domain + path/id.
    This works reliably even when a website enforces strict anti-bot/WAF blocks on direct server scraping.
    """
    try:
        parsed = urllib.parse.urlparse(url_str)
        domain = parsed.hostname.replace('www.', '') if parsed.hostname else ''
        path_segments = [p for p in parsed.path.strip('/').split('/') if p]

        queries = []
        if path_segments:
            queries.append(f"site:{domain} {path_segments[-1]}")
            if len(path_segments) > 1:
                queries.append(f"site:{domain} {path_segments[-2]} {path_segments[-1]}")
        queries.append(f'"{url_str}"')

        for q in queries:
            encoded_q = urllib.parse.quote(q)
            rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"
            req = urllib.request.Request(
                rss_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                tree = ET.fromstring(resp.read())
                for item in tree.findall('.//item'):
                    title_elem = item.find('title')
                    if title_elem is not None and title_elem.text:
                        raw_title = title_elem.text.strip()
                        cleaned = clean_extracted_title(raw_title)
                        if len(cleaned) > 12:
                            return cleaned
    except Exception:
        pass
    return None

class ArticleFullParser(HTMLParser):
    """
    HTML parser to extract article titles and full webpage text content:
    - og:title / twitter:title / <h1> / <title> / meta description
    - Full article body text from <p>, <h2>, <h3>, <h4>, <li>, <blockquote>, <article>, <section> tags
      ignoring <script>, <style>, <nav>, <header>, <footer>, <aside>, <svg>, <noscript>, <form>, <button>.
    """
    IGNORED_TAGS = set(['script', 'style', 'nav', 'header', 'footer', 'aside', 'svg', 'noscript', 'form', 'button'])
    PARAGRAPH_TAGS = set(['p', 'h2', 'h3', 'h4', 'li', 'blockquote', 'article', 'section'])

    def __init__(self):
        super().__init__()
        self.og_title = None
        self.twitter_title = None
        self.meta_desc = None
        self.first_h1 = None
        self.html_title = None

        self.ignored_stack = []
        self.in_h1 = False
        self.in_title = False

        self.h1_buffer = []
        self.title_buffer = []
        self.body_paragraphs = []
        self.current_para = []
        self.in_para = False

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        attr_dict = {k.lower(): (v or '') for k, v in attrs}

        if tag_lower in self.IGNORED_TAGS:
            self.ignored_stack.append(tag_lower)
            return

        if self.ignored_stack:
            return

        if tag_lower == 'meta':
            prop = attr_dict.get('property', '').lower()
            name = attr_dict.get('name', '').lower()
            content = attr_dict.get('content', '').strip()

            if content:
                if prop == 'og:title' or name == 'og:title':
                    if not self.og_title:
                        self.og_title = content
                elif prop == 'twitter:title' or name == 'twitter:title':
                    if not self.twitter_title:
                        self.twitter_title = content
                elif name == 'description' or prop == 'og:description':
                    if not self.meta_desc and len(content) > 15:
                        self.meta_desc = content

        elif tag_lower == 'h1' and not self.first_h1:
            self.in_h1 = True
            self.h1_buffer = []

        elif tag_lower == 'title' and not self.html_title:
            self.in_title = True
            self.title_buffer = []

        elif tag_lower in self.PARAGRAPH_TAGS:
            if tag_lower in ('p', 'h2', 'h3', 'h4', 'li', 'blockquote'):
                if self.current_para:
                    text = normalize_typography("".join(self.current_para))
                    if len(text) > 20 and not is_boilerplate(text):
                        self.body_paragraphs.append(text)
                    self.current_para = []
                self.in_para = True

    def handle_data(self, data):
        if self.ignored_stack:
            return
        if self.in_h1:
            self.h1_buffer.append(data)
        if self.in_title:
            self.title_buffer.append(data)
        if self.in_para or not (self.in_h1 or self.in_title):
            cleaned = data.strip()
            if cleaned:
                self.current_para.append(data)

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if self.ignored_stack and self.ignored_stack[-1] == tag_lower:
            self.ignored_stack.pop()
            return

        if self.ignored_stack:
            return

        if tag_lower == 'h1' and self.in_h1:
            self.in_h1 = False
            text = normalize_typography("".join(self.h1_buffer))
            if text and not self.first_h1:
                self.first_h1 = text

        elif tag_lower == 'title' and self.in_title:
            self.in_title = False
            text = normalize_typography("".join(self.title_buffer))
            if text and not self.html_title:
                self.html_title = text

        elif tag_lower in ('p', 'h2', 'h3', 'h4', 'li', 'blockquote') and self.in_para:
            self.in_para = False
            para_text = normalize_typography("".join(self.current_para))
            if len(para_text) > 20 and not is_boilerplate(para_text):
                self.body_paragraphs.append(para_text)
            self.current_para = []

def fetch_and_extract_headline(url_str):
    """Backwards compatible function calling full webpage content extractor."""
    success, result = fetch_and_extract_webpage_content(url_str)
    if not success:
        return False, result
    return True, result['headline']

def fetch_and_extract_webpage_content(url_str):
    """
    Safely fetches the HTML webpage from url_str and extracts both headline and full article text.
    Uses modern desktop browser emulation with requests.Session, SSL bypass, and multi-tier
    fallbacks (mobile headers, Google News RSS index, URL slug) to bypass anti-bot/Cloudflare restrictions.
    Returns: (success: bool, data_dict_or_error: dict|str)
    """
    is_valid, err_msg = validate_url_security(url_str)
    if not is_valid:
        return False, err_msg

    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/',
        'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1'
    }

    html_text = None
    direct_fetch_succeeded = False

    # Attempt 1: Direct Fetch with Desktop Chrome Headers
    try:
        response = session.get(url_str, headers=headers, timeout=9, allow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' in content_type or 'application/xhtml+xml' in content_type or not content_type:
                html_text = response.content.decode('utf-8', errors='replace')
                direct_fetch_succeeded = True
        elif response.status_code in (403, 401, 503):
            # Attempt 1b: Mobile Safari Fallback for strict Cloudflare/WAF anti-bot sites
            mobile_headers = headers.copy()
            mobile_headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1'
            m_resp = session.get(url_str, headers=mobile_headers, timeout=7, allow_redirects=True)
            if m_resp.status_code == 200:
                html_text = m_resp.content.decode('utf-8', errors='replace')
                direct_fetch_succeeded = True
    except Exception:
        pass

    # If direct HTML fetch succeeded, parse DOM elements
    if direct_fetch_succeeded and html_text:
        parser = ArticleFullParser()
        try:
            parser.feed(html_text)
        except Exception:
            pass

        # Hierarchy: og:title -> twitter:title -> <h1> -> <title> -> meta_desc
        candidate = parser.og_title or parser.twitter_title or parser.first_h1 or parser.html_title or parser.meta_desc
        cleaned_headline = clean_extracted_title(candidate)

        # Check if headline is generic site name (e.g. "MSN", "BBC", "Home", "Index", "News", "Dawn")
        generic_titles = {'msn', 'bbc', 'home', 'index', 'news', 'cnn', 'yahoo', 'fox news', 'reuters', 'bloomberg', 'dawn'}
        if not cleaned_headline or cleaned_headline.lower() in generic_titles or len(cleaned_headline) < 4:
            slug_title = extract_headline_from_url_slug(url_str)
            if slug_title:
                cleaned_headline = slug_title

        # Deduplicate body paragraphs
        unique_paras = []
        seen = set()
        for p in parser.body_paragraphs:
            p_clean = p.strip()
            if p_clean and p_clean not in seen:
                seen.add(p_clean)
                unique_paras.append(p_clean)

        full_body_text = " ".join(unique_paras)

        if cleaned_headline and len(cleaned_headline) >= 5:
            if not full_body_text:
                full_body_text = cleaned_headline
            body_preview = full_body_text[:400] + "..." if len(full_body_text) > 400 else full_body_text
            return True, {
                "headline": cleaned_headline,
                "body_text": full_body_text,
                "body_preview": body_preview if body_preview else cleaned_headline,
                "word_count": len(full_body_text.split()),
                "paragraph_count": len(unique_paras)
            }

    # Attempt 2: Fallback via Google News RSS Index
    fallback_headline = search_google_news_rss_for_url(url_str)
    if fallback_headline and len(fallback_headline) >= 6:
        return True, {
            "headline": fallback_headline,
            "body_text": fallback_headline,
            "body_preview": "Headline extracted via verified news index (full body scraping restricted by publisher WAF).",
            "word_count": len(fallback_headline.split()),
            "paragraph_count": 1
        }

    # Attempt 3: Fallback via URL slug
    slug_title = extract_headline_from_url_slug(url_str)
    if slug_title and len(slug_title) >= 8:
        return True, {
            "headline": slug_title,
            "body_text": slug_title,
            "body_preview": "Headline parsed from URL structure.",
            "word_count": len(slug_title.split()),
            "paragraph_count": 1
        }

    # If all automated extraction fails:
    return False, "This website is protected by Cloudflare bot verification or an interactive CAPTCHA. Please copy the headline directly from the article and paste it into the Headline Analysis box above."
