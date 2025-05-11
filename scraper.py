import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urldefrag, urljoin
from PartA import tokenize
import json
from collections import Counter, defaultdict
import hashlib
import math

with open("stopwords.txt", "r", encoding="utf-8") as f:
    stopwords = set(w.strip() for w in f.readlines())

word_counter = Counter()
subdomain_counter = defaultdict(int)
word_in_page = dict()
most_word_in_page = ("", 0)

stats_file = "stats.json"
save_frequency = 100

page_hashes = set()  # ← GLOBAL: para exact duplicate detection
simhashes = set()


def simhash(tokens):
    hashbits = 64
    v = [0] * hashbits
    for token in tokens:
        h = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
        for i in range(hashbits):
            bitmask = 1 << i
            v[i] += 1 if h & bitmask else -1
    fingerprint = 0
    for i in range(hashbits):
        if v[i] > 0:
            fingerprint |= 1 << i
    return fingerprint


def hamming_distance(x, y):
    return bin(x ^ y).count('1')


def save_stats():
    stats = {
        "unique_pages": len(word_in_page),
        "most_word_in_page": {
            "url": most_word_in_page[0],
            "word_count": most_word_in_page[1]
        },
        "top_50_words": word_counter.most_common(50),
        "subdomains": dict(sorted(subdomain_counter.items())),
        "word_in_page": word_in_page
    }
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"[STATS] Stats saved in {stats_file}")


def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]


def extract_next_links(url, resp):
    if resp.status != 200 or not resp.raw_response:
        return []

    content_type = resp.raw_response.headers.get('content-type')
    if not content_type or "text/html" not in content_type.lower():
        return []

    soup = BeautifulSoup(resp.raw_response.content, 'lxml')
    text = soup.get_text(separator=" ", strip=True).lower()
    raw_tokens = tokenize(text)
    tokens = [t for t in raw_tokens if t not in stopwords and len(t) > 1 and not t.isdigit()]

    # EXACT DUPLICATE DETECTION
    page_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
    if page_hash in page_hashes:
        with open("filtered_urls.log", "a", encoding="utf-8") as log_file:
            log_file.write(f"[DUPLICATE] Motivo: Exact duplicate hash → {url}\n")
        return []
    page_hashes.add(page_hash)

    # NEAR DUPLICATE DETECTION
    fingerprint = simhash(tokens)
    for existing in simhashes:
        if hamming_distance(fingerprint, existing) <= 3:
            with open("filtered_urls.log", "a", encoding="utf-8") as log_file:
                log_file.write(f"[DUPLICATE] Motivo: Near duplicate (SimHash) → {url}\n")
            return []
    simhashes.add(fingerprint)

    word_counter.update(tokens)
    word_count = len(tokens)
    word_in_page[url] = word_count

    global most_word_in_page
    if word_count > most_word_in_page[1]:
        most_word_in_page = (url, word_count)

    parsed = urlparse(url)
    if parsed.netloc.endswith(".ics.uci.edu"):
        subdomain_counter[parsed.netloc] += 1

    if len(word_in_page) % save_frequency == 0:
        save_stats()

    new_links = []
    links = soup.find_all('a')

    for link in links:
        href = link.get('href')
        if href:
            joined = urljoin(url, href)
            clean_url, _ = urldefrag(joined)
            try:
                if is_valid(clean_url):
                    new_links.append(clean_url)
            except Exception as e:
                print(f"[ERROR] is_valid failed for URL {clean_url}: {e}")
    return new_links

    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path
        scheme = parsed.scheme
        query = parsed.query

        def log_reason(reason):
            with open("filtered_urls.log", "a", encoding="utf-8") as log_file:
                log_file.write(f"[{domain}] Motivo: {reason} → {url}\n")

        if scheme not in {"http", "https"}:
            log_reason("Invalid Scheme")
            return False

        if not (domain == "ics.uci.edu"
                or domain.endswith(".ics.uci.edu")
                or domain == "cs.uci.edu"
                or domain.endswith(".cs.uci.edu")
                or domain == "informatics.uci.edu"
                or domain.endswith(".informatics.uci.edu")
                or domain == "stat.uci.edu"
                or domain.endswith(".stat.uci.edu")
                or (domain == "today.uci.edu" and path.startswith("/department/information_computer_sciences/"))):
            log_reason("Out of permitted domain")
            return False

        bad_params = {"share=", "action=login", "pwd=", "format=",
                      "action=download", "upname=", "ical=", "action=edit",
                      "replytocom=", "print=", "session=", "redirect_to=",
                      "post_type=", "tribe-bar-date=", "eventDisplay=past",
                      "do=media", "tab_files=", "image=", "do=diff", "difftype="}

        if any(p in query for p in bad_params):
            log_reason("Query bad parameters")
            return False

        if re.search(r'/day/(19|20)\d{2}-\d{2}-\d{2}', path):
            log_reason("Tramp: specific day calendar")
            return False

        segments = path.strip("/").split("/")
        if len(segments) != len(set(segments)):
            log_reason("Trap: repeated path segments")
            return False

        if re.search(r'/events?/\d{4}-\d{2}-\d{2}', path):
            log_reason("Trap: /event(s)/ with specific date")
            return False

        if re.search(r'/events?/month(/\\d{4}-\\d{2})?/?$', path):
            log_reason("Trap : /events/month/")
            return False

        if re.search(r'/events/category/.*/(19|20)\d{2}-\d{2}', path):
            log_reason("Trap: /events/category/.../YYYY-MM")
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except Exception as e:
        with open("filtered_urls.log", "a", encoding="utf-8") as log_file:  ### CAMBIO: Registro de error
            log_file.write(f"[ERROR] Motivo: Exception ({e}) → {url}\n")
        return False
