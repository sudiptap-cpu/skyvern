"""About command — describes what Skyvern is and does."""

import typer
from rich.markdown import Markdown
from rich.panel import Panel

from .commands._output import output
from .console import console

about_app = typer.Typer(
    invoke_without_command=True,
    help="Show a description of what Skyvern is and does.",
)

ABOUT_TEXT = """\
Skyvern automates browser-based workflows using LLMs and computer vision.

It provides:
- A Playwright-compatible SDK with AI-powered page commands (act, extract, validate, prompt)
- A no-code workflow builder for both technical and non-technical users
- Resistance to website layout changes — no brittle XPath or CSS selectors required
- Support for any website, even ones Skyvern has never seen before

Key commands added on top of Playwright:
- page.act(prompt)         — perform actions using natural language
- page.extract(prompt)     — extract structured data from the page
- page.validate(prompt)    — check page state, returns bool
- page.prompt(prompt)      — send arbitrary prompts to the LLM

Run `skyvern quickstart` to set up and start Skyvern locally.
Visit https://app.skyvern.com to use the managed cloud version.
Docs: https://www.skyvern.com/docs
"""

_ABOUT_DATA = {
    "name": "Skyvern",
    "tagline": "Automate browser-based workflows using LLMs and computer vision",
    "description": (
        "Skyvern provides a Playwright-compatible SDK that adds AI functionality on top of "
        "Playwright, as well as a no-code workflow builder to help both technical and "
        "non-technical users automate manual workflows on any website, replacing brittle or "
        "unreliable automation solutions."
    ),
    "key_features": [
        "AI-powered page commands: act, extract, validate, prompt",
        "Natural-language element location for all standard Playwright actions",
        "No-code workflow builder",
        "Works on any website without pre-written selectors",
        "Resistant to website layout changes",
        "Cloud and self-hosted deployment options",
    ],
    "docs_url": "https://www.skyvern.com/docs",
    "cloud_url": "https://app.skyvern.com",
    "quickstart": "skyvern quickstart",
}


@about_app.callback(invoke_without_command=True)
def about_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Display a description of what Skyvern is and does.

    Examples:
      skyvern about
      skyvern about --json
    """
    if ctx.invoked_subcommand is not None:
        return

    if json_output:
        output(_ABOUT_DATA, action="about", json_mode=True)
        return

    console.print(
        Panel(
            Markdown(ABOUT_TEXT),
            title="[bold cyan]About Skyvern[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
