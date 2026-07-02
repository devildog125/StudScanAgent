# Technical Decisions — The "Why" Behind StudScan

> These aren't arbitrary choices. Each one was made to solve a specific real problem.  
> Non-traditional background, self-taught, learned most of this by shipping and breaking things.

---

## Decision 1: ReAct Agent for the Orchestrator

**What it is:** The main agent uses a ReAct (Reason + Act) loop — it reasons about what it knows, calls a tool, observes the result, reasons again, calls another tool, and so on until it's ready to produce a final answer.

**Why not just call all three tools and combine the results yourself?**

Two reasons:

1. **Partial failure is normal.** Any of the three sites might be down, return a 404, or have a CAPTCHA. A ReAct agent handles this gracefully — it reasons "BrickEconomy came back empty, I'll note it as missing and proceed with what I have." A hardcoded sequential pipeline would either crash or need explicit branching logic for every failure case.

2. **The model can adapt.** If the system prompt instructions say "prefer LEGO.com as ground truth," the agent can actually follow that instruction rather than needing it encoded in procedural code. Reconciliation logic lives in the prompt, not in `if/elif` chains.

---

## Decision 2: Sub-Agents for Extraction (Not Direct Prompting)

**The alternative would be:** scrape the page, dump the raw markdown directly into the main agent's context, and ask it to extract everything at once.

**Why sub-agents instead?**

Raw markdown from a LEGO product page can be 10,000+ characters of navigation menus, product descriptions, cookie banners, related products, and review snippets — most of it irrelevant. Feeding all three sites' raw content into one big prompt would:

- Burn a lot of tokens
- Force the model to context-switch between three completely different page layouts
- Make debugging a nightmare (which site caused the bad parse?)

Sub-agents each get *one site's* raw markdown and *one specific schema*. Their job is narrow and their failure surface is small. If BrickEconomy extraction breaks, you fix `brickecon_prompt.txt` and `BrickEconomy` model — nothing else changes.

**This is the single responsibility principle applied to LLM calls.**

---

## Decision 3: Pydantic for All Structured Outputs

**Why Pydantic?**

LLMs hallucinate. They also occasionally output malformed JSON, use wrong field names, or return values in unexpected formats (e.g., `"$89.99"` instead of `89.99`). Pydantic validation catches these at the boundary — either the output parses correctly into the model, or you get a validation error you can handle explicitly.

The `ResalePrices` model has a custom `field_validator` (`unwrap_schema_objects`) specifically because the LLM was occasionally returning price fields as `{"type": "null"}` dict objects instead of `null`. That validator unwraps those gracefully. This is the kind of edge case you only discover by running the system on real data — and Pydantic makes it trivial to fix without touching the core logic.

**Typed outputs also make downstream code honest.** When you write `result.verdict` or `result.retail_price_usd`, you know exactly what you're getting or exactly when it's `None`. No dict key typos, no silent `KeyError`.

---

## Decision 4: Firecrawl for Web Scraping

**Why not `requests` + `BeautifulSoup`?**

The target sites (LEGO.com, BrickEconomy, BrickLink) are all JavaScript-heavy. Content is rendered client-side after the page loads. A plain HTTP request returns skeleton HTML with no actual product data in it.

Firecrawl handles:
- JavaScript rendering via headless browser
- Cookie consent and bot detection (to a reasonable degree)
- Returning clean markdown instead of raw HTML

The alternative would be maintaining a Playwright or Selenium setup, handling browser lifecycle, parsing HTML yourself, and dealing with site-specific DOM changes every time a site redesigns. Firecrawl trades a monthly API bill for not maintaining any of that.

The **two-step approach** (search first, then scrape the specific URL) is important: going directly to a URL like `brickeconomy.com/set/75415` would require knowing the exact URL format for every site. Searching by set number and filtering for the right result is more resilient to URL structure changes.

---

## Decision 5: Separate Prompt Files (Not Inline Strings)

**Why `prompts/system_prompt.txt` instead of just a Python string?**

Prompts change far more often than code. A developer improving the verdict instructions shouldn't have to open `main.py`, find the right string, and be careful not to accidentally touch surrounding logic. Separate `.txt` files mean:

- Non-technical collaborators can edit prompts without touching Python
- Git diffs for prompt changes are clean and isolated
- The files are loaded at startup so startup fails fast if a file is missing (rather than silently using an empty prompt)

The fallback for `bricklink_prompt.txt` (`if _bricklink_prompt_path.exists() else LEGO_SITE_PROMPT`) is a small but deliberate safety net — if someone deletes the file accidentally, the system degrades gracefully rather than crashing.

---

## Decision 6: `_to_tool_text()` as a Serialization Boundary

**The problem it solves:**

Tool return values in LangChain must be strings (or ToolMessages). But sub-agents return either a Pydantic model or a dict wrapping a Pydantic model. The exact shape can vary.

`_to_tool_text()` is a single function that normalizes all of that:
- If the result is a dict with a `structured_response` key, unwrap it
- If it's a Pydantic model, serialize to JSON via `model_dump_json()`
- Anything else, `str()` it

This means the tool functions themselves stay clean (`return official_lego_md`) and all serialization logic is in one place. When the serialization needs to change — and it will — there's exactly one function to update.

---

## Decision 7: `handle_tool_errors` Middleware

**Why not just `try/except` inside each tool?**

Every tool would need its own identical try/except block. The middleware approach applies one error handler to all tools at once, and it wraps exceptions in proper `ToolMessage` objects with the correct `tool_call_id` — which is what the LangChain framework requires for the agent to continue its loop rather than crash.

`ToolRetryMiddleware(max_retries=1)` adds one automatic retry for transient failures (rate limits, network blips) without any per-tool logic.

This is the same pattern as HTTP middleware in web frameworks — handle cross-cutting concerns once at the infrastructure layer, not scattered through every endpoint.

---

## Trade-offs and Known Limitations

These decisions have real costs worth being honest about:

| Decision | Cost |
|---|---|
| Firecrawl API | Real money per request. Not free to run at scale. |
| gpt-4o-mini for sub-agents | Fast and cheap but occasionally misses nuanced extraction. Swappable per sub-agent if needed. |
| Two LLM calls per data source | Latency. Three sources = six LLM calls minimum in a typical run. |
| Prompt-based reconciliation | The main agent's reconciliation logic is only as good as the system prompt. Bugs there are harder to unit test than code bugs. |
| No caching | Every run re-scrapes all three sites. Adding a simple cache keyed on set number would dramatically reduce API costs for repeated lookups. |

None of these are blocking problems — they're conscious trade-offs that made the system simpler to build and understand first. Optimization comes after the thing works.
