# File: ui/tabs/logic_tab.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class LogicTab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lbl = QLabel("Logic Analyzer / Oscilloscope (Coming soon)")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size:18px;color:gray;")
        lay.addWidget(lbl)
