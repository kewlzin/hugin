import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class Event:
    type: str
    data: Dict[str, Any]

FLOW_CREATED = "FlowCreated"
FLOW_UPDATED = "FlowUpdated"
FLOW_FINISHED = "FlowFinished"
FLOW_PAUSED = "FlowPaused"
LOG_MESSAGE = "LogMessage"

SET_INTERCEPT = "SetIntercept"
FORWARD_FLOW = "Forward"
DROP_FLOW = "Drop"
REPEAT_FLOW = "Repeat"
APPLY_RULES = "ApplyRules"

class EventBus:
    def __init__(self) -> None:
        self.core_to_gui: Optional[asyncio.Queue[Event]] = None
        self.gui_to_core: Optional[asyncio.Queue[Event]] = None
        self._initialized = False

    def _ensure_queues(self):
        """Garante que as queues sejam criadas no event loop correto"""
        if not self._initialized:
            try:
                loop = asyncio.get_running_loop()
                self.core_to_gui = asyncio.Queue()
                self.gui_to_core = asyncio.Queue()
                self._initialized = True
            except RuntimeError:
                # Se não há loop rodando, cria as queues sem loop específico
                self.core_to_gui = asyncio.Queue()
                self.gui_to_core = asyncio.Queue()
                self._initialized = True

    async def publish_core(self, type: str, data: Dict[str, Any]) -> None:
        self._ensure_queues()
        await self.core_to_gui.put(Event(type, data))

    async def consume_gui_cmd(self) -> Event:
        self._ensure_queues()
        ev = await self.gui_to_core.get()
        self.gui_to_core.task_done()
        return ev

    async def subscribe_gui(self):
        self._ensure_queues()
        while True:
            ev = await self.core_to_gui.get()
            self.core_to_gui.task_done()
            yield ev

    async def send_gui_cmd(self, type: str, data: Dict[str, Any]) -> None:
        self._ensure_queues()
        await self.gui_to_core.put(Event(type, data))
