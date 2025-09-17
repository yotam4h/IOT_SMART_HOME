import sys
from PyQt5.QtWidgets import QApplication, QDockWidget, QWidget, QFormLayout, QLineEdit, QPushButton, QMainWindow
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import Qt, QTimer
from .mqtt_client import MqttClient
from .config import broker_ip, broker_port, username, password, comm_topic, logs_dir
import logging
from datetime import datetime


def time_format():
    return f"{datetime.now()}  DeviceEmu|> "


class MC(MqttClient):
    def __init__(self, on_cmd):
        super().__init__()
        self.on_cmd = on_cmd
        self.relay_on = False

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        m_decode = str(msg.payload.decode("utf-8", "ignore"))
        logging.getLogger(__name__).debug("cmd: %s %s", topic, m_decode)
        payload = m_decode.strip(); upper = payload.upper()
        status_payload = None
        if 'SUB' in topic or topic.endswith('/sub'):
            if upper.endswith('ON') or 'RELAY: ON' in upper:
                self.relay_on = True
                status_payload = 'Status: ON'
            elif upper.endswith('OFF') or 'RELAY: OFF' in upper:
                self.relay_on = False
                status_payload = 'Status: OFF'
            elif 'STATUS?' in upper:
                status_payload = f'Status: {"ON" if self.relay_on else "OFF"}'
            if status_payload:
                self.publish_to(feeder_pub(topic), status_payload, retain=True)
                self.on_cmd(status_payload)
                return
        self.on_cmd(m_decode)


def feeder_pub(sub_topic: str) -> str:
    return sub_topic[:-3] + 'pub' if sub_topic.endswith('sub') else sub_topic.replace('/sub', '/pub')


