import requests

from config import settings


class FetchError(Exception):
    pass


def fetch_html(url: str) -> str:
    headers = {"User-Agent": settings.user_agent}
    try:
        response = requests.get(url, headers=headers, timeout=settings.request_timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FetchError(f"Failed to fetch {url}: {exc}") from exc
    return response.text
