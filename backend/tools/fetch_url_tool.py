"""Web fetch tool — fetches URL content and converts HTML to Markdown."""

import httpx
import html2text

from langchain_core.tools import tool as lc_tool, BaseTool

MAX_OUTPUT = 5000
TIMEOUT = 15


def create_fetch_url_tool() -> BaseTool:

    @lc_tool
    async def fetch_url(url: str) -> str:
        """Fetch a URL and return its content as clean Markdown text."""
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")

            if "json" in content_type:
                text = resp.text
            else:
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = True
                h.body_width = 0
                text = h.handle(resp.text)

            if len(text) > MAX_OUTPUT:
                text = text[:MAX_OUTPUT] + "\n...[truncated]"
            return text.strip()
        except httpx.TimeoutException:
            return "Error: request timed out (15s limit)."
        except Exception as e:
            return f"Error fetching URL: {e}"

    return fetch_url
