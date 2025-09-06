import asyncio
import httpx
from typing import Tuple, List, Optional
from .flows import LRUFlows, Flow
from .bus import EventBus, FLOW_CREATED, FLOW_UPDATED, FLOW_FINISHED, FLOW_PAUSED, LOG_MESSAGE, SET_INTERCEPT, FORWARD_FLOW, DROP_FLOW, REPEAT_FLOW
from .rules import Ruleset, apply_rules

class ProxyServer:
    def __init__(self, host="127.0.0.1", port=8080, bus: Optional[EventBus]=None):
        self.host = host
        self.port = port
        self.flows = LRUFlows(2000)
        self.bus = bus or EventBus()
        self.intercept = False
        self.ruleset = Ruleset()
        self._pending_forwards = {}

    async def serve(self):
        asyncio.create_task(self._gui_cmd_loop())
        server = await asyncio.start_server(self._handle_client, self.host, self.port)
        await self.bus.publish_core(LOG_MESSAGE, {"msg": f"Proxy listening on {self.host}:{self.port}"})
        async with server:
            await server.serve_forever()

    async def _gui_cmd_loop(self):
        while True:
            ev = await self.bus.consume_gui_cmd()
            if ev.type == SET_INTERCEPT:
                self.intercept = bool(ev.data.get("on", False))
                await self.bus.publish_core(LOG_MESSAGE, {"msg": f"Intercept set to {self.intercept}"})
            elif ev.type in (FORWARD_FLOW, DROP_FLOW, REPEAT_FLOW):
                fid = int(ev.data["flow_id"])
                fut = self._pending_forwards.get(fid)
                if fut and not fut.done():
                    fut.set_result(ev.type)
            elif ev.type == "ApplyRules":
                self.ruleset = Ruleset(**ev.data["ruleset"])

    async def _read_line(self, reader: asyncio.StreamReader) -> bytes:
        return await reader.readline()

    async def _read_headers(self, reader: asyncio.StreamReader) -> List[Tuple[str, str]]:
        headers = []
        while True:
            line = await reader.readline()
            if not line or line in (b"\r\n", b"\n"):
                break
            k, v = line.decode("iso-8859-1").split(":", 1)
            headers.append((k.strip(), v.strip()))
        return headers

    def _split_host(self, host: str) -> Tuple[str, int]:
        if ":" in host:
            h, p = host.rsplit(":", 1)
            try:
                return h, int(p)
            except ValueError:
                return host, 80
        return host, 80

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            line = await self._read_line(reader)
            if not line:
                writer.close(); await writer.wait_closed(); return
            req_line = line.decode("iso-8859-1").strip()
            parts = req_line.split(" ", 2)
            if len(parts) < 2:
                writer.close(); await writer.wait_closed(); return
            method, target = parts[0], parts[1]
            headers = await self._read_headers(reader)

            if method.upper() == "CONNECT":
                host, port = self._split_host(target)
                # MVP: simple TCP tunnel (no MITM in this minimal file, see README for scope)
                await self._tunnel(reader, writer, host, port)
                return

            host_header = next((v for (k, v) in headers if k.lower() == "host"), "")
            url = target if target.startswith("http") else f"http://{host_header}{target}"

            body = b""
            cl = next((v for (k, v) in headers if k.lower() == "content-length"), None)
            if cl:
                body = await reader.readexactly(int(cl))

            flow = self.flows.new_flow()
            flow.method = method
            flow.scheme = "http"
            flow.host = host_header.split(":")[0]
            flow.port = int(host_header.split(":")[1]) if ":" in host_header else 80
            flow.path = target
            flow.request.headers = headers
            flow.request.body = body
            await self.bus.publish_core(FLOW_CREATED, {"id": flow.id})

            url, headers, body, mocked = apply_rules("request", url, method, None, headers, body, self.ruleset)

            if self.intercept:
                await self.bus.publish_core(FLOW_PAUSED, {"id": flow.id, "where": "request"})
                fut = asyncio.get_event_loop().create_future()
                self._pending_forwards[flow.id] = fut
                decision = await fut
                self._pending_forwards.pop(flow.id, None)
                if decision == "Drop":
                    flow.error = "Dropped by user at request"
                    await self.bus.publish_core(FLOW_FINISHED, {"id": flow.id})
                    writer.close(); await writer.wait_closed(); return

            if mocked:
                resp_status = mocked["status"]
                resp_headers = mocked["headers"]
                resp_body = mocked["body"]
            else:
                async with httpx.AsyncClient(follow_redirects=False) as client:
                    r = await client.request(method, url, headers=dict(headers), content=body)
                resp_status = r.status_code
                resp_headers = list(r.headers.items())
                resp_body = r.content

            _, resp_headers, resp_body, _ = apply_rules("response", url, method, resp_status, resp_headers, resp_body, self.ruleset)

            if self.intercept:
                await self.bus.publish_core(FLOW_PAUSED, {"id": flow.id, "where": "response"})
                fut = asyncio.get_event_loop().create_future()
                self._pending_forwards[flow.id] = fut
                decision = await fut
                self._pending_forwards.pop(flow.id, None)
                if decision == "Drop":
                    flow.error = "Dropped by user at response"
                    await self.bus.publish_core(FLOW_FINISHED, {"id": flow.id})
                    writer.close(); await writer.wait_closed(); return

            flow.response.headers = resp_headers
            flow.response.body = resp_body
            flow.status_code = resp_status
            flow.size = len(resp_body)
            await self.bus.publish_core(FLOW_UPDATED, {"id": flow.id})

            writer.write(f"HTTP/1.1 {resp_status} OK\r\n".encode("ascii"))
            has_cl = any(k.lower() == "content-length" for k, _ in resp_headers)
            hdrs = resp_headers[:]
            if not has_cl:
                hdrs.append(("Content-Length", str(len(resp_body))))
            for k, v in hdrs:
                writer.write(f"{k}: {v}\r\n".encode("iso-8859-1"))
            writer.write(b"\r\n")
            writer.write(resp_body)
            await writer.drain()

            await self.bus.publish_core(FLOW_FINISHED, {"id": flow.id})
            writer.close(); await writer.wait_closed()

        except Exception as e:
            try:
                await self.bus.publish_core(LOG_MESSAGE, {"msg": f"Handler error: {e!r}"})
            except Exception:
                pass
            try:
                writer.close(); await writer.wait_closed()
            except Exception:
                pass

    async def _tunnel(self, reader, writer, host, port):
        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()
        try:
            remote_reader, remote_writer = await asyncio.open_connection(host, port)
        except Exception:
            writer.close(); await writer.wait_closed(); return

        async def pipe(src, dst):
            try:
                while True:
                    data = await src.read(65536)
                    if not data:
                        break
                    dst.write(data)
                    await dst.drain()
            except Exception:
                pass
            finally:
                try:
                    dst.close()
                    await dst.wait_closed()
                except Exception:
                    pass

        await asyncio.gather(pipe(reader, remote_writer), pipe(remote_reader, writer))
