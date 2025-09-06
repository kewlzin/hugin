import asyncio
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QSplitter
from PySide6.QtCore import Qt, Slot
from ..core.bus import EventBus, FLOW_CREATED, FLOW_UPDATED, FLOW_FINISHED, FLOW_PAUSED, LOG_MESSAGE, SET_INTERCEPT, FORWARD_FLOW, DROP_FLOW
from .flows_view import FlowsTable
from .flow_detail import FlowDetail
from .rules_editor import RulesEditor
from ..core.proxy import ProxyServer

class HuginApp(QMainWindow):
    def __init__(self, bus=None):
        super().__init__()
        self.setWindowTitle("HuginProxy MVP")
        self.resize(1200, 700)
        self.bus = bus or EventBus()
        self.intercept_on = False

        # start proxy in background
        self.proxy = ProxyServer(bus=self.bus)
        self.bus.proxy = self.proxy
        asyncio.create_task(self.proxy.serve())

        # UI
        topbar = QHBoxLayout()
        self.btn_intercept = QPushButton("Intercept OFF")
        self.btn_forward = QPushButton("Forward")
        self.btn_drop = QPushButton("Drop")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filtro (texto / host / método / status)")

        topbar.addWidget(self.btn_intercept)
        topbar.addWidget(self.btn_forward)
        topbar.addWidget(self.btn_drop)
        topbar.addWidget(QLabel("Filtro:"))
        topbar.addWidget(self.search, 1)

        center = QSplitter()
        self.table = FlowsTable(self.bus)
        self.detail = FlowDetail(self.bus)

        center.addWidget(self.table)
        center.addWidget(self.detail)
        center.setStretchFactor(0, 3)
        center.setStretchFactor(1, 4)

        rules = RulesEditor(self.bus)

        container = QWidget()
        v = QVBoxLayout(container)
        v.addLayout(topbar)
        v.addWidget(center, 1)
        v.addWidget(rules, 1)

        self.setCentralWidget(container)

        # wiring
        self.btn_intercept.clicked.connect(self.toggle_intercept)
        self.btn_forward.clicked.connect(self.forward_selected)
        self.btn_drop.clicked.connect(self.drop_selected)
        self.search.textChanged.connect(self.table.set_filter)

        self.table.selection_changed.connect(self.detail.load_flow)

        asyncio.create_task(self._event_loop())

    async def _event_loop(self):
        async for ev in self.bus.subscribe_gui():
            if ev.type == LOG_MESSAGE:
                self.statusBar().showMessage(ev.data.get("msg", ""), 5000)
            elif ev.type in (FLOW_CREATED, FLOW_UPDATED, FLOW_FINISHED):
                self.table.refresh()
            elif ev.type == FLOW_PAUSED:
                self.table.mark_paused(ev.data["id"])

    @Slot()
    def toggle_intercept(self):
        self.intercept_on = not self.intercept_on
        self.btn_intercept.setText(f"Intercept {'ON' if self.intercept_on else 'OFF'}")
        asyncio.create_task(self.bus.send_gui_cmd(SET_INTERCEPT, {"on": self.intercept_on}))

    def _selected_flow_id(self):
        return self.table.current_flow_id()

    @Slot()
    def forward_selected(self):
        fid = self._selected_flow_id()
        if fid:
            asyncio.create_task(self.bus.send_gui_cmd(FORWARD_FLOW, {"flow_id": fid}))

    @Slot()
    def drop_selected(self):
        fid = self._selected_flow_id()
        if fid:
            asyncio.create_task(self.bus.send_gui_cmd(DROP_FLOW, {"flow_id": fid}))
