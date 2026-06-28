
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


SYSTEM_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "system_prompt.txt"
).read_text(encoding="utf-8").strip()

LEGO_SITE_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "lego_site_prompt.txt"
).read_text(encoding="utf-8").strip()






fire_crawler = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))


@tool
def search_brickeconomy(lego_set: str):
    """Look up necessary Brickeconomy data"""

    # do a general firecrawl web search here but send brickeconomy search with set number // retry only 3 times
    brickeconomy_search = fire_crawler.search(query = f"www.brickeconomy.com/search?query={lego_set}", limit = 3)
    
    # brickeconomy search results should have correct results as the first item, grab that url
    # as we going to pass that and do a more refined scrape next for better details
    brickeconomy_search_item_url = brickeconomy_search.web[0].url

    # take new result and pass to scraper for set details
    brickeconomy_details = fire_crawler.scrape(brickeconomy_search_item_url, formats=["markdown", "html"])

    raw_markdown = brickeconomy_details.markdown or ""

    # summarized_markdown

    return raw_markdown

@tool 
def search_lego(lego_set: str):
    """Search Lego.com for any relevant data up to date unless its bui

    Args:
        query: Search terms to look for
        limit: Maximum number of results to return
    """

    # do a broad search
    results = fire_crawler.search(f"Lego.com set #{lego_set}")
    if not results:
        return f"Nothing found on Lego.com for {lego_set}"

    items = []
    if isinstance(results, dict):
        items = results.get("data", [])
    elif isinstance(results, list):
        items = results
    elif hasattr(results, "web"):
        items = results.web

    # loop through the broad list to find the actual legit lego site
    lego_url = None
    for item in items:
        url = None
        if isinstance(item, dict):
            url = item.get("url") or item.get("link")
        else:
            url = getattr(item, "url", None)

        if not url:
            continue

        lower_url = url.lower()
        is_lego = "lego.com" in lower_url

        if is_lego:
            lego_url = url
            break

    if not lego_url:
        return f"No official lego.com non-instructions page found for {lego_set}"

    page = fire_crawler.scrape_url(lego_url)
    if page is None or getattr(page, "markdown", None) is None:
        return f"Found {lego_url} but could not scrape markdown"

    raw_markdown = page.markdown or ""

    # spin up sub_agent via same model to summarize raw mark down into pydantic model
    sub_agent = create_agent(model="gpt-4o-mini",
                              response_format=LegoSite,
                              system_prompt=LEGO_SITE_PROMPT)
    
    summarized_markdown = sub_agent.invoke({"messages": [{"role": "user", "content": f"{raw_markdown}"}]})

    return summarized_markdown


@tool
def search_brickowl(lego_set: str):
    """Searches Brickowl for various lego set info"""



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

