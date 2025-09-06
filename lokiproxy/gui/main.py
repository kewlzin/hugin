import asyncio
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop
from .app import HuginApp
from ..core.bus import EventBus
from ..core.proxy import ProxyServer

def main(bus=None, host="127.0.0.1", port=8080):
    app = QApplication([])
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    bus = bus or EventBus()

    # Cria o proxy e o expõe no bus ANTES de criar a janela
    proxy = ProxyServer(host=host, port=port, bus=bus)
    bus.proxy = proxy

    # Agende o servidor no loop do qasync
    asyncio.create_task(proxy.serve())

    win = HuginApp(bus=bus)
    win.show()

    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()
