from __future__ import annotations

import ipaddress
from typing import Any

import httpx

from ip_api_mcp.rate_limit import InMemoryRateLimiter


IP_API_ENDPOINT = "http://ip-api.com/json"


class IpApiError(RuntimeError):
    """Raised when ip-api.com returns an error payload."""


class IpApiClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        rate_limiter: InMemoryRateLimiter | None = None,
    ) -> None:
        self._http_client = http_client or httpx.AsyncClient(timeout=10)
        self._rate_limiter = rate_limiter or InMemoryRateLimiter(
            max_calls=45,
            window_seconds=60,
        )

    async def lookup(self, ip_address: str | None = None) -> dict[str, Any]:
        normalized_ip = self._normalize_ip(ip_address)
        await self._rate_limiter.acquire()

        url = IP_API_ENDPOINT if normalized_ip is None else f"{IP_API_ENDPOINT}/{normalized_ip}"
        response = await self._http_client.get(url)
        response.raise_for_status()

        payload = response.json()
        if payload.get("status") != "success":
            message = payload.get("message") or "ip-api.com returned an unsuccessful response"
            query = payload.get("query")
            if query:
                message = f"{message} ({query})"
            raise IpApiError(message)

        return {
            "query": payload.get("query"),
            "country": payload.get("country"),
            "city": payload.get("city"),
            "isp": payload.get("isp"),
            "latitude": payload.get("lat"),
            "longitude": payload.get("lon"),
            "source": "ip-api.com",
        }

    @staticmethod
    def _normalize_ip(ip_address: str | None) -> str | None:
        if ip_address is None:
            return None

        value = ip_address.strip()
        try:
            return str(ipaddress.ip_address(value))
        except ValueError as exc:
            raise ValueError("ip_address must be a valid IPv4 or IPv6 address") from exc
