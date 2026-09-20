"""Compatibility wrapper around MCP destination research."""

from mcp_server import search_guides_data


def tavily_search(query: str, max_results: int = 5):
    return search_guides_data(query=query, max_results=max_results)
