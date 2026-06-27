
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langsmith import traceable
from firecrawl import Firecrawl


MAX_ITERATIONS=10
MODEL="openai:gpt-5.4-mini"

SYSTEM_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "system_prompt.txt"
).read_text(encoding="utf-8").strip()

app = Firecrawl(api_key="FIRECRAWL_API_KEY")


@tool
def searchFireCrawl(legoSet: str):
    """Look up necessary Lego data pulled from various sites."""
    print(f"    >>> Executing searchFireCrawl(legoSet='{legoSet}')")



@traceable(name="Main StudScan Agent ReAct Loop")
def run_agent(question:str):
    tools = [searchFireCrawl]
    tools_dict = {t.name: t for t in tools}
    
    llm = init_chat_model(MODEL, model_provider="openai", temperature= 0)

    llm_with_tools = llm.bind_tools(tools)

    print("Question: {question}")
    print("=" * 60)


    messages = [
        SystemMessage(
            content = SYSTEM_PROMPT
        ),
        HumanMessage(content = question),
    ]

















if __name__ == "__main__":
    result = run_agent("What is the price of a laptop after appliying a gold discount?")

