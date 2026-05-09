"""SearXNG MCP Server for web search."""
import json
import requests

SEARXNG_URL = "http://localhost:8888"

def search(query: str, num_results: int = 5) -> list:
    """Search the web via SearXNG."""
    try:
        response = requests.get(
            f"{SEARXNG_URL}/search",
            params={"q": query, "format": "json", "engines": "google"},
            timeout=10
        )
        results = response.json().get('results', [])[:num_results]
        return [{"title": r.get('title', ''), "url": r.get('url', ''), "content": r.get('content', '')} for r in results]
    except Exception as e:
        return [{"error": str(e)}]

if __name__ == "__main__":
    # Test
    print("SearXNG MCP Server")
    print(search("test query"))
