import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urldefrag, urljoin
from PartA import tokenize
import json
from collections import Counter, defaultdict
import hashlib
import os

with open("stopwords.txt", "r", encoding="utf-8") as f:
    stopwords = set(w.strip() for w in f.readlines())

word_counter = Counter()
subdomain_counter = defaultdict(int)
word_in_page = dict()
most_word_in_page = ("", 0)

stats_file = "stats.json"
save_frequency = 100

page_hashes = set()  # ← Exact duplicate detection
simhashes = set()


def load_stats():
    global word_counter, subdomain_counter, word_in_page, most_word_in_page
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                word_counter.update(dict(data.get("top_50_words", [])))
                subdomain_counter.update(data.get("subdomains", {}))
                word_in_page.update(data.get("word_in_page", {}))
                most = data.get("most_word_in_page", {})
                if most and most.get("url") and most.get("word_count", 0) > most_word_in_page[1]:
                    most_word_in_page = (most["url"], most["word_count"])
            print(f"[STATS] Cargadas estadísticas desde {stats_file}")
        except Exception as e:
            print(f"[STATS] Error al cargar {stats_file}: {e}")


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
    print(f"[STATS] Stats saved in {stats_file} | Unique pages: {len(word_in_page)}")


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


# ← Cargar stats al inicio
load_stats()


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

    # Exact duplicate
    page_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
    if page_hash in page_hashes:
        print("Exact duplicate hash → {url}\n")
        with open("filtered_urls.log", "a", encoding="utf-8") as log_file:
            log_file.write(f"[DUPLICATE] Motivo: Exact duplicate hash → {url}\n")
        return []
    page_hashes.add(page_hash)

    # Near duplicate
    fingerprint = simhash(tokens)
    for existing in simhashes:
        if hamming_distance(fingerprint, existing) <= 3:
            print("Near duplicate (SimHash) → {url}\n")
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
    for link in soup.find_all('a'):
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


def is_valid(url):
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

        if "doku.php" in url:
            log_reason("Trap: DokuWiki URL")
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

        if re.search(r'/-/(blob|blame|raw|commits|tree)/', path) and "README.md" in path:
            log_reason("Trap: GitLab redundant README views")
            return False

        if re.search(r'~epstein/pix/', path):
            log_reason("Low-value personal photo page (epstein/pix)")
            return False

        if "/epstein/pix/" in path:
            log_reason("Low-value personal photo page (epstein/pix)")
            return False

        # GitLab commit and tree views
        if "/-/commit/" in path:
            log_reason("Trap: GitLab commit view")
            return False

        if "/-/tree/" in path:
            log_reason("Trap: GitLab tree view")
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
        with open("filtered_urls.log", "a", encoding="utf-8") as log_file:
            log_file.write(f"[ERROR] Motivo: Exception ({e}) → {url}\n")
        return False
