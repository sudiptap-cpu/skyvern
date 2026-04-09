# Skyvern Architecture and Code Explanation

This document explains the structure and design of the Skyvern codebase. It is intended to help contributors and developers quickly understand how the different components fit together.

---

## Table of Contents

1. [Overview](#overview)
2. [Project Layout](#project-layout)
3. [Core Components](#core-components)
   - [Agent System (`skyvern/forge/agent.py`)](#agent-system)
   - [Browser Automation (`skyvern/webeye/`)](#browser-automation)
   - [Workflow Engine (`skyvern/forge/sdk/workflow/`)](#workflow-engine)
   - [LLM Integration (`skyvern/forge/sdk/api/llm/`)](#llm-integration)
   - [API Layer (`skyvern/forge/api_app.py`)](#api-layer)
   - [Services (`skyvern/services/`)](#services)
4. [Data Flow](#data-flow)
5. [Configuration](#configuration)
6. [Key Design Patterns](#key-design-patterns)

---

## Overview

Skyvern is an AI-powered browser automation platform. Instead of relying on brittle CSS selectors or XPath expressions, Skyvern uses Large Language Models (LLMs) combined with computer vision to understand and interact with web pages dynamically. This makes automations resilient to UI changes and capable of operating on websites the system has never visited before.

Key capabilities:
- **Task execution**: Given a URL and a natural-language goal, Skyvern navigates the web and completes the task.
- **Workflow builder**: A no-code editor lets users chain together blocks (navigation, extraction, loops, etc.) into reusable workflows.
- **Playwright SDK extension**: A drop-in AI enhancement layer on top of standard Playwright scripts.
- **REST API and WebSocket streaming**: All functionality is exposed via a FastAPI server so it can be integrated into any application.

---

## Project Layout

```
skyvern/                  Main Python package
  cli/                    Command-line interface (skyvern run, skyvern quickstart, …)
  config.py               Pydantic-settings configuration (reads .env files)
  constants.py            Global constants and enumerations
  exceptions.py           Custom exception hierarchy
  forge/                  Core automation logic and FastAPI server
    agent.py              ForgeAgent — the central orchestrator for tasks and workflow runs
    agent_functions.py    AgentFunction — LLM-driven action planning helpers
    api_app.py            FastAPI app factory, middleware, and startup lifecycle
    forge_app.py          Dependency-injection container (database, LLM clients, browser, …)
    prompts/              Jinja2 prompt templates for every LLM call
    sdk/
      api/llm/            LLM provider abstraction (OpenAI, Anthropic, Gemini, Bedrock, …)
      artifact/           Screenshot / recording / download storage (local, S3, Azure)
      db/                 SQLAlchemy async ORM, Alembic migrations
      routes/             FastAPI route handlers (tasks, workflows, browser sessions, …)
      schemas/            Pydantic request/response models
      services/           Business-logic services used by route handlers
      workflow/           Workflow runtime: block execution, parameters, loop control
  services/               Higher-level services (run_service, task_v1/v2, webhooks, …)
  webeye/                 Browser automation layer
    browser_factory.py    Creates and configures Playwright browser instances
    browser_manager.py    Manages browser lifecycle per task / workflow run
    browser_state.py      Per-session page state (current page, history, …)
    scraper/              DOM scraping + accessibility-tree extraction
    actions/              Action types (click, type, select, …) and execution logic
    utils/                DOM helpers (SkyvernElement, SkyvernFrame)

skyvern-frontend/         React + TypeScript UI
alembic/                  Database migrations
tests/                    Pytest unit tests
```

---

## Core Components

### Agent System

**`skyvern/forge/agent.py`** — `ForgeAgent`

`ForgeAgent` is the central orchestrator. It ties together the browser, the LLM, and the database to execute a single task or drive an entire workflow run step by step.

Responsibilities:
1. **Task lifecycle** — creates `Task` and `Step` records in the database, transitions their statuses (created → running → completed / failed / cancelled).
2. **Step loop** — for each step it (a) takes a screenshot, (b) scrapes the DOM / accessibility tree, (c) sends both to the LLM for action planning, (d) executes the returned actions in the browser, and (e) checks completion/termination criteria.
3. **Workflow block dispatch** — for workflow runs it instantiates and executes typed `Block` objects (see [Workflow Engine](#workflow-engine)).
4. **Async operation pool** — long-running side operations (webhook delivery, artifact upload) are offloaded via `AsyncOperationPool` so they do not block the main step loop.

**`skyvern/forge/agent_functions.py`** — `AgentFunction`

`AgentFunction` holds the per-step LLM logic that `ForgeAgent` delegates to:

- `extract_action` — sends the scraped page + prompt to the LLM and parses the returned action list.
- `get_extracted_information_for_task` — runs a data-extraction prompt to pull structured data out of a page.
- `get_task_final_response` — asks the LLM whether the task goal has been met (complete / not-complete / terminate).

---

### Browser Automation

**`skyvern/webeye/`**

This layer wraps Playwright and provides Skyvern-specific utilities.

| File | Purpose |
|---|---|
| `browser_factory.py` | Launches Chromium (or another browser) with the desired proxy, locale, and stealth settings. |
| `browser_manager.py` | Protocol that maps task / workflow-run IDs to `BrowserState` instances. The concrete implementation (`real_browser_manager.py`) persists state across steps. |
| `browser_state.py` | Holds a reference to the live Playwright `Page`, tracks download state, and provides helpers like `get_working_page()`. |
| `scraper/` | Walks the DOM and accessibility tree to produce a serialisable element tree. The element tree is what the LLM "sees" instead of raw HTML. |
| `actions/` | Defines every low-level action type (`ClickAction`, `TypeAction`, `SelectOptionAction`, `ScrollAction`, …) and the executor that calls the corresponding Playwright APIs. |
| `utils/dom.py` | `SkyvernElement` — a rich wrapper around a Playwright `ElementHandle` with convenience methods for clicking, typing, and attribute inspection. |

---

### Workflow Engine

**`skyvern/forge/sdk/workflow/`**

Workflows are directed graphs of *Blocks*. Each block is a self-contained unit of automation.

**Block types** (defined in `models/block.py`):

| Block | What it does |
|---|---|
| `TaskBlock` / `NavigationBlock` | Navigates to a URL and completes a natural-language goal. |
| `ExtractionBlock` | Extracts structured data from the current page. |
| `ValidationBlock` | Checks a condition and fails / continues based on the result. |
| `ForLoopBlock` | Iterates over a list parameter and executes child blocks for each element. |
| `CodeBlock` | Runs an arbitrary Python snippet inside a sandboxed executor. |
| `TextPromptBlock` | Sends a free-form prompt to the LLM and captures the response as a parameter. |
| `DownloadToS3Block` / `UploadToS3Block` | Move files between the browser download folder and S3. |
| `SendEmailBlock` | Sends an email via SMTP or an email-API service. |
| `HttpRequestBlock` | Makes an outbound HTTP request. |
| `BranchBlock` | Conditional branching using Jinja2 expressions or LLM evaluation. |
| `HumanInteractionBlock` | Pauses the run and waits for a human to act in the browser. |
| `WaitBlock` | Waits a fixed number of seconds before proceeding. |

**Parameters** (`models/parameter.py`):

Parameters are typed values that flow between blocks. They can be:
- *Workflow parameters* — provided by the caller when starting the run.
- *Output parameters* — produced by a block and consumed downstream.
- *Context parameters* — derived from the current workflow run context (URL, organisation, …).
- *AWS/Bitwarden secrets* — fetched from external vaults at runtime.

**`WorkflowRunContext`** keeps all parameter values for a single run and resolves Jinja2 template expressions on demand.

---

### LLM Integration

**`skyvern/forge/sdk/api/llm/`**

Skyvern is LLM-provider-agnostic. All providers are accessed through a unified interface:

- **`LLMAPIHandler`** (`api_handler.py`) — the common callable: takes messages and returns a parsed response.
- **`LLMAPIHandlerFactory`** (`api_handler_factory.py`) — builds an `LLMAPIHandler` for any registered provider using LiteLLM as the routing layer.
- **`LLMConfigRegistry`** (`config_registry.py`) — a global registry of named LLM configurations (`LLM_KEY`, `SECONDARY_LLM_KEY`, etc.).

Supported providers: OpenAI, Anthropic, Azure OpenAI, AWS Bedrock, Google Gemini, Ollama, and any LiteLLM-compatible endpoint.

The primary LLM is used for full reasoning steps; the secondary LLM handles lighter tasks (short prompts, verification) to reduce latency and cost.

---

### API Layer

**`skyvern/forge/api_app.py`** builds the FastAPI application:

1. **Lifespan** — on startup it initialises the database engine, runs pending Alembic migrations (SQLite only), creates a default organisation and API key, and starts the cleanup scheduler. On shutdown it releases all resources.
2. **Middleware** — CORS, raw-request logging, OpenTelemetry tracing, and starlette-context propagation.
3. **Routers** — route modules are registered under `/api/v1/`:
   - `agent_protocol` — task CRUD and execution endpoints.
   - `workflows` — workflow CRUD and run endpoints.
   - `browser_sessions` — persistent browser session management.
   - `credentials` — credential vault management.
   - `streaming` — Server-Sent Events for real-time step updates.
   - `scripts`, `code_samples`, `prompts` — developer utilities.

---

### Services

**`skyvern/services/`** contains stateless business-logic services that the route handlers call:

| Service | Responsibility |
|---|---|
| `run_service.py` | Top-level entry point: starts a task or workflow run, delegates to `ForgeAgent`. |
| `task_v1_service.py` / `task_v2_service.py` | Task creation, status transitions, result saving. |
| `workflow_service.py` | Workflow CRUD, version management, run creation. |
| `action_service.py` | Persists executed actions and their outcomes. |
| `webhook_service.py` | Delivers webhook callbacks to caller-provided URLs with retry logic. |
| `browser_session_service.py` | Manages long-lived browser sessions shared across runs. |
| `cleanup_service.py` | Background scheduler that removes stale runs, artifacts, and browser sessions. |

---

## Data Flow

```
User / API Client
       │
       ▼
  FastAPI (api_app.py)
       │  POST /api/v1/tasks  or  POST /api/v1/workflows/{id}/run
       ▼
  run_service.py  ──►  creates Task / WorkflowRun in DB
       │
       ▼
  ForgeAgent.execute_task()  or  ForgeAgent.execute_workflow()
       │
       │  for each Step:
       │    1. BrowserManager  ──►  BrowserState (Playwright Page)
       │    2. Scraper         ──►  element tree (JSON + accessibility tree)
       │    3. Screenshot      ──►  base64 image
       │    4. LLMAPIHandler   ──►  action list (JSON)
       │    5. ActionExecutor  ──►  Playwright API calls
       │    6. Database        ──►  persist Step result
       │
       ▼
  Webhook / SSE stream  ──►  notify caller
```

For workflow runs, `ForgeAgent` iterates over the ordered list of blocks returned by `WorkflowDefinitionConverter`, instantiates each block, calls `block.execute(workflow_run_context)`, and threads the output parameters back into the context for subsequent blocks.

---

## Configuration

All settings live in `skyvern/config.py` and are read from environment variables or `.env` files via **pydantic-settings**.

Important settings:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_STRING` | SQLite at `~/.skyvern/data.db` | SQLAlchemy connection URL. Set to a PostgreSQL URL for production. |
| `LLM_KEY` | — | Named LLM configuration to use for main reasoning (e.g. `OPENAI_GPT4O`). |
| `SECONDARY_LLM_KEY` | — | Named LLM configuration for lightweight operations. |
| `BROWSER_TYPE` | `chromium` | Playwright browser type. |
| `ENABLE_OPENAI` / `ENABLE_ANTHROPIC` / … | `false` | Feature flags to enable individual LLM providers. |
| `SKYVERN_API_KEY` | auto-generated | API key required for all REST calls. |
| `ARTIFACT_STORAGE_PATH` | `~/.skyvern/artifacts` | Local directory for screenshots, videos, and downloaded files. |

---

## Key Design Patterns

1. **Dependency injection via `forge_app.py`** — `ForgeApp` is a plain Python object that acts as a service locator. It is populated during application startup and referenced throughout as `from skyvern.forge import app`. This avoids circular imports and makes unit testing straightforward.

2. **Async-first** — all I/O (database, browser, LLM, HTTP) uses `asyncio` and `async/await`. The FastAPI event loop runs everything on a single thread per worker, with `asyncio.gather` used for parallel sub-operations.

3. **Structured logging** — `structlog` is used everywhere with key-value context propagated via `structlog.contextvars` so that every log line for a given task/step includes the relevant IDs automatically.

4. **Protocol-based abstractions** — `BrowserManager`, `BaseStorage`, `BaseCache`, `RateLimiter`, etc. are defined as Python `Protocol` classes. Concrete implementations are swapped in at startup based on configuration, enabling local (file/SQLite) and cloud (S3/PostgreSQL) modes without changing any business logic.

5. **Block-based workflow composition** — workflows are modelled as a list of polymorphic `Block` objects. Each block implements `execute(context) -> BlockResult`. New block types can be added without touching the orchestrator.

6. **Prompt templating** — all LLM prompts are Jinja2 templates stored in `skyvern/forge/prompts/`. The `PromptEngine` class loads and renders them, making it easy to iterate on prompts without touching Python code.
