
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


MAX_ITERATIONS=10
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "system_prompt.txt"
).read_text(encoding="utf-8").strip()

app = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))


@tool
def searchFireCrawl(legoSet: str):
    """Look up necessary Lego data pulled from various sites."""
    print(f"    >>> Executing FireCrawl search for (legoSet='{legoSet}')")

    brickLinkresults = searchBrickLink(legoSet)





def searchBrickLink(setnumber:str) -> str:
    





@traceable(name="Main StudScan Agent ReAct Loop")
def run_agent(question:str):
    tools = [searchFireCrawl]
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

        # Action
        tool_call = tools_calls[0]
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {})
        tool_call_id = tool_call.get("id")

        tool_to_use = tools_dict.get(tool_name)
        if tool_to_use is None:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        # Observation
        observation = tool_to_use.invoke(tool_args)

        messages.append(query)
        messages.append(
            ToolMessage(content=str(observation), tool_call_id=tool_call_id)
        )

    print("Error: Max iterations reached with a final answer")
    return None
        
















if __name__ == "__main__":
    result = run_agent("Tell me about lego 10195")

