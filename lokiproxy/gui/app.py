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
        self.autoscroll_on = False

        # start proxy in background
        #self.proxy = ProxyServer(bus=self.bus)
        #self.bus.proxy = self.proxy
        self.proxy = self.bus.proxy
        #asyncio.create_task(self.proxy.serve())

        # UI
        topbar = QHBoxLayout()
        self.btn_intercept = QPushButton("Intercept OFF")
        self.btn_forward = QPushButton("Forward")
        self.btn_drop = QPushButton("Drop")
        self.btn_autoscroll = QPushButton("Auto-scroll OFF")
        self.btn_autoscroll.setCheckable(True)
        self.btn_cert = QPushButton("Gerar Certificado HTTPS")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filtro (texto / host / método / status)")

        topbar.addWidget(self.btn_intercept)
        topbar.addWidget(self.btn_forward)
        topbar.addWidget(self.btn_drop)
        topbar.addWidget(self.btn_autoscroll)
        topbar.addWidget(self.btn_cert)
        topbar.addWidget(QLabel("Filtro:"))
        topbar.addWidget(self.search, 1)

        # Layout principal com mais espaço para requisições
        main_splitter = QSplitter(Qt.Vertical)
        
        # Área principal: tabela de requisições e detalhes
        center = QSplitter()
        self.table = FlowsTable(self.bus)
        self.detail = FlowDetail(self.bus)

        center.addWidget(self.table)
        center.addWidget(self.detail)
        center.setStretchFactor(0, 2)  # Tabela menor
        center.setStretchFactor(1, 3)  # Detalhes maior

        # Editor de regras (menor)
        rules = RulesEditor(self.bus)
        rules.setMaximumHeight(150)  # Limita altura máxima

        main_splitter.addWidget(center)
        main_splitter.addWidget(rules)
        main_splitter.setStretchFactor(0, 4)  # Área principal maior
        main_splitter.setStretchFactor(1, 1)  # Regras menor

        container = QWidget()
        v = QVBoxLayout(container)
        v.addLayout(topbar)
        v.addWidget(main_splitter, 1)

        self.setCentralWidget(container)

        # wiring
        self.btn_intercept.clicked.connect(self.toggle_intercept)
        self.btn_forward.clicked.connect(self.forward_selected)
        self.btn_drop.clicked.connect(self.drop_selected)
        self.btn_autoscroll.clicked.connect(self.toggle_autoscroll)
        self.btn_cert.clicked.connect(self.generate_certificate)
        self.search.textChanged.connect(self.table.set_filter)

        self.table.selection_changed.connect(self.detail.load_flow)

        # Inicia o event loop após a GUI estar pronta
        self._start_event_loop()

    def _start_event_loop(self):
        """Inicia o event loop de forma segura com qasync"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._event_loop())
        except RuntimeError:
            # Se não há loop rodando, aguarda até que a GUI esteja pronta
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._start_event_loop)

    def _safe_create_task(self, coro):
        """Cria uma task de forma segura, verificando se há um event loop rodando"""
        try:
            loop = asyncio.get_running_loop()
            return loop.create_task(coro)
        except RuntimeError:
            # Se não há loop rodando, agenda para quando o loop estiver disponível
            from PySide6.QtCore import QTimer
            def schedule_task():
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(coro)
                except RuntimeError:
                    pass
            QTimer.singleShot(0, schedule_task)

    async def _event_loop(self):
        async for ev in self.bus.subscribe_gui():
            if ev.type == LOG_MESSAGE:
                self.statusBar().showMessage(ev.data.get("msg", ""), 5000)
            elif ev.type in (FLOW_CREATED, FLOW_UPDATED, FLOW_FINISHED):
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, self.table.refresh)
                # Auto-scroll para a última requisição se habilitado
                if self.autoscroll_on and ev.type == FLOW_CREATED:
                    QTimer.singleShot(50, self.table.scroll_to_bottom)
                # Se intercept está ativo, seleciona automaticamente a última requisição
                if self.intercept_on and ev.type == FLOW_CREATED:
                    QTimer.singleShot(100, self.table.scroll_to_bottom)
                    QTimer.singleShot(150, self._select_last_flow)
            elif ev.type == FLOW_PAUSED:
                self.table.mark_paused(ev.data["id"])
                # Se intercept está ativo, seleciona a requisição pausada
                if self.intercept_on:
                    QTimer.singleShot(50, self._select_flow_by_id, ev.data["id"])

    @Slot()
    def toggle_intercept(self):
        self.intercept_on = not self.intercept_on
        self.btn_intercept.setText(f"Intercept {'ON' if self.intercept_on else 'OFF'}")
        self._safe_create_task(self.bus.send_gui_cmd(SET_INTERCEPT, {"on": self.intercept_on}))

    @Slot()
    def toggle_autoscroll(self):
        self.autoscroll_on = self.btn_autoscroll.isChecked()
        self.btn_autoscroll.setText(f"Auto-scroll {'ON' if self.autoscroll_on else 'OFF'}")

    @Slot()
    def generate_certificate(self):
        """Gera certificado HTTPS para importar no navegador"""
        try:
            from ..core.ca import ensure_ca, CA_CERT_PATH
            cert, key = ensure_ca()
            
            from PySide6.QtWidgets import QMessageBox, QFileDialog
            from PySide6.QtCore import QStandardPaths
            import os
            
            # Pergunta onde salvar o certificado
            downloads_path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
            cert_path = os.path.join(downloads_path, "huginproxy-ca.pem")
            
            # Copia o certificado para Downloads
            import shutil
            shutil.copy2(CA_CERT_PATH, cert_path)
            
            QMessageBox.information(
                self, 
                "Certificado Gerado", 
                f"Certificado HTTPS gerado com sucesso!\n\n"
                f"Arquivo salvo em: {cert_path}\n\n"
                f"Para instalar no navegador:\n"
                f"1. Abra as configurações do navegador\n"
                f"2. Vá para Certificados/Autoridades de Certificação\n"
                f"3. Importe o arquivo: {cert_path}\n"
                f"4. Marque como confiável para HTTPS"
            )
            
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Erro", f"Erro ao gerar certificado: {str(e)}")

    def _selected_flow_id(self):
        return self.table.current_flow_id()

    def _select_last_flow(self):
        """Seleciona a última requisição na tabela"""
        if self.table.model.rowCount() > 0:
            last_row = self.table.model.rowCount() - 1
            last_idx = self.table.model.index(last_row, 0)
            proxy_idx = self.table.proxy_model.mapFromSource(last_idx)
            self.table.table.setCurrentIndex(proxy_idx)
            # Carrega os detalhes da requisição selecionada
            self.detail.load_flow(self.table.model.flow_at(last_row).id)

    def _select_flow_by_id(self, flow_id):
        """Seleciona uma requisição específica pelo ID"""
        for row in range(self.table.model.rowCount()):
            flow = self.table.model.flow_at(row)
            if flow.id == flow_id:
                idx = self.table.model.index(row, 0)
                proxy_idx = self.table.proxy_model.mapFromSource(idx)
                self.table.table.setCurrentIndex(proxy_idx)
                self.detail.load_flow(flow_id)
                break

    @Slot()
    def forward_selected(self):
        fid = self._selected_flow_id()
        if fid:
            self._safe_create_task(self.bus.send_gui_cmd(FORWARD_FLOW, {"flow_id": fid}))

    @Slot()
    def drop_selected(self):
        fid = self._selected_flow_id()
        if fid:
            self._safe_create_task(self.bus.send_gui_cmd(DROP_FLOW, {"flow_id": fid}))
