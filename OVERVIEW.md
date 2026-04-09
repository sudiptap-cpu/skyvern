# What is Skyvern?

Skyvern is an open-source **AI-powered browser automation platform**. It lets you automate any browser-based workflow by describing what you want in plain English — no custom scripts, no fragile XPath selectors, no page-specific code.

## The core idea

Traditional browser automation breaks whenever a website changes its layout. Skyvern avoids this by using **Vision LLMs and computer vision** to read and understand a page the same way a human would, then decide which actions to take. Because it reasons about the visual state of a page rather than memorized selectors, it:

- Works on websites it has never seen before
- Stays functional when page layouts change
- Applies one workflow definition across many different websites

## How it works

When you give Skyvern a task, a swarm of coordinated agents handles it:

1. **Planner** – receives the goal and breaks it into a sequence of steps
2. **Agent** – takes a screenshot, maps visible elements to actions, and executes them via Playwright
3. **Validator** – checks whether the step succeeded and feeds the result back to the Planner

This loop continues until the task is complete or an error occurs.

## What you can do with it

### AI page commands (Python SDK)

| Command | What it does |
|---|---|
| `page.act(prompt)` | Perform an action described in plain English |
| `page.extract(prompt, schema)` | Pull structured data from the current page |
| `page.validate(prompt)` | Check a condition on the page; returns `bool` |
| `page.prompt(prompt, schema)` | Send an arbitrary prompt to the LLM |

### AI-augmented Playwright actions

Every standard Playwright action accepts an optional `prompt` parameter. Skyvern tries the selector first; if it fails or no selector is given, it locates the element with AI:

```python
await page.click(prompt="Click the green Submit button")
await page.fill(prompt="Email field", value="user@example.com")
```

### Higher-level agent commands

| Command | What it does |
|---|---|
| `page.agent.run_task(prompt)` | Execute a complex, multi-step task end-to-end |
| `page.agent.login(type, id)` | Authenticate using stored credentials |
| `page.agent.download_files(prompt)` | Navigate to and download files |
| `page.agent.run_workflow(workflow_id)` | Run a pre-built no-code workflow |

### No-code workflow builder

Non-technical users can build multi-step automations visually in the web dashboard at `http://localhost:8080` (or [app.skyvern.com](https://app.skyvern.com) for the cloud version).

## Common use cases

- **Invoice downloading** – Log into vendor portals, find invoices, download PDFs
- **Form filling at scale** – Submit job applications, registrations, and compliance forms
- **Data extraction** – Pull structured data from any website without an API
- **Healthcare portals** – Extract patient demographics and billing from EHR systems
- **E-commerce purchasing** – Search products, add to cart, and complete purchases
- **Government forms** – Navigate complex government websites to register or file
- **Insurance quotes** – Fill multi-step quote forms across multiple providers
- **Job applications** – Auto-fill and submit on Lever, Greenhouse, and similar platforms

## Deployment options

| Option | How to start |
|---|---|
| **Pip install (local)** | `pip install skyvern && skyvern quickstart` |
| **Docker Compose** | `pip install skyvern && skyvern quickstart` (choose Docker when prompted) |
| **Skyvern Cloud** | Sign up at [app.skyvern.com](https://app.skyvern.com) |
| **Self-hosted** | See [self-hosted docs](https://www.skyvern.com/docs/self-hosted/overview) |

## Key directories in this repo

| Path | What lives there |
|---|---|
| `skyvern/forge/` | FastAPI server and REST/WebSocket API |
| `skyvern/webeye/` | Playwright browser engine and DOM scraping |
| `skyvern/services/` | Business logic (tasks, workflows, sessions) |
| `skyvern/library/` | Public Python SDK (`Skyvern`, `SkyvernPage`) |
| `skyvern/cli/` | `skyvern` command-line tool |
| `skyvern-frontend/` | React dashboard UI |
| `alembic/` | Database migrations |
| `docs/` | Documentation site source |
