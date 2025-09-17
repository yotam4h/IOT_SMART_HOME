# Tank (FoodTank/WaterTank) and Tray (FoodTray/WaterTray) emulators
import sys
import random
from PyQt5 import  QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from .config import *
from .mqtt_client import MqttClient
from datetime import datetime 

import logging
from .config import logs_dir

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(str(logs_dir / 'emulator.log'))
formatter    = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

global clientname, tmp_upd
r=random.randrange(1,10000000)
clientname="IOT_clYT-Id-"+str(r)

class MC(MqttClient):
    def __init__(self):
        super().__init__()
    def on_message(self, client, userdata, msg):
            topic=msg.topic
            m_decode=str(msg.payload.decode("utf-8","ignore"))
            logger.debug("message from %s %s", topic, m_decode)
            try:
                if 'Refill:' in m_decode and ('FoodTank' in mainwin.name or 'WaterTank' in mainwin.name):
                    amount_txt = m_decode.split('Refill:')[1].strip()
                    num = ''.join(ch for ch in amount_txt if ch.isdigit() or ch=='.')
                    if num:
                        amount = float(num)
                        if 'FoodTank' in mainwin.name:
                            mainwin.level = min(Food_capacity_g, mainwin.level + amount)
                        elif 'WaterTank' in mainwin.name:
                            mainwin.level = min(Water_capacity_ml, mainwin.level + amount)
                if 'Dispense:' in m_decode and ('FoodTank' in mainwin.name or 'WaterTank' in mainwin.name):
                    amount_txt = m_decode.split('Dispense:')[1].strip()
                    num = ''.join(ch for ch in amount_txt if ch.isdigit() or ch=='.')
                    if num:
                        amount = float(num)
                        if 'FoodTank' in mainwin.name:
                            mainwin.level = max(0, mainwin.level - amount)
                            mainwin.mc.publish_to(f"{comm_topic}foodtray-1/sub", f"Add: {int(amount)} g")
                        elif 'WaterTank' in mainwin.name:
                            mainwin.level = max(0, mainwin.level - amount)
                            mainwin.mc.publish_to(f"{comm_topic}watertray-1/sub", f"Add: {int(amount)} ml")
                if 'Add:' in m_decode and ('FoodTray' in mainwin.name or 'WaterTray' in mainwin.name):
                    amount_txt = m_decode.split('Add:')[1].strip()
                    num = ''.join(ch for ch in amount_txt if ch.isdigit() or ch=='.')
                    if num:
                        amount = float(num)
                        mainwin.level = mainwin.level + amount
            except Exception:
                logger.exception("Failed to handle refill command")

class ConnectionDock(QDockWidget):
    def __init__(self, mc, name, topic_sub, topic_pub):
        QDockWidget.__init__(self)        
        self.name = name
        self.topic_sub = topic_sub
        self.topic_pub = topic_pub
        self.mc = mc
        self.mc.set_on_connected_callback(self.on_connected)
        self.eHostInput=QLineEdit(); self.eHostInput.setPlaceholderText('hostname or IP'); self.eHostInput.setText(broker_ip)
        self.ePort=QLineEdit(); self.ePort.setValidator(QIntValidator()); self.ePort.setMaxLength(4); self.ePort.setText(broker_port)
        self.eClientID=QLineEdit(); global clientname; self.eClientID.setText(clientname)
        self.eUserName=QLineEdit(); self.eUserName.setText(username)
        self.ePassword=QLineEdit(); self.ePassword.setEchoMode(QLineEdit.Password); self.ePassword.setText(password)
        self.eKeepAlive=QLineEdit(); self.eKeepAlive.setValidator(QIntValidator()); self.eKeepAlive.setText("60")
        self.eSSL=QCheckBox(); self.eCleanSession=QCheckBox(); self.eCleanSession.setChecked(True)
        self.auto_reconnect = True
        self.eConnectbtn=QPushButton("Connect", self)
        self.eConnectbtn.clicked.connect(self.on_button_connect_click)
        self.eConnectbtn.setStyleSheet("background-color: gray")
        self.eDisconnectbtn=QPushButton("Disconnect", self)
        self.eDisconnectbtn.clicked.connect(self.on_button_disconnect_click)
        formLayot=QFormLayout()
        if 'Env' in self.name or 'DHT' in self.name:
            self.ePublisherTopic=QLineEdit(); self.ePublisherTopic.setText(self.topic_pub)
            self.Temperature=QLineEdit(); self.Temperature.setText('')
            self.Humidity=QLineEdit(); self.Humidity.setText('')
            formLayot.addRow("Connect",self.eConnectbtn)
            formLayot.addRow("Disconnect", self.eDisconnectbtn)
            formLayot.addRow("Pub topic",self.ePublisherTopic)
            formLayot.addRow("Temperature",self.Temperature)
            formLayot.addRow("Humidity",self.Humidity)
        elif 'FoodTank' in self.name or 'WaterTank' in self.name or 'FoodTray' in self.name or 'WaterTray' in self.name:
            self.ePublisherTopic=QLineEdit(); self.ePublisherTopic.setText(self.topic_pub)
            self.Level=QLineEdit(); self.Level.setText('')
            formLayot.addRow("Connect",self.eConnectbtn)
            formLayot.addRow("Disconnect", self.eDisconnectbtn)
            formLayot.addRow("Pub topic",self.ePublisherTopic)
            formLayot.addRow("Level",self.Level)
        else:
            self.eSubscribeTopic=QLineEdit(); self.eSubscribeTopic.setText(self.topic_sub)
            self.ePushtbtn=QPushButton("", self); self.ePushtbtn.setToolTip("Push me"); self.ePushtbtn.setStyleSheet("background-color: gray")
            self.Temperature=QLineEdit(); self.Temperature.setText('')
            formLayot.addRow("Connect",self.eConnectbtn)
            formLayot.addRow("Disconnect", self.eDisconnectbtn)
            formLayot.addRow("Sub topic",self.eSubscribeTopic)
            formLayot.addRow("Status",self.ePushtbtn)
        widget = QWidget(self); widget.setLayout(formLayot); self.setTitleBarWidget(widget); self.setWidget(widget); self.setWindowTitle("IOT Emulator")
    def on_connected(self):
        self.eConnectbtn.setStyleSheet("background-color: green")                    
    def on_button_connect_click(self):
        self.auto_reconnect = True
        # set last will for this device
        try:
            self.mc.set_last_will(comm_topic+'alarm', f'{self.name} disconnected')
        except Exception:
            pass
        self.mc.set_broker(self.eHostInput.text()); self.mc.set_port(int(self.ePort.text())); self.mc.set_client_name(self.eClientID.text()); self.mc.set_username(self.eUserName.text()); self.mc.set_password(self.ePassword.text())
        self.mc.connect_to(); self.mc.start_listening()
    def on_button_disconnect_click(self):
        try:
            self.auto_reconnect = False
            # publish alarm before disconnect
            try:
                if self.mc.connected:
                    self.mc.publish_to(comm_topic+'alarm', f'{self.name} disconnected')
            except Exception:
                pass
            self.mc.stop_listening()
            self.mc.disconnect_from()
            self.eConnectbtn.setStyleSheet("background-color: gray")
        except Exception:
            pass

