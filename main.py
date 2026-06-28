
import os
import sys
from pathlib import Path
from collections.abc import Callable

from dotenv import load_dotenv
load_dotenv()

from langchain.tools import tool
from langchain.tools.tool_node import ToolCallRequest
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call, ToolRetryMiddleware
from langchain.messages import ToolMessage
from langsmith import traceable
from firecrawl import Firecrawl
from models import LegoSetReport, LegoSite, BrickEconomy, BrickLinkInventory


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

_bricklink_prompt_path = Path(__file__).resolve().parent / "prompts" / "bricklink_prompt.txt"
BRICKLINK_PROMPT = (
    _bricklink_prompt_path.read_text(encoding="utf-8").strip()
    if _bricklink_prompt_path.exists()
    else LEGO_SITE_PROMPT
)


def _to_tool_text(result: object) -> str:
    """Normalize structured model/tool output into stable text for parent agent tools."""
    if isinstance(result, dict) and "structured_response" in result:
        structured = result["structured_response"]
    else:
        structured = result

    if hasattr(structured, "model_dump_json"):
        return structured.model_dump_json()

    return str(structured)

def create_summary_md(site:str, set_number:str) -> str:
    """ Ingests a set_number and site, performs fire crawl scrape via structured output,
            passes back summarized md."""
    
    # do a broad search
    try:
        results = fire_crawler.search(f"{site} set #{set_number}")
    except Exception as exc:
        return f"Firecrawl search failed for {site} set {set_number}: {exc}"
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

    try:
        page = fire_crawler.scrape(site_url)
    except Exception as exc:
        return f"Firecrawl scrape failed for {site_url}: {exc}"
    if page is None or getattr(page, "markdown", None) is None:
        return f"Unable to scrape page {site_url}"

    raw_markdown = page.markdown or ""

    # Route schema + prompt by source site so each extractor enforces the right shape.
    site_key = site.lower()
    format_and_prompt_by_site = {
        "lego.com": (LegoSite, LEGO_SITE_PROMPT),
        "brickeconomy.com": (BrickEconomy, BRICKECON_PROMPT),
        "bricklink.com": (BrickLinkInventory, BRICKLINK_PROMPT)
    }
    response_format, system_prompt = format_and_prompt_by_site.get(
        site_key,
        (LegoSite, LEGO_SITE_PROMPT),
    )

    # spin up sub_agent via same model to summarize raw markdown into a pydantic model
    sub_agent = create_agent(
        model="gpt-4o-mini",
        response_format=response_format,
        system_prompt=system_prompt,
    )
    
    try:
        summarized_markdown = sub_agent.invoke({"messages": [{"role": "user", "content": f"{raw_markdown}"}]})
    except Exception as exc:
        return f"Extraction agent failed for {site_url}: {exc}"

    return _to_tool_text(summarized_markdown)

@wrap_tool_call
def handle_tool_errors(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage],
) -> ToolMessage:
    """Convert tool exceptions into ToolMessages the model can handle."""
    try:
        return handler(request)
    except Exception as e:
        return ToolMessage(
            content=f"Tool error: Please check your input and try again. ({e})",
            tool_call_id=request.tool_call["id"],
        )


@tool 
def search_lego(lego_set: str) -> str:
    """Search Lego.com for any official Lego data"""
    
    official_lego_md = create_summary_md("lego.com", lego_set)

    return official_lego_md


@tool
def search_brickeconomy(lego_set: str) -> str:
    """Look up necessary BrickEconomy data for historical and potential future data"""

    brickecon_historical_data_md = create_summary_md("brickeconomy.com", lego_set)

    return brickecon_historical_data_md

@tool
def search_bricklink(lego_set: str) -> str:
    """Searches bricklink for various lego set info"""
    
    bricklink_set_data = create_summary_md("bricklink.com", lego_set)

    return bricklink_set_data

@traceable(name="Main StudScan Agent ReAct Loop")
def run_agent(question:str):


    agent = create_agent(model="gpt-4o-mini", 
                         response_format=LegoSetReport,
                         system_prompt=SYSTEM_PROMPT,
                         tools = [search_brickeconomy, search_lego, search_bricklink],
                         middleware=[
                             ToolRetryMiddleware( max_retries= 1 )
                         ])
    
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})

    return result["structured_response"]
        
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <set_number>")
        sys.exit(1)
    set_number = sys.argv[1]
    result = run_agent(f"Tell me about lego {set_number}")
    print("\nReturned value:")
    print(result.verdict)

