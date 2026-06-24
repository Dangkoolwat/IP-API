from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ip_api_mcp.client import IpApiClient


def create_mcp_server(lookup_client: IpApiClient | None = None) -> FastMCP:
    client = lookup_client or IpApiClient()
    mcp = FastMCP("IP API Location")

    @mcp.tool()
    async def lookup_ip_location(ip_address: str | None = None) -> dict[str, Any]:
        """Look up country, city, ISP, latitude, and longitude for an IP address.

        Omit ip_address to look up the approximate location of the requester IP.
        The upstream service is ip-api.com and this server enforces its free
        tier limit of 45 calls per minute in process.
        """
        return await client.lookup(ip_address)

    return mcp


def main() -> None:
    create_mcp_server().run()


if __name__ == "__main__":
    main()
