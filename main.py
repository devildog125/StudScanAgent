
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langsmith import traceable
from firecrawl import Firecrawl
from models import LegoSetReport, LegoSite, BrickEconomy

fire_crawler = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

SYSTEM_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "system_prompt.txt"
).read_text(encoding="utf-8").strip()

LEGO_SITE_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "lego_site_prompt.txt"
).read_text(encoding="utf-8").strip()

BRICKECON_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "brickecon_prompt.txt"
).read_text(encoding="utf-8").strip()

def create_summary_md(site:str, set_number:str) -> str:
    """ Ingests a set_number and site, performs fire crawl scrape via structured output,
            passes back summarized md."""
    
    # do a broad search
    results = fire_crawler.search(f"{site} set #{set_number}")
    if not results:
        return f"Unable to perform fire crawl search for site: {site} and {set_number}"

    # drill down to get correct search results
    items = []
    if isinstance(results, dict):
        items = results.get("data", [])
    elif isinstance(results, list):
        items = results
    elif hasattr(results, "web"):
        items = results.web

    # loop through the broad list to find the actual site
    site_url = None
    for item in items:
        url = None
        if isinstance(item, dict):
            url = item.get("url") or item.get("link")
        else:
            url = getattr(item, "url", None)

        if not url:
            continue

        lower_url = url.lower()
        is_set_page = site in lower_url

        if is_set_page:
            site_url = url
            break

    # if we don't find anything, return a null
    if not site_url:
        return f"Couldn't find given site {site} from fire crawl search"

    page = fire_crawler.scrape(site_url, limit = 3)
    if page is None or getattr(page, "markdown", None) is None:
        return f"Unable to scrape page {site_url}"

    raw_markdown = page.markdown or ""

    # spin up sub_agent via same model to summarize raw mark down into pydantic model
    sub_agent = create_agent(model="gpt-4o-mini",
                              response_format=LegoSite,
                              system_prompt=LEGO_SITE_PROMPT)
    
    summarized_markdown = sub_agent.invoke({"messages": [{"role": "user", "content": f"{raw_markdown}"}]})

    return summarized_markdown

@tool 
def search_lego(lego_set: str) -> str:
    """Search Lego.com for any official Lego data"""
    
    official_lego_md = create_summary_md("lego.com", lego_set)

    return official_lego_md


@tool
def search_brickeconomy(lego_set: str):
    """Look up necessary BrickEconomy data for historical and potential future data"""

    brickecon_historical_data_md = create_summary_md("brickeconomy.com", lego_set)

    return brickecon_historical_data_md

@tool
def search_bricklink(lego_set: str):
    """Searches bricklink for various lego set info"""
    
    bricklink_set_data = create_summary_md("bricklink.com", lego_set)

    return bricklink_set_data

@traceable(name="Main StudScan Agent ReAct Loop")
def run_agent(question:str):


    agent = create_agent(model="gpt-4o-mini", 
                         response_format=LegoSetReport,
                         system_prompt=SYSTEM_PROMPT,
                         tools = [search_brickeconomy, search_lego])
    
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    return result["structured_response"]
        
if __name__ == "__main__":
    result = run_agent("Tell me about lego 75415")
    print("\nReturned value:")
    print(result.verdict)