class DeviceDock(QDockWidget):
    def __init__(self, mc: MC, device_name: str):
        super().__init__()
        fh = logging.FileHandler(str(logs_dir / 'device_emulator.log'))
        fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s | %(message)s'))
        logging.getLogger(__name__).addHandler(fh)
        self.device_name = device_name
        self.topic_sub = f"{comm_topic}{device_name}/sub"
        self.topic_pub = f"{comm_topic}{device_name}/pub"
        self.mc = mc
        self.mc.set_on_connected_callback(self.on_connected)

        self.eHostInput = QLineEdit(); self.eHostInput.setPlaceholderText('hostname or IP'); self.eHostInput.setText(broker_ip)
        self.ePort = QLineEdit(); self.ePort.setValidator(QIntValidator()); self.ePort.setMaxLength(5); self.ePort.setText(str(broker_port))
        self.eClientID = QLineEdit(); self.eClientID.setText(f"dev-emu-{device_name}")
        self.eStatus = QLineEdit(); self.eStatus.setText(""); self.eStatus.setReadOnly(True)
        self.auto_reconnect = True
        self.eConnect = QPushButton("Connect", self); self.eConnect.clicked.connect(self.on_connect_click)
        self.eDisconnect = QPushButton("Disconnect", self); self.eDisconnect.clicked.connect(self.on_disconnect_click)
        self.eSubscribe = QPushButton("Subscribe", self); self.eSubscribe.clicked.connect(self.on_subscribe_click)
        self.eOn = QPushButton("ON", self); self.eOn.clicked.connect(lambda: self.mc.publish_to(self.topic_sub, "ON"))
        self.eOff = QPushButton("OFF", self); self.eOff.clicked.connect(lambda: self.mc.publish_to(self.topic_sub, "OFF"))

        form = QFormLayout()
        form.addRow("Host", self.eHostInput)
        form.addRow("Port", self.ePort)
        form.addRow("Connect", self.eConnect)
        form.addRow("Disconnect", self.eDisconnect)
        form.addRow("Subscribe", self.eSubscribe)
        form.addRow("State", self.eStatus)
        form.addRow("Actions", self.wrap_buttons(self.eOn, self.eOff))

        widget = QWidget(self); widget.setLayout(form); self.setTitleBarWidget(widget); self.setWidget(widget)
        self.setWindowTitle(f"Device Emulator: {device_name}")
        QTimer.singleShot(0, self.on_connect_click); QTimer.singleShot(800, self.on_subscribe_click)

    def wrap_buttons(self, *btns):
        w = QWidget(self); l = QFormLayout(); [l.addRow(b) for b in btns]; w.setLayout(l); return w

    def on_connected(self):
        self.eConnect.setStyleSheet("background-color: green"); self.eConnect.setText("Connected")
        # subscribe (may have failed before connect) and publish state snapshot
        QTimer.singleShot(0, lambda: self.ensure_subscribed(force=True))
        try:
            status_payload = f'Status: {"ON" if self.mc.relay_on else "OFF"}'
            self.mc.publish_to(self.topic_pub, status_payload, retain=True)
            self.on_cmd(status_payload)
        except Exception:
            pass

    def on_connect_click(self):
        self.auto_reconnect = True
        try:
            self.mc.set_last_will(comm_topic+'alarm', f'{self.device_name} disconnected')
        except Exception:
            pass
        self.mc.subscribed = False
        self.mc.set_broker(self.eHostInput.text()); self.mc.set_port(int(self.ePort.text())); self.mc.set_client_name(self.eClientID.text())
        self.mc.set_username(username); self.mc.set_password(password); self.mc.connect_to(); self.mc.start_listening()

    def on_disconnect_click(self):
        try:
            self.auto_reconnect = False
            try:
                if self.mc.connected:
                    self.mc.publish_to(comm_topic+'alarm', f'{self.device_name} disconnected')
            except Exception:
                pass
            self.mc.stop_listening(); self.mc.disconnect_from()
            self.eConnect.setStyleSheet("background-color: gray"); self.eConnect.setText("Connect")
            self.eSubscribe.setStyleSheet("")
        except Exception:
            pass

    def on_subscribe_click(self):
        self.ensure_subscribed(force=True)

    def ensure_subscribed(self, force: bool = False):
        if self.mc.subscribed:
            self.eSubscribe.setStyleSheet("background-color: #2196F3; color: white")
            return
        if not self.mc.connected:
            if force:
                QTimer.singleShot(500, lambda: self.ensure_subscribed(force=True))
            return
        self.mc.subscribe_to(self.topic_sub)
        if self.mc.subscribed:
            self.eSubscribe.setStyleSheet("background-color: #2196F3; color: white")
        elif force:
            QTimer.singleShot(500, lambda: self.ensure_subscribed(force=True))

    def publish_status(self, payload: str):
        text = (payload or '').strip()
        retain_flag = text.upper().startswith('STATUS')
        self.mc.publish_to(self.topic_pub, payload, retain=retain_flag)
        self.on_cmd(payload)

    def on_cmd(self, m_decode: str):
        payload = (m_decode or '').strip()
        upper = payload.upper()
        if payload.startswith('Status:') or upper in ('ON', 'OFF', 'STATUS: ON', 'STATUS: OFF'):
            if ':' in payload:
                value = payload.split(':', 1)[1].strip()
            else:
                value = payload
            relay_value = 'UNKNOWN'
            relay_upper = value.upper()
            if 'ON' in relay_upper:
                relay_value = 'ON'
                color = '#4caf50'
            elif 'OFF' in relay_upper:
                relay_value = 'OFF'
                color = '#f44336'
            else:
                color = '#9e9e9e'
            self.eStatus.setText(relay_value)
            if value and value != relay_value:
                self.eStatus.setToolTip(value)
            elif payload and payload != relay_value:
                self.eStatus.setToolTip(payload)
            else:
                self.eStatus.setToolTip('')
            self.eStatus.setStyleSheet(f'color: {color}')
            return
        if "DispenseFood:" in m_decode or "Dispense:" in m_decode:
            try: grams = m_decode.split(":")[1].strip()
            except Exception: grams = "0 g"
            if not grams.lower().endswith('g'): grams = f"{grams} g"
            if self.mc.relay_on:
                self.mc.publish_to(f"{comm_topic}food-1/sub", f"Dispense: {grams}"); self.publish_status(f"Dispensed: {grams}")
            else:
                self.publish_status("Status: OFF - blocked")
            self.eStatus.setToolTip(payload or grams)
        elif "DispenseWater:" in m_decode:
            try: ml = m_decode.split(":")[1].strip()
            except Exception: ml = "0 ml"
            if not ml.lower().endswith('ml'): ml = f"{ml} ml"
            if self.mc.relay_on:
                self.mc.publish_to(f"{comm_topic}water-1/sub", f"Dispense: {ml}"); self.publish_status(f"Dispensed: {ml}")
            else:
                self.publish_status("Status: OFF - blocked")
            self.eStatus.setToolTip(payload or ml)
        else:
            # keep tooltip with last non-status payload for quick inspection
            if payload:
                self.eStatus.setToolTip(payload)


class Main(QMainWindow):
    def __init__(self, device_name: str):
        super().__init__()
        self.setGeometry(100, 100, 300, 150); self.setWindowTitle(f"Device Emulator: {device_name}")
        mc = MC(on_cmd=self.on_cmd); self.dock = DeviceDock(mc, device_name); self.addDockWidget(Qt.TopDockWidgetArea, self.dock)

    def on_cmd(self, payload: str):
        self.dock.on_cmd(payload)

    def closeEvent(self, event):
        try:
            self.dock.mc.stop_listening(); self.dock.mc.disconnect_from()
        except Exception: pass
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        from .config import APP_STYLESHEET
        app.setStyleSheet(APP_STYLESHEET)
    except Exception:
        pass
    device = sys.argv[1] if len(sys.argv) > 1 else 'feeder'
    w = Main(device); w.show(); app.exec_()
