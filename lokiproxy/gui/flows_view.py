from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, Signal, QSortFilterProxyModel
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView
from ..core.flows import Flow, LRUFlows
from ..core.bus import EventBus

class FlowsModel(QAbstractTableModel):
    HEADERS = ["ID", "Método", "Host", "Caminho", "Status", "Tamanho", "Duração (ms)"]
    def __init__(self, flows: LRUFlows):
        super().__init__()
        self.flows = flows
        self._rows = []

    def refresh(self):
        self.beginResetModel()
        self._rows = self.flows.all()
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._rows)

    def columnCount(self, parent=None):
        return len(self.HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole,):
            return None
        f: Flow = self._rows[index.row()]
        col = index.column()
        if col == 0: return f.id
        if col == 1: return f.method
        if col == 2: return f.host
        if col == 3: return f.path
        if col == 4: return f.status_code or ""
        if col == 5: return f.size
        if col == 6: return f.duration_ms or ""
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole: return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return section+1

    def flow_at(self, row) -> Flow:
        return self._rows[row]

class FlowsTable(QWidget):
    selection_changed = Signal(int)  # flow id
    def __init__(self, bus: EventBus):
        super().__init__()
        self.bus = bus
        self.proxy = bus.proxy

        self.model = FlowsModel(self.proxy.flows)
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setSourceModel(self.model)

        v = QVBoxLayout(self)
        self.table = QTableView()
        self.table.setModel(self.proxy_model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.doubleClicked.connect(self._emit_selected)
        v.addWidget(self.table)

        self.refresh()

    def refresh(self):
        self.model.refresh()

    def _emit_selected(self, idx):
        src = self.proxy_model.mapToSource(idx)
        fid = self.model.flow_at(src.row()).id
        self.selection_changed.emit(fid)

    def current_flow_id(self) -> int | None:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        src = self.proxy_model.mapToSource(idx)
        return self.model.flow_at(src.row()).id

    def set_filter(self, text: str):
        self.proxy_model.setFilterFixedString(text)

    def mark_paused(self, fid: int):
        for row, f in enumerate(self.model._rows):
            if f.id == fid:
                idx = self.model.index(row, 0)
                self.table.setCurrentIndex(self.proxy_model.mapFromSource(idx))
                break
