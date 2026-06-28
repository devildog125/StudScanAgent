
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
from pydantic import BaseModel, Field
from typing import Optional

class ResalePrices(BaseModel):
    bricklink: Optional[float] = None
    brickowl: Optional[float] = None
    brickeconomy: Optional[float] = None

class LegoSetReport(BaseModel):
    set_number: str
    set_name: Optional[str] = None
    theme: Optional[str] = None
    retail_price_usd: Optional[float] = Field(None, description="Original MSRP in USD, sourced from LEGO.com")
    piece_count: Optional[int] = None
    availability_status: Optional[str] = Field(None, description="in production / retired / exclusive")
    resale_new: ResalePrices = Field(default_factory=ResalePrices)
    resale_used: ResalePrices = Field(default_factory=ResalePrices)
    growth_percent_since_release: Optional[float] = None
    retirement_date: Optional[str] = None
    sources_missing: list[str] = Field(default_factory=list)
    discrepancies: list[str] = Field(default_factory=list)
    verdict: str = Field(..., description="1-3 sentence plain-language synthesis, not a restatement of numbers")


SYSTEM_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "system_prompt.txt"
).read_text(encoding="utf-8").strip()

fireCrawler = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))


@tool
def searchBricklink(legoSet: str):
    """Look up necessary Bricklink data"""

    # do a general firecrawl web search here but send bricklink search with set number // retry only 3 times
    brickLinkSearch = fireCrawler.search(query = f"www.brickeconomy.com/search?query={legoSet}", limit = 3)
    
    # bricklink search results should have correct results as the first item, grab that url
    # as we going to pass that and do a more refined scrape next for better details
    brickLinkSearchItemUrl = brickLinkSearch.web[0].url

    # take new result and pass to scraper for set details
    brickLinkDetails = fireCrawler.scrape(brickLinkSearchItemUrl, formats=["markdown", "html"])


    return brickLinkDetails.markdown     

@tool 
def searchLego(legoSet: str):
    """Search Lego.com for any relevant data up to date unless its bui

    Args:
        query: Search terms to look for
        limit: Maximum number of results to return
    """

    # do a broad search
    results = fireCrawler.search(f"Lego.com set #{legoSet}")
    if not results:
        return f"Nothing found on Lego.com for {legoSet}"

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
        return f"No official lego.com non-instructions page found for {legoSet}"

    page = fireCrawler.scrape_url(lego_url)
    if page is None or getattr(page, "markdown", None) is None:
        return f"Found {lego_url} but could not scrape markdown"

    return page.markdown

@tool
def searchBrickowl(legoSet: str):
    """Searches Brickowl for various lego set info"""
    pass

@traceable(name="Main StudScan Agent ReAct Loop")
def run_agent(question:str):


    agent = create_agent(model="gpt-4o-mini", 
                         response_format=LegoSetReport,
                         system_prompt=SYSTEM_PROMPT,
                         tools = [searchBricklink, searchLego])
    
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    return result["structured_response"]
        
if __name__ == "__main__":
    result = run_agent("Tell me about lego 10195")
    print("\nReturned value:")
    print(result.verdict)

