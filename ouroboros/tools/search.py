"""Web search tools — OpenAI Responses API and DuckDuckGo."""

from __future__ import annotations

import json
import logging
import os
import urllib
from typing import Any, Dict, List
import re

import requests

from ouroboros.tools.registry import ToolContext, ToolEntry
from ouroboros.utils import utc_now_iso

log = logging.getLogger(__name__)

DEFAULT_SEARCH_MODEL = "gpt-5.2"
DEFAULT_SEARCH_CONTEXT_SIZE = "medium"
DEFAULT_REASONING_EFFORT = "high"

_OPENAI_PRICING = {
    "gpt-5.2": (1.75, 14.0),
    "gpt-5.4-mini": (0.75, 4.5),
    "gpt-4.1": (2.0, 8.0),
    "o3": (2.0, 8.0),
    "o4-mini": (1.10, 4.40),
}

# DuckDuckGo results (no cost, free service)
_DUCKDUCKGO_MAX_RESULTS = 10


def _estimate_openai_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost from token counts. Returns 0 if model pricing unknown."""
    pricing = _OPENAI_PRICING.get(model)
    if not pricing:
        for key, val in _OPENAI_PRICING.items():
            if key in model:
                pricing = val
                break
    if not pricing:
        pricing = (2.0, 10.0)
    input_price, output_price = pricing
    return round(input_tokens * input_price / 1_000_000 + output_tokens * output_price / 1_000_000, 6)


def _resolve_openai_client_settings() -> tuple[str, str | None, str, str]:
    """Return credentials only for official OpenAI Responses web search."""
    official_key = (os.environ.get("OPENAI_API_KEY", "") or "").strip()
    legacy_base_url = (os.environ.get("OPENAI_BASE_URL", "") or "").strip()

    if official_key and not legacy_base_url:
        return official_key, None, "openai", "openai"
    return "", None, "openai", "openai"


def _web_search(
    ctx: ToolContext,
    query: str,
    model: str = "",
    search_context_size: str = "",
    reasoning_effort: str = "",
) -> str:
    """
    Web search via DuckDuckGo Instant Answer API.
    Free, no API key required, returns structured results.
    
    Uses https://api.duckduckgo.com/ which provides instant answers,
    related topics, definitions, and web results for general queries.
    """
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&pretty=1"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        
        data = resp.json()
        results = []
        
        # Extract web results from RelatedTopics
        related_topics = data.get("RelatedTopics", []) or []
        
        for topic in related_topics[:10]:
            text = topic.get("Text", "")
            first_url = topic.get("FirstURL", "")
            
            if text and first_url:
                title = first_url.split("/")[-1].replace("_", " ").replace("%20", " ")
                results.append({
                    "title": title or "(no title)",
                    "link": first_url,
                    "snippet": text[:300]
                })
        
        # Also try Results array for general web search
        if not results:
            results_array = data.get("Results", []) or []
            for item in results_array[:10]:
                text = item.get("Text", "")
                first_url = item.get("FirstURL", "")
                
                if text and first_url:
                    title = first_url.split("/")[-1].replace("_", " ").replace("%20", " ")
                    results.append({
                        "title": title or "(no title)",
                        "link": first_url,
                        "snippet": text[:300]
                    })
        
        if results:
            return json.dumps({
                "results": results,
                "query": query,
                "total": len(results),
                "source": "DuckDuckGo Instant Answer API",
                "note": "Free search via DuckDuckGo"
            }, indent=2, ensure_ascii=False)
        
        # No results from DuckDuckGo
        return json.dumps({
            "results": [],
            "query": query,
            "total": 0,
            "source": "DuckDuckGo Instant Answer API",
            "message": "No results found"
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "error": f"DuckDuckGo search failed: {repr(e)}",
            "query": query
        }, ensure_ascii=False)


def _duckduckgo_search(query: str, max_results: int = _DUCKDUCKGO_MAX_RESULTS) -> str:
    """
    Search the web via DuckDuckGo using ddgs library.
    Free, no API key required, returns structured results.
    
    Uses the ddgs (duckduckgo-search) library which properly handles
    HTTP requests and avoids CAPTCHA by emulating a real browser.
    
    This is non-exact match search - queries are NOT wrapped in quotes,
    so DuckDuckGo returns results with any word order, better for
    local/regional queries.
    
    Args:
        query: Search query string (searches without exact match quotes)
        max_results: Maximum number of results to return
    
    Returns:
        JSON with results array containing title, link, text
    """
    try:
        # Use ddgs library (renamed from duckduckgo_search)
        # It properly handles requests and avoids CAPTCHA
        from ddgs import DDGS
        
        ddgs = DDGS()
        results = ddgs.text(query, max_results=max_results)
        
        if not results:
            return json.dumps({
                "results": [],
                "query": query,
                "message": "No results found"
            }, indent=2)
        
        # Format results to match tool schema
        formatted_results = []
        for item in results:
            formatted_results.append({
                "title": item.get('title', '(no title)'),
                "link": item.get('href', '#'),
                "snippet": item.get('body', 'No description available')[:300]
            })
        
        return json.dumps({
            "results": formatted_results,
            "query": query,
            "total": len(formatted_results),
            "source": "DuckDuckGo via ddgs library (non-exact match)"
        }, indent=2, ensure_ascii=False)
        
    except ImportError:
        return json.dumps({
            "error": "DuckDuckGo library not installed. Please run: pip install ddgs",
            "query": query
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "error": f"DuckDuckGo search failed: {repr(e)}",
            "query": query
        }, ensure_ascii=False, indent=2)


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("web_search", {
            "name": "web_search",
            "description": (
                "Search the web via OpenAI Responses API. "
                f"Defaults: model={DEFAULT_SEARCH_MODEL}, search_context_size={DEFAULT_SEARCH_CONTEXT_SIZE}, "
                f"reasoning_effort={DEFAULT_REASONING_EFFORT}. "
                "Override any parameter per-call if needed (LLM-first: you decide)."
            ),
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "Search query"},
                "model": {"type": "string", "description": f"OpenAI model (default: {DEFAULT_SEARCH_MODEL})"},
                "search_context_size": {"type": "string", "enum": ["low", "medium", "high"],
                                        "description": f"How much context to fetch (default: {DEFAULT_SEARCH_CONTEXT_SIZE})"},
                "reasoning_effort": {"type": "string", "enum": ["low", "medium", "high"],
                                     "description": f"Reasoning effort (default: {DEFAULT_REASONING_EFFORT})"},
            }, "required": ["query"]},
        }, _web_search, timeout_sec=540),
        ToolEntry("duckduckgo_search", {
            "name": "duckduckgo_search",
            "description": (
                f"Search the web via DuckDuckGo HTML search. Free, no API key required. "
                f"Defaults: max_results={_DUCKDUCKGO_MAX_RESULTS}. "
                "Returns JSON with title, link, and snippet for each result. "
                "Good for quick searches without API costs."
            ),
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": f"Maximum results to return (default: {_DUCKDUCKGO_MAX_RESULTS})"},
            }, "required": ["query"]},
        }, _duckduckgo_search, timeout_sec=60),
    ]
