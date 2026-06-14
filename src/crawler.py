import os
import re
from xmlrpc import client
import httpx
from bs4 import BeautifulSoup
from apify_client import ApifyClientAsync
from dotenv import load_dotenv
import json
load_dotenv() 

CRAWLER_API_KEY = os.getenv("CRAWLER_API_KEY")
LINKEDIN_JOB_ACTOR = os.getenv("LINKEDIN_JOB_ACTOR", "cheap_scraper/linkedin-job-scraper")


HEADERS = {
 "User-Agent": (
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
 )
}

JUNK_NAMES = {"stealth startup", "stealth", "confidential", "undisclosed"}

def _pick_best_item(items: list) -> dict:
    for item in items:
        name = (item.get("companyName") or "").strip().lower()
        website = item.get("companyWebsite") or ""
        # Skip placeholder/anonymous company names
        if name in JUNK_NAMES or not name:
            continue
        # Require a real external website
        if website.startswith("http") and "linkedin.com" not in website:
            return item
    return items[0] if items else {}

async def crawl_linkedin(linkedin_url:str) -> tuple[str,str]:
    '''Returns (company_name, company_website_url)'''
    if CRAWLER_API_KEY:
        return await _crawl_via_api(linkedin_url)
    return await _crawl_direct(linkedin_url)

async def _crawl_direct(linkedin_url:str) -> tuple[str, str]: 
    async with httpx.AsyncClient(headers = HEADERS, follow_redirects = True, timeout = 20) as client:
        resp = await client.get(linkedin_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    company_name = _extract_company_name(soup)
    company_website = _extract_company_website(soup)
    if not company_website:
        company_website = f"search: official website of {company_name}"
    return company_name, company_website

async def _crawl_via_api(linkedin_url:str) -> tuple[str, str]:
    '''
    Calls an Apify LinkedIn job Actor with the job URL, returns
    (company_name, company_website_url).
    '''
    client = ApifyClientAsync(CRAWLER_API_KEY)
    run_input = {
    "startUrls": [{"url": linkedin_url}],   
    "enrichCompanyData": True,              
    "maxItems": 150,                        
    }

    run = await client.actor(LINKEDIN_JOB_ACTOR).call(run_input=run_input)
    run = run.model_dump()                       # turn the Run object into a plain dict
    result = await client.dataset(run["default_dataset_id"]).list_items()
    items = result.items
    if not items:
        return ('Unknown Company', 'search: official website of Unknown Company')
    item = _pick_best_item(items)

    import json
    print(json.dumps(items[0], indent=2))   # TEMPORARY — shows the real field names

    company_name = (
        item.get('companyName')
        or item.get('company')
        or item.get('company_name')
        or 'Unknown Company'
    )

    company_website = (
        item.get('companyWebsite')
        or item.get('companyUrl')
        or item.get('company_url')
        or None
    )

    if not company_website:
        company_website = f"search: official website of {company_name}" 
    
    return company_name, company_website

def _extract_company_name(soup: BeautifulSoup) -> str | None:
    og_title = soup.find('meta', property = 'og:title')
    if og_title and og_title.get('content') and " - " in og_title['content']:
        return og_title['content'].spit("-")[-1].strip()
    for selector in [
        "a.topcard__org-name-link",
        "span.topcard__flavor",
    ]:
        element = soup.select_one(selector)
        if element and element.get_text(strip = True):
            return element.get_text(strip = True)
        
    return "Unknown Company"

def _extract_company_website(soup: BeautifulSoup) -> str | None:
    for a in soup.findall("a", href = True):
        href = a['href']
        if re.match(r"^https?://", href) and "linkedin.com" in href:
            return href
    return None



