import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urldefrag

unique_pages = set()
def is_relevant(text):
    words = re.findall(r'\w+', text.lower())
    word_count = len(words)
    unique_words = len(set(words))

    stop_words = {'search', 'subscribe', 'select', 'today', 'event', 'navigation',
                  'calendar', 'keyword', 'view', 'previous', 'next', 'contact',
                  'login', 'signup', 'home', 'menu', 'back'}

    common_words = sum(1 for w in words if w in stop_words)

    if word_count < 100:
        for i in range(5):
            print("Irrelevant: Less than 100 words")
            return False

    if unique_words < 40:
        for i in range(5):
            print("Irrelevant: Less than 40 unique words")
            return False

    if common_words / word_count > 0.3:
        for i in range(5):
            print("Irrelevant: too many common words")
            return False

    return True


def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]


def extract_next_links(url, resp):
    if resp.status != 200 or not resp.raw_response:
        return []

    content_type = resp.raw_response.headers.get('content-type')
    if not content_type or "text/html" not in content_type.lower():
        return []

    if "text/html" not in content_type:
        return []

    if url not in unique_pages:
        unique_pages.add(url)
        if len(unique_pages) % 100 == 0:
            print(f"[INFO] Unique pages found: {len(unique_pages)}")

    soup = BeautifulSoup(resp.raw_response.content, 'lxml')

    new_links = []
    unique_URLs = set()
    links = soup.find_all('a')

    text = soup.get_text(separator=" ", strip=True)
    # if not is_relevant(text):
    #     return []

    for link in links:
        href = link.get('href')
        if href:
            # print("Raw URL: " + href)
            clean_url, _ = urldefrag(href)
            # print("Cleaned URL: " + clean_url)
            try:
                if is_valid(clean_url):
                    # print("URL is valid: " + clean_url)
                    # print("------------------------------")
                    new_links.append(clean_url)
                    unique_URLs.add(clean_url)
            except Exception as e:
                print(f"[ERROR] is_valid failed for URL {clean_url}: {e}")
            # else:
            # print("URL is invalid: " + clean_url)
            # print("------------------------------")

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

        if scheme not in set(["http", "https"]):
            # print("Filtered: not http or https")
            return False

        if not (domain.endswith(".ics.uci.edu")
                or domain.endswith(".cs.uci.edu")
                or domain.endswith(".informatics.uci.edu")
                or domain.endswith(".stat.uci.edu")
                or (domain.endswith(".today.uci.edu")
                    and path.startswith("/department/information_computer_sciences/"))):
            # print("Filtered: not in permitted domain")
            return False

        bad_params = {"share=", "action=login", "pwd=", "format=", "page=",
                      "action=download", "upname=", "ical=", "action=edit",
                      "replytocom=", "print=", "session=", "redirect_to="}

        if any(p in query for p in bad_params):
            # print("Filtered: bad parameters in query")
            return False

        if len(query.split("&")) > 5:
            # print("Filtered:", url, "too many queries" )
            return False

        date_pattern = re.compile(r"\d{4}-\d{2}(-\d{2})?")
        if date_pattern.search(path) or date_pattern.search(query):
            # print("Filtered: is a date pattern")
            return False

        # calendar_keywords = [
        #     "ical", "calendar", "month=", "year=",
        #     "day=", "date=", "tribe-bar-date", "event-display", "week=", "day"
        # ]
        # if any(kw in path or kw in query for kw in calendar_keywords):
        #     print("Filtered:", url, " calendar in query or path")
        #     return False

        if re.search(r"(\/[^\/]+)\1{2,}", path):
            # print("Filtered: repeated paths")
            return False

        # bad_paths = ["/pmwiki/", "/layoutvariables", "/includeotherpages", "/charges"]
        # if any(bp in path for bp in bad_paths):
        #     # print("Filtered: is a bad path")
        #     return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())


    except TypeError:
        print("TypeError for ", parsed)
        raise
