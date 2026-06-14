import asyncio
import sys
from crawler import crawl_linkedin
from navigator_agent import navigate
from schemas import JobSourceResult
async def resolve(linkedin_url:str) -> JobSourceResult:
    company_name, company_website= await crawl_linkedin(linkedin_url)
    nav = await navigate(company_website)
    return JobSourceResult(
        company_name = company_name,
        careers_url = nav.careers_url,
        position_url = nav.position_url,

    )

def cli():
    if len(sys.argv) != 2:
        print("Usage: python pipeline.py <linkedin_url> ")
        raise SystemExit(1)
    result = asyncio.run(resolve(sys.argv[1]))

    print(f"\n{result.company_name}, {result.careers_url}, {result.position_url}")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    cli()