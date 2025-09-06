import asyncio
from dataclasses import dataclass
from typing import Any, Dict

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
        self.core_to_gui: asyncio.Queue[Event] = asyncio.Queue()
        self.gui_to_core: asyncio.Queue[Event] = asyncio.Queue()

    async def publish_core(self, type: str, data: Dict[str, Any]) -> None:
        await self.core_to_gui.put(Event(type, data))

    async def consume_gui_cmd(self) -> Event:
        ev = await self.gui_to_core.get()
        self.gui_to_core.task_done()
        return ev

    async def subscribe_gui(self):
        while True:
            ev = await self.core_to_gui.get()
            self.core_to_gui.task_done()
            yield ev

    async def send_gui_cmd(self, type: str, data: Dict[str, Any]) -> None:
        await self.gui_to_core.put(Event(type, data))
