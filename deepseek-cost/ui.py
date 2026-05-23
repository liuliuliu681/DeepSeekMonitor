import logging
from datetime import datetime

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QSpinBox,
    QTextEdit, QVBoxLayout, QWidget,
)

from animation import BalanceAnimator
from api import fetch_balance
from config import load_config, save_config
from logger import setup_logger

# ═══════════════════════════════════════════════════════════════════
#  Win11 Fluent Design Tokens
# ═══════════════════════════════════════════════════════════════════
LIGHT = {
    "window_bg": "#F3F3F3",
    "card_bg": "#FFFFFF",
    "card_border": "#E0E0E0",
    "text": "#1E1E1E",
    "text_secondary": "#5C5C5C",
    "text_tertiary": "#A0A0A0",
    "accent": "#0078D4",
    "accent_hover": "#106EBE",
    "accent_pressed": "#005A9E",
    "accent_text": "#FFFFFF",
    "input_bg": "#FFFFFF",
    "input_border": "#C0C0C0",
    "input_focus_border": "#0078D4",
    "chip_bg": "#F5F5F5",
    "chip_border": "#EBEBEB",
    "status_bar_bg": "#FCFCFC",
    "status_bar_border": "#E8E8E8",
    "log_bg": "#FAFAFA",
    "log_text": "#1E1E1E",
    "shadow": QColor(0, 0, 0, 30),
    "success": "#10B981",
    "error": "#EF4444",
    "warning": "#F59E0B",
    "waiting": "#9CA3AF",
    "scrollbar_handle": "#C4C4C4",
    "scrollbar_handle_hover": "#A0A0A0",
    "toggle_hover_bg": "#F0F0F0",
    "separator": "#E8E8E8",
}

DARK = {
    "window_bg": "#202020",
    "card_bg": "#2B2B2B",
    "card_border": "#383838",
    "text": "#E8E8E8",
    "text_secondary": "#A0A0A0",
    "text_tertiary": "#6B7280",
    "accent": "#60CDFF",
    "accent_hover": "#80D6FF",
    "accent_pressed": "#4DB8F0",
    "accent_text": "#1E1E1E",
    "input_bg": "#333333",
    "input_border": "#454545",
    "input_focus_border": "#60CDFF",
    "chip_bg": "#333333",
    "chip_border": "#3D3D3D",
    "status_bar_bg": "#252525",
    "status_bar_border": "#353535",
    "log_bg": "#2A2A2A",
    "log_text": "#E8E8E8",
    "shadow": QColor(0, 0, 0, 80),
    "success": "#10B981",
    "error": "#EF4444",
    "warning": "#F59E0B",
    "waiting": "#6B7280",
    "scrollbar_handle": "#555555",
    "scrollbar_handle_hover": "#707070",
    "toggle_hover_bg": "#333333",
    "separator": "#383838",
}


# ═══════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════
def _shadow(widget, t):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(16)
    effect.setColor(t["shadow"])
    effect.setOffset(0, 3)
    widget.setGraphicsEffect(effect)


def _app_stylesheet(t):
    return f"""
    QToolTip {{
        background: {t["card_bg"]};
        color: {t["text"]};
        border: 1px solid {t["card_border"]};
        border-radius: 6px;
        padding: 6px 10px;
    }}
    """


def _scrollbar_qss(t):
    return f"""
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 8px;
        margin: 4px 0;
    }}
    QScrollBar::handle:vertical {{
        background: {t["scrollbar_handle"]};
        border-radius: 4px;
        min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t["scrollbar_handle_hover"]};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        height: 0px;
    }}
    """


# ═══════════════════════════════════════════════════════════════════
#  API Worker Thread
# ═══════════════════════════════════════════════════════════════════
class BalanceWorker(QThread):
    finished = Signal(dict)

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg

    def run(self):
        try:
            result = fetch_balance(
                self.cfg["api_key"],
                self.cfg["base_url"],
                self.cfg["balance_endpoint"],
            )
        except Exception as e:
            result = {"success": False, "error": str(e)}
        self.finished.emit(result)