class MainWindow(QMainWindow):    
    def __init__(self, args, parent=None):
        QMainWindow.__init__(self, parent)
        global tmp_upd
        self.name = args[1]; self.units = args[2]
        self.topic_sub = comm_topic+args[3]+'/sub'; self.topic_pub = comm_topic+args[3]+'/pub'
        self.update_rate = args[4]
        self.mc=MC()
        if 'Env' in self.name or 'DHT' in self.name:
            tmp_upd = 22; self.timer = QtCore.QTimer(self); self.timer.timeout.connect(self.create_data); self.timer.start(int(self.update_rate)*1000)
        elif 'FoodTank' in self.name or 'WaterTank' in self.name:
            self.level = Food_capacity_g if 'FoodTank' in self.name else Water_capacity_ml
            self.timer = QtCore.QTimer(self); self.timer.timeout.connect(self.create_data_Level); self.timer.start(int(self.update_rate)*1000)
        elif 'FoodTray' in self.name or 'WaterTray' in self.name:
            self.level = 0; self.timer = QtCore.QTimer(self); self.timer.timeout.connect(self.create_data_Level); self.timer.start(int(self.update_rate)*1000)
        self.setUnifiedTitleAndToolBarOnMac(True); self.setGeometry(30, 600, 300, 150); self.setWindowTitle(self.name)
        self.connectionDock = ConnectionDock(self.mc, self.name, self.topic_sub, self.topic_pub); self.addDockWidget(Qt.TopDockWidgetArea, self.connectionDock)

    def closeEvent(self, event):
        try:
            try: self.timer.stop()
            except Exception: pass
            self.mc.stop_listening(); self.mc.disconnect_from()
        except Exception: pass
        super().closeEvent(event)

    def create_data(self):
        global tmp_upd
        logger.debug('Next update')
        temp=tmp_upd+random.randrange(1,10); hum=74+random.randrange(1,25)
        current_data= f'From: {self.name} Temperature: {temp} Humidity: {hum}'
        self.connectionDock.Temperature.setText(str(temp)); self.connectionDock.Humidity.setText(str(hum))
        if not self.mc.connected:
            if self.connectionDock.auto_reconnect:
                self.connectionDock.on_button_connect_click();
            return
        self.mc.publish_to(self.topic_pub,current_data)

    def create_data_Level(self):
        logger.debug('Level data update')
        if not self.mc.connected:
            if self.connectionDock.auto_reconnect:
                self.connectionDock.on_button_connect_click();
            return
        if not self.mc.subscribed:
            self.mc.subscribe_to(self.topic_sub)
        if 'FoodTank' in self.name:
            unit = ' g'
        elif 'WaterTank' in self.name:
            unit = ' ml'
        elif 'FoodTray' in self.name:
            delta = random.randrange(2, 10); self.level = max(0, self.level - delta); unit = ' g'
        elif 'WaterTray' in self.name:
            delta = random.randrange(10, 40); self.level = max(0, self.level - delta); unit = ' ml'
        else:
            unit = ''
        current_data = f'From: {self.name} Level: {int(self.level)}{unit}'
        try:
            self.connectionDock.Level.setText(str(self.level))
        except Exception:
            pass
        self.mc.publish_to(self.topic_pub, current_data)

if __name__ == '__main__':
    try:    
        app = QApplication(sys.argv)
        try:
            app.setStyleSheet(APP_STYLESHEET)
        except Exception:
            pass
        argv=sys.argv
        if len(sys.argv)==1:
            argv.append('FoodTank-1'); argv.append('g'); argv.append('food-1'); argv.append('5')
        mainwin = MainWindow(argv); mainwin.show(); app.exec_()
    except Exception:
        logger.exception("Crash!")
