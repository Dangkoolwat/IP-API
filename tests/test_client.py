import time

import pytest

from ip_api_mcp.client import IpApiClient, IpApiError
from ip_api_mcp.rate_limit import InMemoryRateLimiter, RateLimitExceeded


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeAsyncHttpClient:
    def __init__(self, response):
        self.response = response
        self.requests = []

    async def get(self, url):
        self.requests.append(url)
        return self.response


@pytest.mark.asyncio
async def test_lookup_current_ip_uses_base_endpoint_and_normalizes_success_payload():
    http_client = FakeAsyncHttpClient(
        FakeResponse(
            {
                "status": "success",
                "query": "203.0.113.10",
                "country": "South Korea",
                "city": "Seoul",
                "isp": "Example ISP",
                "lat": 37.5665,
                "lon": 126.978,
            }
        )
    )
    client = IpApiClient(http_client=http_client)

    result = await client.lookup()

    assert http_client.requests == ["http://ip-api.com/json"]
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
async def test_lookup_specific_ip_appends_ip_to_endpoint():
    http_client = FakeAsyncHttpClient(
        FakeResponse(
            {
                "status": "success",
                "query": "8.8.8.8",
                "country": "United States",
                "city": "Mountain View",
                "isp": "Google LLC",
                "lat": 37.4056,
                "lon": -122.0775,
            }
        )
    )
    client = IpApiClient(http_client=http_client)

    result = await client.lookup("8.8.8.8")

    assert http_client.requests == ["http://ip-api.com/json/8.8.8.8"]
    assert result["query"] == "8.8.8.8"
    assert result["country"] == "United States"


@pytest.mark.asyncio
async def test_lookup_rejects_invalid_ip_before_http_request():
    http_client = FakeAsyncHttpClient(FakeResponse({}))
    client = IpApiClient(http_client=http_client)

    with pytest.raises(ValueError, match="valid IPv4 or IPv6"):
        await client.lookup("not an ip")

    assert http_client.requests == []


@pytest.mark.asyncio
async def test_lookup_raises_clear_error_when_ip_api_reports_failure():
    http_client = FakeAsyncHttpClient(
        FakeResponse(
            {
                "status": "fail",
                "message": "private range",
                "query": "192.168.0.1",
            }
        )
    )
    client = IpApiClient(http_client=http_client)

    with pytest.raises(IpApiError, match="private range"):
        await client.lookup("192.168.0.1")


@pytest.mark.asyncio
async def test_rate_limiter_blocks_calls_above_limit_inside_window():
    current_time = 1_000.0

    def now():
        return current_time

    limiter = InMemoryRateLimiter(max_calls=2, window_seconds=60, clock=now)

    await limiter.acquire()
    await limiter.acquire()

    with pytest.raises(RateLimitExceeded, match="2 calls per 60 seconds"):
        await limiter.acquire()


@pytest.mark.asyncio
async def test_rate_limiter_allows_calls_after_window_expires():
    current_time = 1_000.0

    def now():
        return current_time

    limiter = InMemoryRateLimiter(max_calls=1, window_seconds=60, clock=now)

    await limiter.acquire()
    current_time += 61
    await limiter.acquire()

    assert time.time() > 0