# ═══════════════════════════════════════════════════════════════════
#  BigAmountWidget — large centered metric for monitoring panel
# ═══════════════════════════════════════════════════════════════════
class BigAmountWidget(QFrame):
    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.setObjectName("bigAmount")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._amount = QLabel("¥ ---.--")
        self._amount.setObjectName("bigAmountValue")
        self._amount.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._amount)

        self._label = QLabel(label)
        self._label.setObjectName("bigAmountLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

    def set_value(self, amount):
        self._amount.setText(f"¥ {float(amount):.2f}")

    def clear(self):
        self._amount.setText("¥ ---.--")

    def apply_theme(self, t):
        self.setStyleSheet(f"""
            #bigAmount {{
                background: transparent;
                border: none;
            }}
            #bigAmountValue {{
                color: {t["accent"]};
                font-size: 56px;
                font-weight: 700;
            }}
            #bigAmountLabel {{
                color: {t["text_secondary"]};
                font-size: 13px;
            }}
        """)


# ═══════════════════════════════════════════════════════════════════
#  SettingsPanel — collapsible settings form
# ═══════════════════════════════════════════════════════════════════
class SettingsPanel(QFrame):
    save_clicked = Signal()
    refresh_clicked = Signal()
    preview_decrease = Signal()
    preview_increase = Signal()

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPanel")
        self.cfg = cfg

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setText(cfg.get("api_key", ""))
        self.key_input.setPlaceholderText("输入 DeepSeek API Key")
        layout.addLayout(self._form_row("API Key", self.key_input))

        self.url_input = QLineEdit()
        self.url_input.setText(cfg.get("base_url", "https://api.deepseek.com"))
        layout.addLayout(self._form_row("Base URL", self.url_input))

        self.ep_input = QLineEdit()
        self.ep_input.setText(cfg.get("balance_endpoint", "/user/balance"))
        layout.addLayout(self._form_row("余额接口", self.ep_input))

        interval_row = QHBoxLayout()
        interval_row.setSpacing(10)
        lbl = QLabel("刷新间隔")
        lbl.setObjectName("formLabel")
        interval_row.addWidget(lbl)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(5, 3600)
        self.interval_spin.setValue(cfg.get("refresh_interval", 30))
        self.interval_spin.setSuffix(" 秒")
        self.interval_spin.setObjectName("intervalSpin")
        interval_row.addWidget(self.interval_spin)
        interval_row.addStretch()
        layout.addLayout(interval_row)

        layout.addSpacing(8)

        self.anim_check = QCheckBox("启用动画")
        self.anim_check.setObjectName("settingCheck")
        self.anim_check.setChecked(cfg.get("animation_enabled", True))
        self.anim_check.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.anim_check)

        self.sound_check = QCheckBox("启用音效")
        self.sound_check.setObjectName("settingCheck")
        self.sound_check.setChecked(cfg.get("sound_enabled", True))
        self.sound_check.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.sound_check)

        layout.addSpacing(8)
        preview_label = QLabel("动画预览")
        preview_label.setObjectName("formLabel")
        layout.addWidget(preview_label)

        preview_row = QHBoxLayout()
        preview_row.setSpacing(10)

        preview_dec_btn = QPushButton("预览减少动画")
        preview_dec_btn.setObjectName("previewDecreaseBtn")
        preview_dec_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        preview_dec_btn.clicked.connect(self.preview_decrease.emit)
        preview_row.addWidget(preview_dec_btn)

        preview_inc_btn = QPushButton("预览增加动画")
        preview_inc_btn.setObjectName("previewIncreaseBtn")
        preview_inc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        preview_inc_btn.clicked.connect(self.preview_increase.emit)
        preview_row.addWidget(preview_inc_btn)

        preview_row.addStretch()
        layout.addLayout(preview_row)

        layout.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        save_btn = QPushButton("保存设置")
        save_btn.setObjectName("primaryBtn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        refresh_btn = QPushButton("手动刷新")
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh_clicked.emit)
        btn_row.addWidget(refresh_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _form_row(self, label, widget):
        row = QHBoxLayout()
        row.setSpacing(10)
        lbl = QLabel(label)
        lbl.setObjectName("formLabel")
        lbl.setFixedWidth(70)
        row.addWidget(lbl)
        widget.setObjectName("formInput")
        row.addWidget(widget, stretch=1)
        return row

    def _on_save(self):
        self.cfg["api_key"] = self.key_input.text().strip()
        self.cfg["base_url"] = self.url_input.text().strip()
        self.cfg["balance_endpoint"] = self.ep_input.text().strip()
        self.cfg["refresh_interval"] = self.interval_spin.value()
        save_config(self.cfg)
        self.save_clicked.emit()

    def get_config(self):
        return {
            "api_key": self.key_input.text().strip(),
            "base_url": self.url_input.text().strip(),
            "balance_endpoint": self.ep_input.text().strip(),
            "refresh_interval": self.interval_spin.value(),
            "animation_enabled": self.anim_check.isChecked(),
            "sound_enabled": self.sound_check.isChecked(),
        }

    def apply_theme(self, t):
        self.setStyleSheet(f"""
            #settingsPanel {{
                background: {t["card_bg"]};
                border: 1px solid {t["card_border"]};
                border-radius: 10px;
            }}
            #formLabel {{
                color: {t["text"]};
                font-size: 13px;
            }}
            #formInput {{
                background: {t["input_bg"]};
                color: {t["text"]};
                border: 1px solid {t["input_border"]};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }}
            #formInput:focus {{
                border-color: {t["input_focus_border"]};
            }}
            #intervalSpin {{
                background: {t["input_bg"]};
                color: {t["text"]};
                border: 1px solid {t["input_border"]};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
            }}
            #intervalSpin:focus {{
                border-color: {t["input_focus_border"]};
            }}
            #intervalSpin::up-button, #intervalSpin::down-button {{
                width: 20px;
                border: none;
            }}
            #primaryBtn {{
                background: {t["accent"]};
                color: {t["accent_text"]};
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 600;
            }}
            #primaryBtn:hover {{
                background: {t["accent_hover"]};
            }}
            #primaryBtn:pressed {{
                background: {t["accent_pressed"]};
            }}
            #secondaryBtn {{
                background: transparent;
                color: {t["accent"]};
                border: 1px solid {t["accent"]};
                border-radius: 6px;
                padding: 7px 17px;
                font-size: 13px;
            }}
            #secondaryBtn:hover {{
                background: {t["accent"]};
                color: {t["accent_text"]};
            }}
            #previewDecreaseBtn {{
                background: transparent;
                color: {t["error"]};
                border: 1px solid {t["error"]};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            #previewDecreaseBtn:hover {{
                background: {t["error"]};
                color: #FFFFFF;
            }}
            #previewIncreaseBtn {{
                background: transparent;
                color: {t["success"]};
                border: 1px solid {t["success"]};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            #previewIncreaseBtn:hover {{
                background: {t["success"]};
                color: #FFFFFF;
            }}
            #settingCheck {{
                color: {t["text"]};
                font-size: 13px;
                spacing: 8px;
            }}
            #settingCheck::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid {t["input_border"]};
                background: {t["input_bg"]};
            }}
            #settingCheck::indicator:checked {{
                background: {t["accent"]};
                border-color: {t["accent"]};
            }}
        """)
        _shadow(self, t)


# ═══════════════════════════════════════════════════════════════════
#  LogPanel — collapsible log viewer
# ═══════════════════════════════════════════════════════════════════
class LogPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("logPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.document().setMaximumBlockCount(200)
        self.log_text.setObjectName("logView")
        layout.addWidget(self.log_text)

    def add_log(self, message, level):
        if level == logging.ERROR:
            color = "#EF4444"
        elif level == logging.WARNING:
            color = "#F59E0B"
        else:
            self.log_text.append(message)
            return
        self.log_text.append(
            f'<span style="color:{color};white-space:pre-wrap">{message}</span>'
        )

    def apply_theme(self, t):
        self.setStyleSheet(f"""
            #logPanel {{
                background: {t["card_bg"]};
                border: 1px solid {t["card_border"]};
                border-radius: 10px;
            }}
            #logView {{
                background: {t["log_bg"]};
                color: {t["log_text"]};
                border: none;
                border-radius: 6px;
                font-family: "Cascadia Code", "Consolas", "Microsoft YaHei", sans-serif;
                font-size: 12px;
                padding: 8px 10px;
            }}
        """)
        _shadow(self, t)


# ═══════════════════════════════════════════════════════════════════
#  StatusBar — simplified bottom bar
# ═══════════════════════════════════════════════════════════════════
class StatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)

        self.time_label = QLabel("上次更新: --")
        self.time_label.setObjectName("statusTime")
        layout.addWidget(self.time_label)
        layout.addStretch()
        self.status_label = QLabel("● 等待中")
        self.status_label.setObjectName("statusText")
        layout.addWidget(self.status_label)

    def set_status(self, status, text):
        colors = {"normal": "#10B981", "error": "#EF4444", "waiting": "#9CA3AF"}
        color = colors.get(status, "#9CA3AF")
        self.status_label.setText(
            f'<span style="color:{color};font-weight:600">●</span> {text}'
        )

    def touch_time(self):
        self.time_label.setText(f"上次更新: {datetime.now().strftime('%H:%M:%S')}")

    def apply_theme(self, t):
        self.setStyleSheet(f"""
            #statusBar {{
                background: {t["status_bar_bg"]};
                border-top: 1px solid {t["status_bar_border"]};
                border-radius: 0px;
            }}
            #statusTime {{
                color: {t["text_tertiary"]};
                font-size: 12px;
            }}
            #statusText {{
                color: {t["text_tertiary"]};
                font-size: 12px;
            }}
        """)


# ═══════════════════════════════════════════════════════════════════
#  MainWindow — minimal monitoring panel
# ═══════════════════════════════════════════════════════════════════
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.logger = setup_logger(self._on_log)
        self._dark = self.cfg.get("theme") == "dark"
        self._theme = DARK if self._dark else LIGHT
        self._settings_open = False
        self._log_open = False
        self._worker = None
        self._last_balance = None
        self._request_id = 0

        self._watchdog_timer = QTimer(self)
        self._watchdog_timer.setSingleShot(True)
        self._watchdog_timer.timeout.connect(self._on_watchdog)

        self._animator = BalanceAnimator(self)
        self._animator.animations_enabled = self.cfg.get("animation_enabled", True)
        self._animator.sound_enabled = self.cfg.get("sound_enabled", True)

        self.setWindowTitle("DeepSeek 余额监控器")
        self.resize(500, 700)
        self.setMinimumSize(420, 560)

        self._setup_ui()
        self._apply_theme()
        self._setup_timer()

        if self.cfg.get("api_key"):
            self.refresh_balance()
        else:
            self.logger.info("请先配置 API Key，然后开始监控")

    # ── UI construction ────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 8)
        root.setSpacing(0)

        # Header
        hdr = QHBoxLayout()
        app_title = QLabel("DeepSeek 余额监控")
        app_title.setObjectName("appTitle")
        hdr.addWidget(app_title)
        hdr.addStretch()

        self.theme_btn = QPushButton("☀ 亮色模式" if self._dark else "🌙 深色模式")
        self.theme_btn.setObjectName("themeToggle")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        hdr.addWidget(self.theme_btn)
        root.addLayout(hdr)

        root.addSpacing(12)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("mainScroll")

        content = QWidget()
        content.setObjectName("contentWidget")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # Top stretch — pushes metrics to center
        cl.addStretch(1)

        # Balance metric
        self.balance_widget = BigAmountWidget("账户余额")
        cl.addWidget(self.balance_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Bottom stretch — balances top stretch
        cl.addStretch(1)

        # Separator
        sep = QFrame()
        sep.setObjectName("toggleSeparator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        cl.addWidget(sep)

        # Toggle row
        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 4, 0, 4)
        toggle_row.setSpacing(32)
        toggle_row.addStretch()

        self.settings_toggle = QPushButton("▸ 设置")
        self.settings_toggle.setObjectName("toggleBtn")
        self.settings_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_toggle.clicked.connect(self._toggle_settings)
        toggle_row.addWidget(self.settings_toggle)

        self.log_toggle = QPushButton("▸ 日志")
        self.log_toggle.setObjectName("toggleBtn")
        self.log_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.log_toggle.clicked.connect(self._toggle_log)
        toggle_row.addWidget(self.log_toggle)

        toggle_row.addStretch()
        cl.addLayout(toggle_row)

        # Another separator
        sep2 = QFrame()
        sep2.setObjectName("toggleSeparator")
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFixedHeight(1)
        cl.addWidget(sep2)

        # Settings panel (hidden by default)
        self.settings_panel = SettingsPanel(self.cfg)
        self.settings_panel.save_clicked.connect(self._on_settings_saved)
        self.settings_panel.refresh_clicked.connect(self._refresh_all)
        self.settings_panel.preview_decrease.connect(self._preview_decrease)
        self.settings_panel.preview_increase.connect(self._preview_increase)
        self.settings_panel.setVisible(False)
        cl.addWidget(self.settings_panel)

        # Log panel (hidden by default)
        self.log_panel = LogPanel()
        self.log_panel.setMinimumHeight(160)
        self.log_panel.setVisible(False)
        cl.addWidget(self.log_panel)

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        # Status bar
        self.status_bar = StatusBar()
        root.addWidget(self.status_bar)

    # ── Toggle logic ───────────────────────────────────────────
    def _toggle_settings(self):
        self._settings_open = not self._settings_open
        self.settings_panel.setVisible(self._settings_open)
        self.settings_toggle.setText("▾ 设置" if self._settings_open else "▸ 设置")

    def _toggle_log(self):
        self._log_open = not self._log_open
        self.log_panel.setVisible(self._log_open)
        self.log_toggle.setText("▾ 日志" if self._log_open else "▸ 日志")

    # ── Theme ─────────────────────────────────────────────────
    def _apply_theme(self):
        t = self._theme
        self.setStyleSheet(f"""
            #appTitle {{
                color: {t["text"]};
                font-size: 16px;
                font-weight: 600;
            }}
            #themeToggle {{
                background: {t["chip_bg"]};
                color: {t["text_secondary"]};
                border: 1px solid {t["chip_border"]};
                border-radius: 8px;
                padding: 5px 12px;
                font-size: 12px;
            }}
            #themeToggle:hover {{
                background: {t["card_border"]};
            }}
            #contentWidget {{
                background: transparent;
            }}
            #toggleBtn {{
                background: transparent;
                color: {t["text_tertiary"]};
                border: none;
                border-radius: 6px;
                padding: 5px 16px;
                font-size: 13px;
            }}
            #toggleBtn:hover {{
                background: {t["toggle_hover_bg"]};
                color: {t["text_secondary"]};
            }}
            #toggleSeparator {{
                background: transparent;
                border: none;
                color: {t["separator"]};
            }}
        """)

        QApplication.instance().setStyleSheet(_app_stylesheet(t))
        self._apply_scrollbar_qss(t)

        self.balance_widget.apply_theme(t)
        self.settings_panel.apply_theme(t)
        self.log_panel.apply_theme(t)
        self.status_bar.apply_theme(t)

    def _apply_scrollbar_qss(self, t):
        qss = _scrollbar_qss(t)
        for s in self.findChildren(QScrollArea):
            s.setStyleSheet(qss)

    def _toggle_theme(self):
        self._dark = not self._dark
        self._theme = DARK if self._dark else LIGHT
        self._apply_theme()
        self.theme_btn.setText("☀ 亮色模式" if self._dark else "🌙 深色模式")
        self.cfg["theme"] = "dark" if self._dark else "light"
        save_config(self.cfg)

    # ── Timer ─────────────────────────────────────────────────
    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_all)
        interval_ms = self.cfg.get("refresh_interval", 30) * 1000
        self.timer.start(interval_ms)

    def _refresh_all(self):
        self.refresh_balance()

    # ── Balance fetch ─────────────────────────────────────────
    def refresh_balance(self):
        if not self.cfg.get("api_key", "").strip():
            self.status_bar.set_status("waiting", "等待配置 API Key")
            return
        if self._worker is not None and self._worker.isRunning():
            return

        self._watchdog_timer.stop()
        self._request_id += 1
        request_id = self._request_id

        self.status_bar.set_status("waiting", "查询中...")

        worker = BalanceWorker(self.cfg)
        self._worker = worker

        def on_finished(result):
            worker.deleteLater()
            if self._request_id == request_id:
                self._on_balance_result(result)

        worker.finished.connect(on_finished)
        worker.start()
        self._watchdog_timer.start(40000)

    def _on_balance_result(self, result):
        try:
            if result.get("success"):
                infos = result.get("balance_infos", [])
                if not infos:
                    self.balance_widget.clear()
                    self.status_bar.set_status("error", "无余额数据")
                else:
                    total = float(infos[0].get("total_balance", 0))
                    if self._last_balance is not None:
                        if total < self._last_balance:
                            self._animator.play_decrease()
                        elif total > self._last_balance:
                            self._animator.play_increase()
                    self._last_balance = total
                    self.balance_widget.set_value(total)
                    status_text = "正常" if result.get("is_available") else "余额不足"
                    status_kind = "normal" if result.get("is_available") else "error"
                    self.status_bar.set_status(status_kind, status_text)
                self.status_bar.touch_time()
                self.logger.info("余额查询成功")
            else:
                err = result.get("error", "未知错误")
                self.status_bar.set_status("error", "错误")
                self.status_bar.touch_time()
                self.logger.error(f"余额查询失败: {err}")
        finally:
            self._watchdog_timer.stop()
            self._worker = None

    # ── Watchdog ─────────────────────────────────────────────
    def _on_watchdog(self):
        self._request_id += 1
        self._worker = None
        self.status_bar.set_status("error", "请求超时")
        self.logger.error("余额查询超时（>40秒），将在下次刷新时自动重试")

    # ── Animation preview ─────────────────────────────────────
    def _preview_decrease(self):
        self._animator.play_decrease()

    def _preview_increase(self):
        self._animator.play_increase()

    # ── Settings save ─────────────────────────────────────────
    def _on_settings_saved(self):
        self.cfg.update(self.settings_panel.get_config())
        self.cfg["theme"] = "dark" if self._dark else "light"
        self._animator.animations_enabled = self.cfg.get("animation_enabled", True)
        self._animator.sound_enabled = self.cfg.get("sound_enabled", True)
        save_config(self.cfg)
        self.timer.stop()
        self.timer.start(self.cfg["refresh_interval"] * 1000)
        self.logger.info(f"设置已保存（刷新间隔: {self.cfg['refresh_interval']} 秒）")
        self._watchdog_timer.stop()
        self.refresh_balance()

    # ── Log callback ──────────────────────────────────────────
    def _on_log(self, message, level):
        self.log_panel.add_log(message, level)

    # ── Cleanup ───────────────────────────────────────────────
    def closeEvent(self, event):
        self.timer.stop()
        self._watchdog_timer.stop()
        super().closeEvent(event)
