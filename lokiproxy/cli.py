import argparse
import asyncio
from .core.ca import ensure_ca, CA_CERT_PATH, CA_KEY_PATH
from .core.proxy import ProxyServer
from .core.bus import EventBus
from .gui.main import main as gui_main

def cmd_ca_init(args):
    cert, key = ensure_ca()
    print(f"CA gerada em:\n  {CA_CERT_PATH}\n  {CA_KEY_PATH}")
    print("Instale o ca.pem manualmente no navegador de testes (escopo local, uso ético).")

async def run_proxy(args, bus: EventBus):
    proxy = ProxyServer(host=args.host, port=args.port, bus=bus)
    bus.proxy = proxy
    await proxy.serve()

def cmd_run(args):
    bus = EventBus()
    loop = asyncio.get_event_loop()
    loop.create_task(run_proxy(args, bus))
    gui_main(bus)

def main():
    p = argparse.ArgumentParser(prog="lokiproxy", description="HuginProxy MVP")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_ca = sub.add_parser("ca", help="CA utilities")
    p_ca_sub = p_ca.add_subparsers(dest="subcmd", required=True)
    p_ca_sub.add_parser("init", help="Generate local CA")

    p_run = sub.add_parser("run", help="Run proxy + GUI")
    p_run.add_argument("--host", default="127.0.0.1")
    p_run.add_argument("--port", default=8080, type=int)

    args = p.parse_args()
    if args.cmd == "ca" and args.subcmd == "init":
        cmd_ca_init(args)
    elif args.cmd == "run":
        cmd_run(args)

if __name__ == "__main__":
    main()
