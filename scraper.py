import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urldefrag


def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    if resp.status != 200 or not resp.raw_response:
        return []

    content_type = resp.raw_response.headers.get('content-type')
    if "text/html" not in content_type:
        return []

    soup = BeautifulSoup(resp.raw_response.content, 'lxml')

    new_links = []
    unique_URLs = set()
    links = soup.find_all('a')

    for link in links:
        href = link.get('href')
        if href:
            print("Raw URL: " + href)
            clean_url, _ = urldefrag(href)
            print("Cleaned URL: " + clean_url)
            if is_valid(clean_url):
                print("URL is valid: " + clean_url)
                new_links.append(clean_url)
                unique_URLs.add(clean_url)
            else:
                print("URL is invalid: " + clean_url)
    print()
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
        # print("Scheme: " + scheme)
        # print("Domain: " + domain)
        # print("Path: " + path)
        # print("Query: " + query)



        if scheme not in set(["http", "https"]):
            return False

        if not(domain.endswith(".ics.uci.edu")
               or domain.endswith(".cs.uci.edu")
               or domain.endswith(".informatics.uci.edu")
               or domain.endswith(".stat.uci.edu")
               or (domain.endswith(".today.uci.edu")
                   and path.startswith("/department/information_computer_sciences/"))):
            return False

        if ("share=" or "action=login" or "pwd=" or "format=" or "page=") in query:
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

    except TypeError:
        print ("TypeError for ", parsed)
        raise
