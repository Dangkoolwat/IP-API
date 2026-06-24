import pytest

from ip_api_mcp.server import create_mcp_server


class FakeLookupClient:
    def __init__(self):
        self.requests = []

    async def lookup(self, ip_address=None):
        self.requests.append(ip_address)
        return {
            "query": ip_address or "203.0.113.10",
            "country": "South Korea",
            "city": "Seoul",
            "isp": "Example ISP",
            "latitude": 37.5665,
            "longitude": 126.978,
            "source": "ip-api.com",
        }


@pytest.mark.asyncio
async def test_mcp_server_exposes_lookup_tool():
    lookup_client = FakeLookupClient()
    server = create_mcp_server(lookup_client=lookup_client)

    _, structured_result = await server.call_tool(
        "lookup_ip_location",
        {"ip_address": "8.8.8.8"},
    )

    assert lookup_client.requests == ["8.8.8.8"]
    assert structured_result["country"] == "South Korea"
    assert structured_result["source"] == "ip-api.com"
