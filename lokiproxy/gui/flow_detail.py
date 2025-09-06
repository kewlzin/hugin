from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTextEdit, QLabel
from ..core.flows import Flow
from ..core.bus import EventBus

def _fmt_headers(headers):
    return "\n".join(f"{k}: {v}" for k, v in headers)

def _fmt_hex(data: bytes, width=16):
    out = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hexpart = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append(f"{i:08x}  {hexpart:<{width*3}}  {asc}")
    return "\n".join(out)

class FlowDetail(QWidget):
    def __init__(self, bus: EventBus):
        super().__init__()
        self.bus = bus
        self._flow: Flow | None = None

        tabs = QTabWidget()
        self.req_text = QTextEdit(); self.req_text.setReadOnly(False)
        self.req_hex = QTextEdit(); self.req_hex.setReadOnly(True)
        self.resp_text = QTextEdit(); self.resp_text.setReadOnly(False)
        self.resp_hex = QTextEdit(); self.resp_hex.setReadOnly(True)

        reqw = QWidget(); rv = QVBoxLayout(reqw)
        rv.addWidget(QLabel("Headers + Body (editável)"))
        rv.addWidget(self.req_text, 1)
        rv.addWidget(QLabel("Hex (só leitura)"))
        rv.addWidget(self.req_hex, 1)

        respw = QWidget(); rsv = QVBoxLayout(respw)
        rsv.addWidget(QLabel("Headers + Body (editável)"))
        rsv.addWidget(self.resp_text, 1)
        rsv.addWidget(QLabel("Hex (só leitura)"))
        rsv.addWidget(self.resp_hex, 1)

        tabs.addTab(reqw, "Request")
        tabs.addTab(respw, "Response")

        v = QVBoxLayout(self)
        v.addWidget(tabs, 1)

    def load_flow(self, fid: int):
        flow = self.bus.proxy.flows.get(fid)
        self._flow = flow
        if not flow:
            self.req_text.setPlainText(""); self.resp_text.setPlainText("")
            self.req_hex.setPlainText(""); self.resp_hex.setPlainText("")
            return
        req_headers = _fmt_headers(flow.request.headers)
        self.req_text.setPlainText(req_headers + "\n\n" + flow.request.body.decode("utf-8", errors="replace"))
        self.req_hex.setPlainText(_fmt_hex(flow.request.body))
        resp_headers = _fmt_headers(flow.response.headers)
        self.resp_text.setPlainText(resp_headers + "\n\n" + (flow.response.body or b"").decode("utf-8", errors="replace"))
        self.resp_hex.setPlainText(_fmt_hex(flow.response.body or b""))
