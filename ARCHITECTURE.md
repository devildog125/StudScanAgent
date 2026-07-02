# StudScan Agent — Architecture Deep Dive

> Written from the perspective of a senior developer who learned by building, breaking, and rebuilding things.

---

## The Problem This Solves

LEGO sets are a surprisingly serious secondary market. A set retails for $80, retires, and three years later sells for $200. But knowing *which* sets are worth holding requires data spread across at least three different websites — LEGO.com (official info), BrickEconomy (historical value/retirement forecasts), and BrickLink (active resale market). Doing that research manually for every set is tedious, inconsistent, and slow.

StudScan automates the entire pipeline: give it a set number, get back a structured valuation report with a plain-English verdict.

---

## 30,000-Foot View

```
User Input (set number)
        │
        ▼
  Main ReAct Agent  ──────────────────────────────────────────┐
  (gpt-4o-mini + LegoSetReport schema)                        │
        │                                                       │
        │  decides which tools to call, in what order          │
        ▼                                                       │
  ┌─────────────┐  ┌─────────────────┐  ┌────────────────┐    │
  │ search_lego │  │search_brickeco- │  │search_bricklink│    │
  │    tool     │  │    nomy tool    │  │     tool       │    │
  └──────┬──────┘  └────────┬────────┘  └───────┬────────┘    │
         │                  │                    │             │
         └──────────────────┴────────────────────┘            │
                            │                                  │
                            ▼                                  │
                   create_summary_md()                         │
                   (shared scrape + parse pipeline)            │
                            │                                  │
                    ┌───────┴───────┐                          │
                    │   Firecrawl   │  ← fetches real web page │
                    └───────┬───────┘                          │
                            │ raw markdown                     │
                            ▼                                  │
                     Sub-Agent                                 │
                  (gpt-4o-mini + site-specific schema)         │
                            │ structured Pydantic model        │
                            ▼                                  │
                    JSON string returned to                     │
                    Main ReAct Agent ──────────────────────────┘
                            │
                            ▼
                   LegoSetReport  (final structured output)
                            │
                            ▼
                      result.verdict  (printed to CLI)
```

---

## Two Layers of Agents — Why Both?

This is the core architectural choice. There are **two separate agent calls** per data source, not one. Here's why that matters.

### Layer 1 — The Sub-Agent (per-site extractor)

Each call to `create_summary_md()` spins up a small agent whose only job is to read raw scraped markdown from *one specific website* and convert it into a tightly defined Pydantic model.

Each site gets its own:
- **Schema** (`LegoSite`, `BrickEconomy`, `BrickLinkInventory`) — shaped around what that site actually provides
- **System prompt** — tuned instructions for what to look for on that page

This matters because LEGO.com, BrickEconomy, and BrickLink are completely different pages. LEGO.com shows retail price and ratings. BrickEconomy shows retirement forecasts and investment grades. BrickLink shows active inventory counts and resale ask prices. Trying to extract all of that with a single generic prompt would produce garbage.

**The sub-agent isolates the "how do I read this page" problem from the "how do I analyze this data" problem.**

### Layer 2 — The Main ReAct Agent (orchestrator + analyst)

The main agent has a different job entirely: it decides *when* to call each tool, *reconciles* the data across sources (handling disagreements, missing fields, and currency issues), and produces the final `LegoSetReport` with a plain-English `verdict`.

It uses a **ReAct loop** (Reasoning + Acting) — the model reasons about what it knows, decides what tool to call next, observes the result, and repeats until it has enough data to produce a final answer.

---

## Data Flow — Step by Step

### Step 1: Tool Dispatch

The main agent receives: `"Tell me about lego 75415"`.

It decides which tools to call. Because it has three tools available (`search_lego`, `search_brickeconomy`, `search_bricklink`), it will typically call all three — though if one fails or a site is unavailable, it can still produce a partial report.

### Step 2: Web Discovery (Firecrawl Search)

