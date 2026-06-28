# StudScan Agent

> Is that LEGO set worth buying? Let an AI figure it out.

StudScan is a LangChain ReAct agent that takes a LEGO set number, scrapes the three main data sources (LEGO.com, BrickEconomy, and BrickLink), and spits out a clean valuation report — including resale prices, retirement status, growth since release, and a plain-English verdict.

---

## What it does

1. You give it a set number (e.g. `75415`)
2. It fires up sub-agents to scrape and parse each site via [Firecrawl](https://firecrawl.dev)
3. A main agent reconciles everything into a structured `LegoSetReport`
4. You get a verdict like: *"Retired in 2023, this set has appreciated ~40% above retail — solid hold if found near retail price."*

---

## Setup

1. Clone the repo
2. Install dependencies with [uv](https://docs.astral.sh/uv/):
   ```bash
   uv sync
   ```
3. Create a `.env` file with your keys:
   ```
   FIRECRAWL_API_KEY=your_key_here
   OPENAI_API_KEY=your_key_here
   ```

---

## Usage

Pass a set number directly on the command line:

```bash
uv run main.py 75415
```

Or import and call it from your own script:

```python
from main import run_agent

result = run_agent("Tell me about lego 75415")
print(result.verdict)
```

---

## Stack

- **LangChain** — agent framework and tool orchestration
- **Firecrawl** — web scraping
- **Pydantic** — structured output validation
- **OpenAI gpt-4o-mini** — the brain

---

## Project structure

```
main.py          # agent logic, tools, entry point
models.py        # Pydantic models for structured outputs
prompts/         # system prompts for main agent and sub-agents
```
