import asyncio
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop
from .app import HuginApp
from ..core.bus import EventBus

def main(bus=None):
    app = QApplication([])
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    bus = bus or EventBus()
    win = HuginApp(bus=bus)
    win.show()
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()
