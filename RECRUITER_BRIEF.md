# StudScan Agent — What This Project Says About Its Developer

> For HR recruiters and hiring managers evaluating this candidate.

---

## The Elevator Pitch

StudScan is an AI-powered research assistant that analyzes LEGO sets as investment assets. A user inputs a set number. The system autonomously scrapes three different websites, extracts and reconciles structured data using multiple AI agents, and returns a plain-English valuation verdict in seconds.

That's the product. Here's what it demonstrates about the person who built it.

---

## Skills Demonstrated — In Plain Language

### 1. AI / LLM Engineering (the skill every company is hiring for right now)

This project was built using **multi-agent orchestration** — a pattern at the frontier of how production AI systems are being designed in 2024–2025. The developer didn't just prompt ChatGPT and call it a day. They:

- Designed a **two-layer agent architecture** where specialized sub-agents handle discrete tasks and a master agent coordinates them
- Wrote targeted **system prompts** tuned to each data source's specific page structure
- Handled **LLM output validation** using Pydantic schemas with custom validators — because real LLMs produce messy output and production systems need guardrails

This is the same pattern used by AI teams at companies like Salesforce, HubSpot, and enterprise SaaS companies building internal AI tooling.

---

### 2. API Integration and Third-Party Services

The project integrates three external APIs: **OpenAI**, **Firecrawl** (web scraping), and **LangSmith** (observability/tracing). The developer understood:

- When to use a managed service vs. build it yourself (chose Firecrawl over maintaining a custom browser automation stack)
- How to abstract API calls cleanly so swapping one service for another doesn't require rewriting core logic
- How to protect credentials using environment variables and `.env` files

---

### 3. Systems Thinking

The architecture isn't one big script. It's a **pipeline with clear separation of concerns**:

- Web discovery → web scraping → per-site extraction → reconciliation → output
- Each stage has its own error handling and degrades gracefully if a piece is unavailable
- Adding a new data source requires touching exactly four things — not a rewrite

This is how experienced engineers think. They design for change before change happens.

---

### 4. Data Modeling and Validation

The developer defined **five distinct Pydantic models** — not because the framework required it, but because they understood that typed, validated data is the foundation of reliable systems. When the LLM returned a price as `{"type": "null"}` instead of `null`, they diagnosed it, added a custom validator, and fixed it without breaking anything else.

That's debugging instinct. That's what separates people who build things that work from people who build things that work *in demos*.

---

### 5. Python Proficiency

The codebase demonstrates command of:
- **Pydantic v2** — modern data validation with custom validators
- **LangChain** — tools, agents, middleware, structured output
- **Type annotations** throughout — `Optional[float]`, `list[str]`, `Callable`
- **Pathlib** for clean file path handling
- **Decorator patterns** (`@tool`, `@traceable`, `@wrap_tool_call`)
- **Dependency management** with `uv` and `pyproject.toml`

This isn't tutorial code. This is structured, maintainable Python.

---

## What "Non-Traditional Background" Actually Means Here

This developer did not come through a four-year CS program. They came through **curiosity, self-direction, and shipping real things**.

What that means in practice:

- **They learned by solving real problems**, not by passing exams. Every pattern in this codebase exists because a naïve approach failed and they figured out why.
- **They communicate clearly.** The prompt files, variable names, and documentation in this project are written for humans — not to impress compilers.
- **They make pragmatic decisions.** They chose `gpt-4o-mini` over a more expensive model because speed and cost matter. They added one retry in middleware rather than building a complex retry framework. They solved the actual problem.
- **They are not intimidated by new technology.** Multi-agent AI systems are new to virtually everyone. This developer didn't wait for a course or a certification — they built with it.

Non-traditional backgrounds produce engineers who are **resourceful, adaptive, and unbothered by ambiguity** — qualities that can't be taught in a classroom and don't show up on a GPA.

---

## The Business Lens

This project shows the developer can:

| Business Need | Evidence in This Project |
|---|---|
| Build internal AI tooling | Multi-agent architecture, prompt engineering, structured output |
| Integrate third-party APIs quickly | OpenAI + Firecrawl + LangSmith in one cohesive system |
| Deliver reliable automated workflows | Error handling, validation, graceful degradation |
| Work with unstructured external data | Live web scraping → clean structured reports |
| Think about scalability | Architecture designed to add new data sources with minimal changes |
| Ship independently | This is a solo project — fully designed, built, and documented by one person |

---

## Roles This Prepares Them For

- **AI Engineer / LLM Engineer** — this is literally the job description
- **Backend Engineer** at a company building AI-augmented products
- **ML Platform / AI Tooling** roles at growth-stage startups
- **Automation Engineer** roles where integrating APIs and building reliable pipelines is the core work
- **Full-Stack Engineer** who owns an AI feature end-to-end

---

## The Bottom Line

Most candidates in 2025 will say they "work with AI." This developer **built a production-pattern AI system from scratch** — multi-agent, validated outputs, real external API integrations, clean error handling, documented architecture.

No degree required to recognize what that demonstrates.

---

*For technical deep-dives, see [`ARCHITECTURE.md`](./ARCHITECTURE.md) and [`TECHNICAL_DECISIONS.md`](./TECHNICAL_DECISIONS.md).*
