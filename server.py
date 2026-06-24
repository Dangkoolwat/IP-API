import asyncio
import ipaddress
import os
import time
from collections import deque
from collections.abc import Callable
from typing import Any

import httpx
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse


IP_API_ENDPOINT = "http://ip-api.com/json"

mcp = FastMCP(
    name="ip-api-location",
    instructions=(
        "Use this server when the user wants approximate location context for "
        "the current public IP address or a specific IPv4/IPv6 address."
    ),
)


class RateLimitExceeded(RuntimeError):
    """Raised when the local ip-api.com request limit would be exceeded."""


class RateLimiter:
    def __init__(
        self,
        max_calls: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_calls < 1:
            raise ValueError("max_calls must be at least 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be at least 1")

        self._max_calls = max_calls
        self._window_seconds = window_seconds
        self._clock = clock
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = self._clock()
            cutoff = now - self._window_seconds

            while self._calls and self._calls[0] <= cutoff:
                self._calls.popleft()

            if len(self._calls) >= self._max_calls:
                raise RateLimitExceeded(
                    f"ip-api.com limit reached: {self._max_calls} calls per "
                    f"{self._window_seconds} seconds"
                )

            self._calls.append(now)


rate_limiter = RateLimiter(max_calls=45, window_seconds=60)


def normalize_ip_address(ip_address: str | None) -> str | None:
    if ip_address is None:
        return None

    value = ip_address.strip()
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise ValueError("ip_address must be a valid IPv4 or IPv6 address") from exc


async def fetch_ip_location(
    ip_address: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    normalized_ip = normalize_ip_address(ip_address)
    await rate_limiter.acquire()

    url = IP_API_ENDPOINT if normalized_ip is None else f"{IP_API_ENDPOINT}/{normalized_ip}"
    close_client = client is None
    active_client = client or httpx.AsyncClient(timeout=10.0)

    try:
        response = await active_client.get(url)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise RuntimeError("ip-api.com request failed") from exc
    finally:
        if close_client:
            await active_client.aclose()

    if data.get("status") != "success":
        message = data.get("message") or "ip-api.com returned an unsuccessful response"
        query = data.get("query")
        if query:
            message = f"{message} ({query})"
        raise RuntimeError(message)

    return {
        "query": data.get("query"),
        "country": data.get("country"),
        "city": data.get("city"),
        "isp": data.get("isp"),
        "latitude": data.get("lat"),
        "longitude": data.get("lon"),
        "source": "ip-api.com",
    }


@mcp.tool(
    name="lookup_ip_location",
    description="현재 공인 IP 또는 특정 IP 주소의 국가, 도시, ISP, 위도, 경도를 조회합니다.",
)
async def lookup_ip_location(ip_address: str | None = None) -> dict[str, Any]:
    result = await fetch_ip_location(ip_address=ip_address)
    query = result.get("query") or ip_address or "current public IP"
    country = result.get("country") or "알 수 없음"
    city = result.get("city") or "알 수 없음"
    isp = result.get("isp") or "알 수 없음"

    return {
        **result,
        "message": f"IP {query} 위치는 {country}, {city}이며 ISP는 {isp}입니다.",
    }


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "ip-api-location"})


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(transport="http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
