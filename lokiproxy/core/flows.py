import time
import itertools
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple

@dataclass
class Message:
    headers: List[Tuple[str, str]] = field(default_factory=list)
    body: bytes = b""
    http_version: str = "1.1"

@dataclass
class Flow:
    id: int
    method: str = ""
    scheme: str = "http"
    host: str = ""
    port: int = 80
    path: str = "/"
    status_code: Optional[int] = None
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    request: Message = field(default_factory=Message)
    response: Message = field(default_factory=Message)
    error: Optional[str] = None
    size: int = 0

    @property
    def duration_ms(self) -> Optional[int]:
        end = self.finished_at or time.time()
        return int((end - self.started_at) * 1000)

class LRUFlows:
    def __init__(self, capacity: int = 2000):
        self.capacity = capacity
        self._flows: Dict[int, Flow] = {}
        self._order: List[int] = []
        import itertools
        self._id_counter = itertools.count(1)

    def new_flow(self) -> Flow:
        fid = next(self._id_counter)
        flow = Flow(id=fid)
        self._flows[fid] = flow
        self._order.append(fid)
        self._shrink_if_needed()
        return flow

    def _shrink_if_needed(self):
        while len(self._order) > self.capacity:
            old_id = self._order.pop(0)
            self._flows.pop(old_id, None)

    def get(self, fid: int) -> Optional[Flow]:
        return self._flows.get(fid)

    def all(self) -> List[Flow]:
        return [self._flows[i] for i in self._order if i in self._flows]

    def update(self, flow: Flow):
        if flow.id in self._flows:
            try:
                self._order.remove(flow.id)
            except ValueError:
                pass
            self._order.append(flow.id)
            self._flows[flow.id] = flow