Each tool calls `create_summary_md(site, set_number)`. The first thing that function does is run a **Firecrawl search** for the set on that site (e.g., `"lego.com set #75415"`).

This returns a list of candidate URLs. The code then loops through looking for a URL that actually contains the site domain — filtering out ads, redirects, and off-topic results.

```
search results → filter by domain → site_url
```

### Step 3: Page Scrape

Once the correct URL is found, Firecrawl scrapes the full page and returns it as **markdown**. Firecrawl handles JavaScript-rendered pages, anti-bot measures, and cookie consent banners — the complex rendering work that would otherwise require a full headless browser setup.

The output is raw markdown — headers, prices, product names, tables, everything on the page.

### Step 4: Sub-Agent Extraction

The raw markdown is passed to a sub-agent. The sub-agent has:
- A system prompt telling it exactly what fields to find on this specific site
- A `response_format` (Pydantic schema) that forces structured JSON output

The result is a clean Pydantic model instance — no ambiguity, no free text, machine-readable.

### Step 5: Serialization Back to the Main Agent

Pydantic models are serialized to JSON strings via `model_dump_json()` and returned to the main agent as tool output (a `ToolMessage`). The main agent reads these JSON strings and uses them to fill in the final `LegoSetReport`.

### Step 6: Final Report

The main agent reconciles everything — preferring LEGO.com as ground truth for retail price and piece count, noting discrepancies, flagging missing or broken sources — and writes a `verdict` that synthesizes the data into a human-readable investment take.

---

## Error Handling Strategy

Every failure point has a fallback that returns a descriptive string rather than raising an exception:

| Failure Point | What Happens |
|---|---|
| Firecrawl search fails | Returns string: `"Firecrawl search failed for {site}..."` |
| Site URL not found in results | Returns string: `"Couldn't find given site..."` |
| Firecrawl scrape fails | Returns string: `"Firecrawl scrape failed for {url}..."` |
| Sub-agent extraction fails | Returns string: `"Extraction agent failed for {url}..."` |
| Tool call throws unexpectedly | `handle_tool_errors` middleware wraps it into a `ToolMessage` |

This means the main agent *always* gets a response from every tool — either real data or a human-readable explanation of what went wrong. It can then decide how to handle missing sources in the final report, which is exactly what the system prompt instructs it to do.

---

## Schema Design

### Why Separate Models per Site?

`LegoSite`, `BrickEconomy`, and `BrickLinkInventory` each capture what their source actually provides — nothing more. Trying to use one unified model for all three would mean either losing data (by forcing sites into a common denominator) or producing sparse, confusing output (by having dozens of optional fields most of which are null for any given site).

### Why `LegoSetReport` as the Final Layer?

`LegoSetReport` is the *reconciled* view. It deliberately has different fields than any single source provides — `resale_new` and `resale_used` are `ResalePrices` objects that can hold values from multiple platforms side-by-side. This allows the main agent to represent the *market* rather than any one data point.

The `verdict` field is the key output — it's a required string (`...` in the Field definition means non-optional) that forces the model to synthesize rather than just dump numbers.

---

## The Workflow Diagram

The repository includes `Mult-Agent_LangGraph_WorkFlow.png` — a visual representation of the agent-tool-agent call chain described above. When in doubt about how control flows between components, that diagram is the reference.

---

## What This Pattern Is Called

This is a **multi-agent orchestration with structured extraction** pattern:

- **Orchestrator agent** — manages workflow, handles partial failures, produces synthesized output
- **Extractor agents** — narrow-purpose, deterministic-output sub-agents for each data source
- **Typed interfaces** — Pydantic enforces the contract between agents so errors surface as validation failures, not silent bad data

It's a pattern that scales well: adding a new data source (say, BrickOwl) means adding one new Pydantic model, one prompt file, one tool function, and one entry in the site routing dict in `create_summary_md`.
