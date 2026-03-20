import asyncio
import json
import websockets
from typing import Optional
from .display import Display


async def stream_logs(slug: str, server_url: str, token: Optional[str], display: Display, stop_event: asyncio.Event):
    uri = server_url.replace("http://", "ws://").replace("https://", "wss://")
    uri = f"{uri}/tunnels/{slug}/live"
    
    extra_headers = {}
    if token:
        extra_headers["Authorization"] = f"Bearer {token}"
    
    while not stop_event.is_set():
        try:
            async with websockets.connect(uri, additional_headers=extra_headers) as ws:
                while not stop_event.is_set():
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        event = json.loads(message)
                        await handle_event(event, display, stop_event)
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        break
        except (websockets.exceptions.WebSocketException, OSError) as e:
            if not stop_event.is_set():
                display.print_error(f"WebSocket connection lost: {e}. Reconnecting...")
                await asyncio.sleep(2)
        except Exception as e:
            if not stop_event.is_set():
                display.print_error(f"Stream error: {e}")
                await asyncio.sleep(2)


async def handle_event(event: dict, display: Display, stop_event: asyncio.Event):
    event_type = event.get("type")
    data = event.get("data", {})
    
    if event_type == "connected":
        display.print_info(f"Connected to tunnel stream")
    
    elif event_type == "request":
        display.print_request_row(data)
    
    elif event_type == "status_change":
        display.print_warning(data.get("message", "Status changed"))
    
    elif event_type == "idle_warning":
        expires_in = data.get("expires_in_seconds", 900)
        display.print_idle_warning(expires_in)
    
    elif event_type == "expired":
        reason = data.get("reason", "unknown")
        summary = data.get("summary", {})
        display.print_expired(reason, summary)
        stop_event.set()
    
    elif event_type == "visitor_count":
        count = data.get("count", 0)
        countries = data.get("countries", [])
        display.update_visitor_count(count, countries)
