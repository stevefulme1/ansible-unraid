"""Stream real-time events from an Unraid server via GraphQL subscriptions.

Connects to the Unraid GraphQL WebSocket endpoint and emits events
for array state changes, Docker container stats, CPU/memory metrics,
notification alerts, and UPS status updates.

Arguments:
    api_url: Unraid server URL (e.g. 'https://tower.local')
    api_key: API key for authentication
    validate_certs: Whether to validate SSL certificates (default: true)
    subscriptions: List of subscriptions to enable (default: all)
        Choices: array, docker, cpu, memory, notifications, ups
    interval: Reconnect interval in seconds on disconnect (default: 5)
"""

import asyncio
import json
import logging
import ssl
from typing import Any

IMPORT_ERRORS = []
try:
    import aiohttp
except ImportError as ie:
    IMPORT_ERRORS.append(ie)

logger = logging.getLogger(__name__)

SUBSCRIPTION_QUERIES = {
    "array": "subscription { arraySubscription { state } }",
    "docker": "subscription { dockerContainerStats { id names cpuPercent memoryUsage } }",
    "cpu": "subscription { systemMetricsCpu { cores { usage } } }",
    "memory": "subscription { systemMetricsMemory { used total } }",
    "notifications": "subscription { notificationAdded { id importance subject description } }",
    "ups": "subscription { upsUpdates { status batteryCharge runtime } }",
}


async def main(queue: asyncio.Queue, args: dict[str, Any]) -> None:
    """Connect to Unraid GraphQL subscriptions and emit events."""
    for exc in IMPORT_ERRORS:
        raise ImportError(
            "The 'aiohttp' package is required for the Unraid EDA event source. "
            "Install it with: pip install aiohttp"
        ) from exc

    api_url = args["api_url"].rstrip("/")
    ws_url = api_url.replace("https://", "wss://").replace("http://", "ws://")
    if not ws_url.endswith("/graphql"):
        ws_url += "/graphql"
    api_key = args["api_key"]
    validate_certs = args.get("validate_certs", True)
    subscriptions = args.get("subscriptions", list(SUBSCRIPTION_QUERIES.keys()))
    interval = int(args.get("interval", 5))

    ssl_context = None
    if not validate_certs:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    ws_url,
                    headers={"x-api-key": api_key},
                    ssl=ssl_context,
                    protocols=["graphql-transport-ws"],
                ) as ws:
                    await ws.send_json({"type": "connection_init"})
                    logger.info("Connected to Unraid WebSocket at %s", ws_url)

                    for idx, sub_name in enumerate(subscriptions):
                        query = SUBSCRIPTION_QUERIES.get(sub_name)
                        if not query:
                            logger.warning("Unknown subscription: %s", sub_name)
                            continue
                        await ws.send_json({
                            "id": str(idx),
                            "type": "subscribe",
                            "payload": {"query": query},
                        })

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if data.get("type") == "next":
                                payload = data.get("payload", {}).get("data", {})
                                event = {
                                    "unraid": {
                                        "subscription_id": data.get("id"),
                                        **payload,
                                    }
                                }
                                await queue.put(event)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break

        except Exception:
            logger.exception("Unraid WebSocket connection error")

        logger.info("Reconnecting in %d seconds", interval)
        await asyncio.sleep(interval)
