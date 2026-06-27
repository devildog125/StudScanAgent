
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

from langchain.chat_models import init_chat_model
from langchain.tools import tool
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


MAX_ITERATIONS = 10
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

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
    """Look up official Lego set data"""
    results = fireCrawler.search(f"Lego.com set #{legoSet}")
    if not results:
        return f"Nothing found on Lego.com for {legoSet}"

    # Firecrawl search usually returns dict with `data`
    items = results.get("data", []) if isinstance(results, dict) else results

    lego_url = None
    for item in items:
        url = item.get("url") or item.get("link")
        if not url:
            continue
        if "lego.com" in url.lower():
            lego_url = url
            break

    if not lego_url:
        return f"Search found results, but none were official lego.com pages for {legoSet}"

    scraped = fireCrawler.scrape_url(lego_url)
    if scraped is None or getattr(scraped, "markdown", None) is None:
        return f"Found official page ({lego_url}) but could not scrape content"

    return scraped.markdown

@tool
def searchBrickowl(legoSet: str):
    """Searches Brickowl for various lego set info"""
    pass

@traceable(name="Main StudScan Agent ReAct Loop")
def run_agent(question:str):
    tools = [searchBricklink]
    # tools = [searchBricklink, searchLego]
    tools_dict = {t.name: t for t in tools}
    
    llm = init_chat_model(MODEL, model_provider="openai", temperature=0)

    llm_with_tools = llm.bind_tools(tools)

    print(f"Question: {question}")
    print("=" * 60)


    messages = [
        SystemMessage(
            content = SYSTEM_PROMPT
        ),
        HumanMessage(content = question),
    ]

    # Single Agent ReAct Process
    for iteration in range(1, MAX_ITERATIONS +1):
        print(f"\n--- Iteration {iteration} ---")

        # Query
        query = llm_with_tools.invoke(messages)

        # Thought
        tools_calls = query.tool_calls

        # If the model responds directly without tool usage, return that answer.
        if not tools_calls:
            final_answer = query.content
            print("Final Answer:")
            print(final_answer)
            return final_answer

        messages.append(query)

        # Observation
        for tool_call in tools_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call.get("id")

            tool_to_use = tools_dict.get(tool_name)


            if tool_to_use is None:
                raise ValueError(f"Tool '{tool_name}' not found")

            observation = tool_to_use.invoke(tool_args)


            messages.fireCrawlerend(
                ToolMessage(content=str(observation), tool_call_id=tool_call_id)
            )

    print("Error: Max iterations reached without a final answer")
    return None
        
if __name__ == "__main__":
    result = run_agent("Tell me about lego 10195")
    print("\nReturned value:")
    print(result)

