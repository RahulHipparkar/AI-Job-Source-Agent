import os
import json
from browser_use import Agent
from dotenv import load_dotenv
from pydantic import ValidationError
load_dotenv()




try:
    from browser_use import ChatAnthropic
except ImportError as e:
    from browser_use.llm import ChatAnthropic

from schemas import NavigationResult

HEADLESS = os.getenv("BROWSER_HEADLESS", "0") == "1"

def _build_llm():
    return ChatAnthropic(model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"))

def _build_task(company_website: str) -> str:
    return (
        f"You are given a company's website or a search hint: {company_website}\n\n"
        "GOAL: Find the company's careers/jobs page, then open ONE currently-open "
        "job posting, and return both URLs.\n\n"
        "STEPS:\n"
        "1. If you were given a search hint (text starting with 'search:') rather "
        "than a real URL, first search the web to find the company's official "
        "website, then go to it.\n"
        "2. On the website, locate the careers or jobs page. Look in the header "
        "navigation, the footer, and 'About'/'Company' menus. It may live on a "
        "subdomain (e.g. jobs.<company>.com) or an external site (Greenhouse, "
        "Lever, Workday, Zoho Recruit) — following those external links is fine.\n"
        "3. On the careers page, pick exactly ONE open position and open its "
        "posting. If opening it switches to a new tab, use the new tab's URL.\n\n"
        "RETURN:\n"
        "- careers_url: the URL of the careers/jobs page you found.\n"
        "- position_url: the URL of the one open position you opened.\n\n"
        "RULES:\n"
        "- Only return URLs you actually navigated to. Never invent or guess a URL.\n"
        "- If after a focused search (checking the header, footer, and an obvious "
        "careers link) you cannot find a careers page, stop and return 'not found' "
        "for careers_url and 'not found' for position_url.\n"
        "- If you find a careers page but it lists no open positions, return the "
        "careers_url you found and 'not found' for position_url.\n"
        "- Do not keep searching indefinitely. If a company clearly has no "
        "navigable careers page, fail gracefully rather than clicking endlessly.\n"
    )

async def navigate(company_website: str) -> NavigationResult:
    agent = Agent(
        task = _build_task(company_website),
        llm = _build_llm(),
        output_model_schema = NavigationResult,
        headless = HEADLESS
    )

    history = await agent.run(max_steps = 10)
   

    result = getattr(history, "structured_output", None)
    if isinstance(result, NavigationResult):
        return result
    
    final = history.final_result()

    if isinstance( final, NavigationResult):
        return final
    

    if isinstance(final, dict):
         return NavigationResult(**final)
    
    if isinstance(final, str):
        try:
            return NavigationResult(**json.loads(final))
        except (json.JSONDecodeError, ValidationError, TypeError):
            pass
    
    return NavigationResult(careers_url="not found", position_url="not found")




