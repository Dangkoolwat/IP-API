import httpx
import pytest
from starlette.requests import Request

from server import (
    RateLimitExceeded,
    RateLimiter,
    extract_client_ip,
    fetch_ip_location,
    lookup_ip_location,
    my_ip_location,
)


def make_request(headers=None, client=("198.51.100.20", 12345)) -> Request:
    raw_headers = []
    for name, value in (headers or {}).items():
        raw_headers.append((name.lower().encode(), value.encode()))

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/my-ip-location",
            "headers": raw_headers,
            "client": client,
        }
    )


@pytest.mark.asyncio
async def test_fetch_ip_location_uses_base_endpoint_and_normalizes_success_payload():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "status": "success",
                "query": "203.0.113.10",
                "country": "South Korea",
                "city": "Seoul",
                "isp": "Example ISP",
                "lat": 37.5665,
                "lon": 126.978,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_ip_location(client=client)

    assert requests[0].url == "http://ip-api.com/json"
    assert result == {
        "query": "203.0.113.10",
        "country": "South Korea",
        "city": "Seoul",
        "isp": "Example ISP",
        "latitude": 37.5665,
        "longitude": 126.978,
        "source": "ip-api.com",
    }


@pytest.mark.asyncio
async def test_fetch_ip_location_appends_specific_ip_to_endpoint():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "status": "success",
                "query": "8.8.8.8",
                "country": "United States",
                "city": "Ashburn",
                "isp": "Google LLC",
                "lat": 39.03,
                "lon": -77.5,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_ip_location("8.8.8.8", client=client)

    assert requests[0].url == "http://ip-api.com/json/8.8.8.8"
    assert result["query"] == "8.8.8.8"
    assert result["country"] == "United States"


@pytest.mark.asyncio
async def test_fetch_ip_location_rejects_invalid_ip_before_http_request():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="valid IPv4 or IPv6"):
            await fetch_ip_location("not an ip", client=client)

    assert requests == []


@pytest.mark.asyncio
async def test_fetch_ip_location_raises_clear_error_when_ip_api_reports_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "fail",
                "message": "private range",
                "query": "192.168.0.1",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError, match="private range"):
            await fetch_ip_location("192.168.0.1", client=client)


@pytest.mark.asyncio
async def test_lookup_ip_location_returns_user_friendly_payload(monkeypatch):
    async def fake_fetch_ip_location(ip_address=None):
        return {
            "query": ip_address or "203.0.113.10",
            "country": "South Korea",
            "city": "Seoul",
            "isp": "Example ISP",
            "latitude": 37.5665,
            "longitude": 126.978,
            "source": "ip-api.com",
        }

    monkeypatch.setattr("server.fetch_ip_location", fake_fetch_ip_location)

    result = await lookup_ip_location("8.8.8.8")

    assert result["message"] == "IP 8.8.8.8 위치는 South Korea, Seoul이며 ISP는 Example ISP입니다."
    assert result["source"] == "ip-api.com"


def test_extract_client_ip_prefers_first_x_forwarded_for_entry():
    request = make_request(
        headers={"x-forwarded-for": "203.0.113.10, 10.0.0.1, 10.0.0.2"},
        client=("198.51.100.20", 12345),
    )

    assert extract_client_ip(request) == "203.0.113.10"


def test_extract_client_ip_falls_back_to_request_client_host():
    request = make_request(client=("198.51.100.20", 12345))

    assert extract_client_ip(request) == "198.51.100.20"


@pytest.mark.asyncio
async def test_my_ip_location_uses_browser_request_ip(monkeypatch):
    requested_ips = []

    async def fake_fetch_ip_location(ip_address=None):
        requested_ips.append(ip_address)
        return {
            "query": ip_address,
            "country": "South Korea",
            "city": "Seoul",
            "isp": "Example ISP",
            "latitude": 37.5665,
            "longitude": 126.978,
            "source": "ip-api.com",
        }

    monkeypatch.setattr("server.fetch_ip_location", fake_fetch_ip_location)
    request = make_request(headers={"x-forwarded-for": "203.0.113.10, 10.0.0.1"})

    response = await my_ip_location(request)

    assert requested_ips == ["203.0.113.10"]
    assert response.status_code == 200
    assert response.body == (
        b'{"query":"203.0.113.10","country":"South Korea","city":"Seoul",'
        b'"isp":"Example ISP","latitude":37.5665,"longitude":126.978,'
        b'"source":"ip-api.com"}'
    )


@pytest.mark.asyncio
async def test_rate_limiter_blocks_calls_above_limit_inside_window():
    current_time = 1_000.0

    def now():
        return current_time

    limiter = RateLimiter(max_calls=2, window_seconds=60, clock=now)

    await limiter.acquire()
    await limiter.acquire()

    with pytest.raises(RateLimitExceeded, match="2 calls per 60 seconds"):
        await limiter.acquire()


@pytest.mark.asyncio
async def test_rate_limiter_allows_calls_after_window_expires():
    current_time = 1_000.0

    def now():
        return current_time

    limiter = RateLimiter(max_calls=1, window_seconds=60, clock=now)

    await limiter.acquire()
    current_time += 61
    await limiter.acquire()
