# AI Job Source Agent

Given a LinkedIn jobs listing, this service returns a company's careers page and one open position on that company's own site.

**Output format:** `company_name, careers_url, position_url`

This is an implementation of Part 2 of the Jobnova take-home challenge.

## What it does

The service takes a LinkedIn jobs URL and runs a two-stage pipeline:

1. **Extract** the company name and website from LinkedIn (via a third-party crawler).
2. **Navigate** that company's own website with an autonomous browser agent to find the careers page and one open position.

The two URLs in the final output come from the company's own site, not from LinkedIn. LinkedIn is only used to identify which company to navigate.

## Architecture

```
POST /resolve { linkedin_url }
        |
        v
  pipeline.resolve()
        |
        |-- Stage 1: crawler.crawl_linkedin()
        |     LinkedIn jobs URL  -->  (company_name, company_website)
        |     [Apify LinkedIn actor, thin and swappable]
        |
        |-- Stage 2: navigator_agent.navigate()      <- the autonomous agent
        |     company_website  -->  browser-use navigates the site
        |                       -->  (careers_url, position_url)
        |
        v
  JobSourceResult: company_name, careers_url, position_url   (typed JSON)
```

**Stage 1 is deliberately thin.** LinkedIn blocks direct scraping, so this stage uses a third-party Apify actor and is kept minimal and swappable. It returns the company name (which flows straight to the output) and the company website (which becomes the input to Stage 2).

**Stage 2 is the core of the project.** A browser agent reasons its way around a company website it has never seen before, locating the careers page and an open position. This is the part of the task that a fixed scraper could not do.

## Project structure

| File | Responsibility |
|------|----------------|
| `src/schemas.py` | Pydantic models for the request and the result triple |
| `src/crawler.py` | Stage 1: company name and website from LinkedIn (Apify) |
| `src/navigator_agent.py` | Stage 2: browser agent that finds careers page and one position |
| `src/pipeline.py` | Ties the two stages together; also runnable as a CLI |
| `src/main.py` | FastAPI app exposing `/resolve` and `/health` |

## Setup

Requires Python 3.13. Uses [uv](https://github.com/astral-sh/uv) for environment management.

```bash
uv venv --python 3.13
source .venv/bin/activate
uv pip install -r requirements.txt
```

Create a `.env` file in the project root with your keys:

```
ANTHROPIC_API_KEY=your_anthropic_key
CRAWLER_API_KEY=your_apify_token
```

## Running

### As an API

```bash
cd src
uv run uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000/docs` for an interactive form (Swagger UI). Send a POST to `/resolve`:

```json
{
  "linkedin_url": "https://www.linkedin.com/jobs/search/?keywords=machine%20learning%20engineer&location=United%20States&f_TPR=r604800"
}
```

A request takes roughly 20 to 40 seconds, because the scrape and the live browser navigation both happen inside the single request. A browser window opens during the call so the agent's navigation is visible.

### From the command line

```bash
cd src
uv run python pipeline.py "https://www.linkedin.com/jobs/search/?keywords=machine%20learning%20engineer&location=United%20States"
```

### Example output

```json
{
  "company_name": "Deepgram",
  "careers_url": "https://deepgram.com/careers",
  "position_url": "https://jobs.ashbyhq.com/Deepgram/aafbab17-4caa-4b87-811c-21acfc566cf4?employmentType=FullTime"
}
```

## Input note

Stage 1 uses a LinkedIn jobs *search* URL (a job listings page), not a single job-view URL. The crawler returns the listings on that page, and the pipeline picks the first company that has a real, navigable website. A recency filter such as `&f_TPR=r604800` (last week) or `&f_TPR=r86400` (last 24 hours) can be appended to the search URL.

## Design decisions

**An agent, not a scraper, for Stage 2.** Every company structures its site differently. The careers link might be in the header, the footer, on a subdomain like `jobs.company.com`, or on an external applicant tracking system. A hardcoded scraper breaks per site. A browser agent generalizes across sites it has never seen, which is the capability the task is testing. The agent handles external ATS redirects (Greenhouse, Lever, Workday, Ashby, Zoho Recruit), which is where most companies actually host their jobs.

**Company filtering in Stage 1.** LinkedIn search results are full of staffing firms, anonymous "Stealth Startup" placeholders, and companies with no real website, all of which are dead ends for navigation. The crawler skips placeholder names and companies without a genuine external website, so the agent is handed a company that actually has somewhere to navigate.

**Graceful failure.** When a company genuinely has no navigable careers page, the agent stops and returns `not found` for the missing fields rather than spinning indefinitely. A step cap (`max_steps`) acts as a hard upper bound on the agent's exploration so a doomed run cannot run away. A "not found" result is a correct, valid output, not a crash.

**Isolated browser session.** The agent navigates untrusted sites on the open web, so it runs in a throwaway browser session that is created and discarded per run. During testing this caught a scareware popup served by a third-party ad; because the session is isolated and disposable, it posed no risk to the host machine.

**Structured output.** The agent returns a typed `NavigationResult` rather than free text, so the two URLs are validated and land in the correct fields. The result is read from browser-use's `structured_output`, which is the parsed Pydantic model.

## Tech stack

- **FastAPI** for the API layer
- **Pydantic** for typed request and response validation
- **Apify** (`cheap_scraper/linkedin-job-scraper`) for the LinkedIn extraction
- **browser-use** (CDP-based browser automation) for the autonomous navigation
- **Claude Sonnet** as the agent's reasoning model

## Known limitations

- A request is synchronous and takes 20 to 40 seconds because real scraping and live navigation happen per call. For production this would move to a background job with a status endpoint.
- The Apify actor used has a pay-per-result minimum, so each run scrapes a batch of listings even though only the first usable company is used.
- Some companies host jobs only on LinkedIn and have no careers page of their own. These correctly return `not found`.
- Heavy, JavaScript-rendered sites occasionally produce transient page-read timeouts. The agent falls back to reading the screenshot and continues, but these sites produce noisier logs.
