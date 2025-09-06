from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QFileDialog, QMessageBox
from ..core.rules import Ruleset
from ..core.bus import EventBus, APPLY_RULES
import yaml
import asyncio

TEMPLATE = {
    "rules": [
        {
            "name": "Exemplo: mock google",
            "on": "request",
            "match": {"url_regex": "google\\.com", "method": "GET"},
            "action": {
                "mock_response": {"status": 200, "headers": {"Content-Type": "text/plain"}, "body": "mocked!"}
            },
            "enabled": True,
        }
    ]
}

class RulesEditor(QWidget):
    def __init__(self, bus: EventBus):
        super().__init__()
        self.bus = bus
        self.text = QTextEdit()
        self.text.setPlainText(yaml.safe_dump(TEMPLATE, sort_keys=False, allow_unicode=True))

        btns = QHBoxLayout()
        btn_load = QPushButton("Carregar YAML")
        btn_save = QPushButton("Salvar YAML")
        btn_apply = QPushButton("Aplicar")

        btn_load.clicked.connect(self.load_yaml)
        btn_save.clicked.connect(self.save_yaml)
        btn_apply.clicked.connect(self.apply_rules)

        v = QVBoxLayout(self)
        v.addLayout(btns)
        v.addWidget(self.text)
        btns.addWidget(btn_load); btns.addWidget(btn_save); btns.addWidget(btn_apply)

    def load_yaml(self):
        path, _ = QFileDialog.getOpenFileName(self, "Carregar regras", "", "YAML (*.yaml *.yml)")
        if not path: return
        with open(path, "r", encoding="utf-8") as f:
            self.text.setPlainText(f.read())

    def save_yaml(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar regras", "rules.yaml", "YAML (*.yaml *.yml)")
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.text.toPlainText())

    def apply_rules(self):
        try:
            data = yaml.safe_load(self.text.toPlainText()) or {}
            rs = Ruleset(**data)
        except Exception as e:
            QMessageBox.critical(self, "Erro de validação", str(e))
            return
        asyncio.create_task(self.bus.send_gui_cmd(APPLY_RULES, {"ruleset": rs.dict()}))
        QMessageBox.information(self, "Regras", "Regras aplicadas.")
