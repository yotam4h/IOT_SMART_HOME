import os
#from sqlite3.dbapi2 import Date
import sys
import random
import re
# pip install pyqt5-tools
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from matplotlib.pyplot import get
BASE_PATH = os.path.abspath(os.path.dirname(__file__))
from .config import *
from .mqtt_client import MqttClient 
import time
from datetime import datetime 
from . import data_acq as da
# pip install pyqtgraph
#from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

import logging
from .config import logs_dir

# Gets or creates a logger
logger = logging.getLogger(__name__)  

# set log level
logger.setLevel(logging.INFO)

# define file handler and set formatter
file_handler = logging.FileHandler(str(logs_dir / 'gui.log'))
formatter    = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
file_handler.setFormatter(formatter)

# add file handler to logger
logger.addHandler(file_handler)

# Logs
# logger.debug('A debug message')
# logger.info('An info message')
# logger.warning('Something is not right.')
# logger.error('A Major error has happened.')
# logger.critical('Fatal error. Cannot continue')

# Also capture unhandled exceptions to the GUI log
def _gui_excepthook(exc_type, exc_value, exc_tb):
    try:
        logger.exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    except Exception:
        pass
sys.excepthook = _gui_excepthook


def time_format():
    return f'{datetime.now()}  GUI|> '
# Creating Client name - should be unique 
global clientname
r=random.randrange(1,10000) # for creating unique client ID
clientname="IOT_clientId-nXLMZeDcjH"+str(r)

def check(fnk):
    try:
        return fnk
    except Exception:
        return 'NA'

class MC(MqttClient):
    def __init__(self, mainwin):
        super().__init__()
        self.mainwin = mainwin
        self.last_relay_status = None
    def on_message(self, client, userdata, msg):
            topic=msg.topic            
            m_decode=str(msg.payload.decode("utf-8","ignore"))
            logger.debug("message from %s %s", topic, m_decode)
            # Handle incoming sensor updates
            # Pet feeder: update Food/Water levels into existing fields
            if 'FoodTank' in topic or 'FoodTank' in m_decode:
                try:
                    val = m_decode.split('Level:')[1].strip()
                    level = val if val.endswith('g') else f"{val} g"
                except Exception:
                    level = ''
                self.mainwin.graphsDock.update_electricity_meter(level)
            if 'WaterTank' in topic or 'WaterTank' in m_decode:
                try:
                    val = m_decode.split('Level:')[1].strip()
                    level = val if val.lower().endswith('ml') else f"{val} ml"
                except Exception:
                    level = ''
                self.mainwin.graphsDock.update_water_meter(level)
            if 'FoodTray' in topic or 'FoodTray' in m_decode:
                try:
                    val = m_decode.split('Level:')[1].strip()
                    level = val if val.endswith('g') else f"{val} g"
                except Exception:
                    level = ''
                self.mainwin.graphsDock.update_electricity_meter(level)
            if 'WaterTray' in topic or 'WaterTray' in m_decode:
                try:
                    val = m_decode.split('Level:')[1].strip()
                    level = val if val.lower().endswith('ml') else f"{val} ml"
                except Exception:
                    level = ''
                self.mainwin.graphsDock.update_water_meter(level)
            if 'Dispensed:' in m_decode:
                try:
                    grams = m_decode.split('Dispensed:')[1].strip()
                except Exception:
                    grams = m_decode
                self.mainwin.recentDock.add_dispense(f"{da.timestamp()} - {grams}")
            try:
                text = m_decode.strip()
                status_txt = None
                topic_match = isinstance(topic, str) and 'feeder' in topic.lower()
                if text:
                    match = re.search(r'status\s*[:=]\s*([^\r\n]+)', text, re.IGNORECASE)
                    if match:
                        status_txt = match.group(1).strip()
                    elif text.upper() in ('ON', 'OFF'):
                        status_txt = text
                    elif 'RELAY' in text.upper() and any(word in text.upper() for word in (' ON', ' OFF', 'UNKNOWN')):
                        # handle payloads like "Relay ON" or "Relay OFF"
                        relay_words = re.findall(r'(ON|OFF|UNKNOWN)', text, flags=re.IGNORECASE)
                        if relay_words:
                            status_txt = relay_words[-1]
                if status_txt and (topic_match or 'STATUS' in text.upper() or 'RELAY' in text.upper()):
                    self.last_relay_status = status_txt
                    # relayDock may not exist yet at very early connect
                    try:
                        self.mainwin.relayDock.update_status(status_txt)
                    except Exception:
                        pass
            except Exception:
                logger.exception('Failed to process relay status message')
            if 'alarm' in topic:            
                self.mainwin.statusDock.update_mess_win(da.timestamp()+': ' + m_decode)
            


   
class ConnectionDock(QDockWidget):
    """Main """
    def __init__(self,mc):
        QDockWidget.__init__(self)        
        self.mc = mc
        self.topic = comm_topic+'#'        
        self.mc.set_on_connected_callback(self.on_connected)        
        self.eHostInput=QLineEdit()
        # Allow hostname or IP entry
        self.eHostInput.setPlaceholderText('hostname or IP')
        self.eHostInput.setText(broker_ip)        
        self.ePort=QLineEdit()
        self.ePort.setValidator(QIntValidator())
        self.ePort.setMaxLength(4)
        self.ePort.setText(broker_port)        
        self.eClientID=QLineEdit()
        global clientname
        self.eClientID.setText(clientname)        
        self.eConnectButton=QPushButton("Connect", self)
        self.eConnectButton.setToolTip("click me to connect")
        self.eConnectButton.clicked.connect(self.on_button_connect_click)
        self.eConnectButton.setStyleSheet("background-color: red")        
        formLayot=QFormLayout()
        formLayot.addRow("Host",self.eHostInput )
        formLayot.addRow("Port",self.ePort )        
        formLayot.addRow("",self.eConnectButton)
        widget = QWidget(self)
        widget.setLayout(formLayot)
        self.setTitleBarWidget(widget)
        self.setWidget(widget)     
        self.setWindowTitle("Connect") 
        
    def on_connected(self):
        self.eConnectButton.setStyleSheet("background-color: green")
        self.eConnectButton.setText('Connected')
            
    def on_button_connect_click(self):
        self.mc.set_broker(self.eHostInput.text())
        self.mc.set_port(int(self.ePort.text()))
        self.mc.set_client_name(self.eClientID.text())           
        self.mc.connect_to()        
        self.mc.start_listening()
        time.sleep(1)
        if not self.mc.subscribed:
            self.mc.subscribe_to(self.topic)
            
class StatusDock(QDockWidget):
    """Status"""
    def __init__(self, mc):
        QDockWidget.__init__(self)
        self.mc = mc
        self.eRecMess = QTextEdit(); self.eRecMess.setReadOnly(True)
        formLayot = QFormLayout()
        formLayot.addRow("Alarm Messages:", self.eRecMess)
        widget = QWidget(self)
        widget.setLayout(formLayot)
        self.setTitleBarWidget(widget)
        self.setWidget(widget)
        self.setWindowTitle("Status")
        self._history_limit = 50
        self.load_history()

    def update_mess_win(self, text):
        self.eRecMess.append(text)

    def load_history(self):
        try:
            df = da.fetch_data(db_name, 'data', 'Alarm')
        except Exception as e:
            logger.debug('No alarm history available yet: %s', e)
            return
        if df.empty or 'timestamp' not in df.columns or 'value' not in df.columns:
            return
        subset = df.tail(self._history_limit)
        for ts, message in subset[['timestamp', 'value']].itertuples(index=False):
            display = f"{ts}: {message}" if ts else str(message)
            self.update_mess_win(display)
        
class GraphsDock(QDockWidget):
    """Graphs """
    def __init__(self, mc, mainwin):
        QDockWidget.__init__(self)        
        self.mc = mc
        self.mainwin = mainwin
        self.eElectricityButton = QPushButton("Show",self)
        self.eElectricityButton.clicked.connect(self.on_button_Elec_click)        
        self.eWaterButton = QPushButton("Show",self)
        self.eWaterButton.clicked.connect(self.on_button_water_click)        
        self.viewSelect = QComboBox(); self.viewSelect.addItems(['Tank', 'Tray'])
        # No date range controls; graphs show entire history
        formLayot=QFormLayout()       
        formLayot.addRow("Food (g)", self.eElectricityButton)
        formLayot.addRow("Water (ml)", self.eWaterButton)
        formLayot.addRow("View:", self.viewSelect)
        # (date range fields removed)
        widget = QWidget(self)
        widget.setLayout(formLayot)
        self.setWidget(widget)
        self.setWindowTitle("Graphs")
        # internal thresholds (percent), initialized from config
        self.food_min = Food_min_percent
        self.water_min = Water_min_percent
        # last plotted meter for auto-refresh
        self.last_meter = 'FoodTank'
        # auto-refresh timer (2s)
        self.refreshTimer = QTimer(self)
        self.refreshTimer.setInterval(2000)
        self.refreshTimer.timeout.connect(self._on_refresh_timer)
        self.refreshTimer.start()

    def update_water_meter(self, text):
        # text-field removed; keep method for compatibility
        return

    def update_electricity_meter(self, text):
        # text-field removed; keep method for compatibility
        return

    def on_button_water_click(self):
        try:
            meter = 'WaterTray' if self.viewSelect.currentText() == 'Tray' else 'WaterTank'
            self.update_plot(meter)
            self.eWaterButton.setStyleSheet("background-color: #2196F3; color: white")
            self.last_meter = meter
        except Exception as e:
            logger.exception("Failed to update WaterLevel plot")
            QMessageBox.critical(self, "Plot Error", f"Failed to update Water plot:\n{e}")

    def on_button_Elec_click(self):
        try:
            meter = 'FoodTray' if self.viewSelect.currentText() == 'Tray' else 'FoodTank'
            self.update_plot(meter)
            self.eElectricityButton.setStyleSheet("background-color: #2196F3; color: white")
            self.last_meter = meter
        except Exception as e:
            logger.exception("Failed to update FoodLevel plot")
            QMessageBox.critical(self, "Plot Error", f"Failed to update Food plot:\n{e}")

    def update_plot(self, meter):
        try:
            df = da.fetch_data(db_name, 'data', meter)
            timenow = list(df['timestamp']) if 'timestamp' in df.columns else []
            values = []
            for v in df['value'] if 'value' in df.columns else []:
                try:
                    values.append(float("{:.2f}".format(float(v))))
                except Exception:
                    pass
            self.mainwin.plotsDock.plot(timenow, values, meter)
        except Exception as e:
            logger.exception("Failed to fetch data for plot: %s", e)

    def _on_refresh_timer(self):
        try:
            self.update_plot(self.last_meter)
        except Exception:
            # ignore refresh errors; already logged in update_plot
            pass


class FeederDock(QDockWidget):
    """Feeder Control"""
    def __init__(self, mc):
        QDockWidget.__init__(self)
        self.mc = mc
        self.topic_sub = comm_topic+'feeder/sub'
        self.topic_pub = comm_topic+'feeder/pub'

        self.portionFood = QLineEdit()
        self.portionFood.setValidator(QIntValidator())
        self.portionFood.setText("50")  # grams
        self.portionWater = QLineEdit()
        self.portionWater.setValidator(QIntValidator())
        self.portionWater.setText("100")  # ml
        self.dispenseFoodBtn = QPushButton("Dispense Food", self)
        self.dispenseFoodBtn.clicked.connect(self.on_dispense_food)
        self.dispenseWaterBtn = QPushButton("Dispense Water", self)
        self.dispenseWaterBtn.clicked.connect(self.on_dispense_water)

        formLayot = QFormLayout()
        formLayot.addRow("Food portion (g)", self.portionFood)
        formLayot.addRow("", self.dispenseFoodBtn)
        formLayot.addRow("Water portion (ml)", self.portionWater)
        formLayot.addRow("", self.dispenseWaterBtn)
        widget = QWidget(self)
        widget.setLayout(formLayot)
        self.setWidget(widget)
        self.setWindowTitle("Feeder")

    def on_dispense_food(self):
        grams = self.portionFood.text().strip() or "0"
        self.mc.publish_to(self.topic_sub, f"DispenseFood: {grams} g")
        self.dispenseFoodBtn.setStyleSheet("background-color: #4caf50; color: white")

    def on_dispense_water(self):
        ml = self.portionWater.text().strip() or "0"
        self.mc.publish_to(self.topic_sub, f"DispenseWater: {ml} ml")
        self.dispenseWaterBtn.setStyleSheet("background-color: #4caf50; color: white")

class RefillDock(QDockWidget):
    """Refill Controls"""
    def __init__(self, mc):
        QDockWidget.__init__(self)
        self.mc = mc
        self.foodTopic = comm_topic + 'food-1/sub'
        self.waterTopic = comm_topic + 'water-1/sub'

        self.foodAmt = QLineEdit(); self.foodAmt.setValidator(QIntValidator()); self.foodAmt.setText('200')
        self.btnFood = QPushButton('Add Food (g)')
        self.btnFood.clicked.connect(self.on_add_food)
        self.waterAmt = QLineEdit(); self.waterAmt.setValidator(QIntValidator()); self.waterAmt.setText('300')
        self.btnWater = QPushButton('Add Water (ml)')
        self.btnWater.clicked.connect(self.on_add_water)

        form = QFormLayout()
        form.addRow('Food amount', self.foodAmt)
        form.addRow('', self.btnFood)
        form.addRow('Water amount', self.waterAmt)
        form.addRow('', self.btnWater)
        widget = QWidget(self)
        widget.setLayout(form)
        self.setWidget(widget)
        self.setWindowTitle('Refill')

    def on_add_food(self):
        amt = self.foodAmt.text().strip() or '0'
        self.mc.publish_to(self.foodTopic, f'Refill: {amt} g')
        self.btnFood.setStyleSheet('background-color: #4caf50; color: white')

    def on_add_water(self):
        amt = self.waterAmt.text().strip() or '0'
        self.mc.publish_to(self.waterTopic, f'Refill: {amt} ml')
        self.btnWater.setStyleSheet('background-color: #4caf50; color: white')

class PlotDock(QDockWidget):
    """Plots """
    def __init__(self):
        QDockWidget.__init__(self)        
        self.setWindowTitle("Plots")
        self.graphWidget = pg.PlotWidget()
        self.setWidget(self.graphWidget)
        # initialize plot thresholds from config so plot() can use them
        self.food_min = Food_min_percent
        self.water_min = Water_min_percent
        # Try to fetch initial FoodLevel data; handle missing DB/table gracefully
        datal = []
        timel = []
        try:
            rez = da.filter_by_date('data','2000-01-01','2100-01-01', 'FoodTank')
            for row in rez:
                timel.append(row[1])
                datal.append(float("{:.2f}".format(float(row[2]))))
        except Exception:
            pass
        self.graphWidget.setBackground('w')
        # Add Title
        self.graphWidget.setTitle("Levels Timeline", color="w", size="15pt")
        # Add Axis Labels
        styles = {"color": "#000", "font-size": "14px"}
        self.graphWidget.setLabel("left", "Level (units)", **styles)
        self.graphWidget.setLabel("bottom", "Samples", **styles)
        #Add legend
        self.graphWidget.addLegend()
        #Add grid
        self.graphWidget.showGrid(x=True, y=True)
        #Set Range
        #self.graphWidget.setXRange(0, 10, padding=0)
        #self.graphWidget.setYRange(20, 55, padding=0)            
        pen = pg.mkPen(color=(33, 150, 243), width=2)
        self.data_line=self.graphWidget.plot( datal,  pen=pen)
        # add initial scatter with tooltips using FoodLevel threshold
        self.scatter = None
        self.plot(timel, datal, 'FoodLevel')
    def plot(self, timel, datal, meter):
        # Update line and scatter with color-coding and tooltips
        self.graphWidget.clear()
        pen = pg.mkPen(color=(33, 150, 243), width=2)
        self.data_line = self.graphWidget.plot(datal, pen=pen, name=meter)
        # threshold based coloring
        thr = None
        if meter == 'FoodLevel':
            thr = self.food_min
        elif meter == 'WaterLevel':
            thr = self.water_min
        elif meter == 'FoodTray':
            thr = getattr(self, 'food_tray_min', Food_tray_min_percent)
        elif meter == 'WaterTray':
            thr = getattr(self, 'water_tray_min', Water_tray_min_percent)
        spots = []
        for i, v in enumerate(datal):
            color = (244, 67, 54) if (thr is not None and v < thr) else (76, 175, 80)
            spots.append({
                'pos': (i, v),
                'brush': pg.mkBrush(color),
                'pen': pg.mkPen('w'),
                'size': 8,
                'symbol': 'o',
                'data': {'ts': timel[i], 'value': v, 'meter': meter},
            })
        self.scatter = pg.ScatterPlotItem(spots=spots)
        # Enable simple hover highlighting if available in this pyqtgraph version
        # hover optional
        try:
            self.scatter.setHoverable(True, hoverBrush=pg.mkBrush(255, 235, 59), hoverPen=pg.mkPen('k'))
        except Exception:
            pass
        self.graphWidget.addItem(self.scatter)

class RecentDispensesDock(QDockWidget):
    """Recent dispenses list"""
    def __init__(self):
        QDockWidget.__init__(self)
        self.setWindowTitle("Recent Dispenses")
        self.list = QListWidget()
        widget = QWidget(self)
        layout = QVBoxLayout()
        layout.addWidget(self.list)
        widget.setLayout(layout)
        self.setWidget(widget)
        self.max_items = 20
        self.load_recent()

    def add_dispense(self, text: str):
        self.list.insertItem(0, text)
        # trim to max_items
        while self.list.count() > self.max_items:
            self.list.takeItem(self.list.count() - 1)

    def load_recent(self):
        try:
            df = da.fetch_data(db_name, 'data', 'MealsDispensed')
        except Exception as e:
            logger.debug('No dispense history available yet: %s', e)
            return
        if df.empty or 'timestamp' not in df.columns or 'value' not in df.columns:
            return
        subset = df.tail(self.max_items)
        for ts, value in subset[['timestamp', 'value']].itertuples(index=False):
            amount = str(value).strip()
            if not amount or amount.lower() == 'nan':
                continue
            normalized = amount.lower()
            if amount and not normalized.endswith(('g', 'ml')):
                try:
                    float(amount)
                except Exception:
                    pass
                else:
                    amount = f"{amount} g"
            display = f"{ts} - {amount}" if ts else amount
            self.list.addItem(display)

class RelayDock(QDockWidget):
    """Relay ON/OFF control and status"""
    def __init__(self, mc):
        QDockWidget.__init__(self)
        self.mc = mc
        self.topic_sub = comm_topic+'feeder/sub'
        self.topic_pub = comm_topic+'feeder/pub'
        self.status = QLineEdit(); self.status.setReadOnly(True); self.status.setText('UNKNOWN')
        self.onBtn = QPushButton('Relay ON'); self.onBtn.clicked.connect(lambda: self.mc.publish_to(self.topic_sub, 'ON'))
        self.offBtn = QPushButton('Relay OFF'); self.offBtn.clicked.connect(lambda: self.mc.publish_to(self.topic_sub, 'OFF'))
        form = QFormLayout(); form.addRow('Status', self.status); form.addRow('', self.onBtn); form.addRow('', self.offBtn)
        widget = QWidget(self); widget.setLayout(form); self.setWidget(widget); self.setWindowTitle('Relay')
        # If we already received a status before dock creation, reflect it
        try:
            if getattr(self.mc, 'last_relay_status', None):
                self.update_status(self.mc.last_relay_status)
        except Exception:
            pass

    def update_status(self, text: str):
        payload = text or 'UNKNOWN'
        logger.info('RelayDock update_status request: %s', payload)
        if QThread.currentThread() != self.thread():
            try:
                QMetaObject.invokeMethod(
                    self,
                    '_apply_status',
                    Qt.QueuedConnection,
                    Q_ARG(str, payload),
                )
            except Exception:
                QTimer.singleShot(0, lambda p=payload: self._apply_status(p))
        else:
            self._apply_status(payload)

    @pyqtSlot(str)
    def _apply_status(self, text: str):
        payload = text or 'UNKNOWN'
        logger.info('RelayDock applying status: %s', payload)
        self.status.setText(payload)
        upper = payload.upper()
        if 'ON' in upper:
            color = '#4caf50'
        elif 'UNKNOWN' in upper:
            color = '#9e9e9e'
        else:
            color = '#f44336'
        self.status.setStyleSheet(f'color: {color}')


class SettingsDock(QDockWidget):
    """Runtime Settings for thresholds/capacities and theme"""
    def __init__(self, mc, mainwin):
        QDockWidget.__init__(self)
        self.mc = mc
        self.mainwin = mainwin
        self.setWindowTitle('Settings')
        self.foodCap = QLineEdit(str(Food_capacity_g)); self.foodCap.setValidator(QIntValidator())
        self.waterCap = QLineEdit(str(Water_capacity_ml)); self.waterCap.setValidator(QIntValidator())
        self.foodTrayCap = QLineEdit(str(Food_tray_capacity_g)); self.foodTrayCap.setValidator(QIntValidator())
        self.waterTrayCap = QLineEdit(str(Water_tray_capacity_ml)); self.waterTrayCap.setValidator(QIntValidator())
        self.foodMin = QLineEdit(str(Food_min_percent)); self.foodMin.setValidator(QIntValidator())
        self.waterMin = QLineEdit(str(Water_min_percent)); self.waterMin.setValidator(QIntValidator())
        self.foodTrayMin = QLineEdit(str(Food_tray_min_percent)); self.foodTrayMin.setValidator(QIntValidator())
        self.waterTrayMin = QLineEdit(str(Water_tray_min_percent)); self.waterTrayMin.setValidator(QIntValidator())
        self.portionMax = QLineEdit(str(Portion_max_g)); self.portionMax.setValidator(QIntValidator())
        self.btnApply = QPushButton('Apply (send to Manager)')
        self.btnApply.clicked.connect(self.on_apply)
        self.btnTheme = QPushButton('Toggle Dark Mode')
        self.btnTheme.clicked.connect(self.on_toggle_theme)
        form = QFormLayout()
        form.addRow('Food capacity (g)', self.foodCap)
        form.addRow('Water capacity (ml)', self.waterCap)
        form.addRow('Food min (%)', self.foodMin)
        form.addRow('Food tray capacity (g)', self.foodTrayCap)
        form.addRow('Food tray min (%)', self.foodTrayMin)
        form.addRow('Water min (%)', self.waterMin)
        form.addRow('Water tray capacity (ml)', self.waterTrayCap)
        form.addRow('Water tray min (%)', self.waterTrayMin)
        form.addRow('Portion max (g)', self.portionMax)
        form.addRow('', self.btnApply)
        form.addRow('', self.btnTheme)
        widget = QWidget(self)
        widget.setLayout(form)
        self.setWidget(widget)

    def on_apply(self):
        # publish config update to manager
        cfg = {
            'Food_capacity_g': self.foodCap.text().strip(),
            'Water_capacity_ml': self.waterCap.text().strip(),
            'Food_min_percent': self.foodMin.text().strip(),
            'Water_min_percent': self.waterMin.text().strip(),
            'Portion_max_g': self.portionMax.text().strip(),
            'Food_tray_capacity_g': self.foodTrayCap.text().strip(),
            'Water_tray_capacity_ml': self.waterTrayCap.text().strip(),
            'Food_tray_min_percent': self.foodTrayMin.text().strip(),
            'Water_tray_min_percent': self.waterTrayMin.text().strip(),
        }
        # update local plot thresholds immediately
        try:
            self.mainwin.plotsDock.food_min = int(float(cfg['Food_min_percent'] or 0))
            self.mainwin.plotsDock.water_min = int(float(cfg['Water_min_percent'] or 0))
            self.mainwin.plotsDock.food_tray_min = int(float(cfg['Food_tray_min_percent'] or 0)) if cfg.get('Food_tray_min_percent') else getattr(self.mainwin.plotsDock, 'food_tray_min', Food_tray_min_percent)
            self.mainwin.plotsDock.water_tray_min = int(float(cfg['Water_tray_min_percent'] or 0)) if cfg.get('Water_tray_min_percent') else getattr(self.mainwin.plotsDock, 'water_tray_min', Water_tray_min_percent)
        except Exception:
            pass
        msg = 'Config: ' + ', '.join([f"{k}={v}" for k, v in cfg.items() if v])
        self.mc.publish_to(comm_topic + 'config', msg)
        self.btnApply.setStyleSheet('background-color: #4caf50; color: white')

    def on_toggle_theme(self):
        try:
            cur = self.mainwin.styleSheet()
            if not cur or cur == APP_STYLESHEET:
                self.mainwin.parent().setStyleSheet(DARK_STYLESHEET)
            else:
                self.mainwin.parent().setStyleSheet(APP_STYLESHEET)
        except Exception:
            # fallback to app instance
            app = QApplication.instance()
            if app:
                if app.styleSheet() == DARK_STYLESHEET:
                    app.setStyleSheet(APP_STYLESHEET)
                else:
                    app.setStyleSheet(DARK_STYLESHEET)



class MainWindow(QMainWindow):    
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)                
        # Init of Mqtt_client class
        # self.mc=Mqtt_client()
        self.mc=MC(self)        
        # general GUI settings
        self.setUnifiedTitleAndToolBarOnMac(True)
        # set up main window
        self.setGeometry(30, 100, 1200, 700)
        self.setWindowTitle('Smart Pet Feeder GUI')
        # Init QDockWidget objects        
        self.connectionDock = ConnectionDock(self.mc)        
        self.statusDock = StatusDock(self.mc)
        self.feederDock = FeederDock(self.mc)
        self.graphsDock = GraphsDock(self.mc, self)
        self.plotsDock = PlotDock()
        self.recentDock = RecentDispensesDock()
        self.refillDock = RefillDock(self.mc)
        self.relayDock = RelayDock(self.mc)
        self.settingsDock = SettingsDock(self.mc, self)
        self.addDockWidget(Qt.TopDockWidgetArea, self.connectionDock)
        self.addDockWidget(Qt.TopDockWidgetArea, self.feederDock)
        self.addDockWidget(Qt.TopDockWidgetArea, self.refillDock)
        self.addDockWidget(Qt.TopDockWidgetArea, self.settingsDock)
        self.addDockWidget(Qt.TopDockWidgetArea, self.relayDock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.statusDock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.graphsDock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.plotsDock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.recentDock)
        # Auto connect GUI client and subscribe to alarms (already subscribing to '#')
        QTimer.singleShot(0, self.connectionDock.on_button_connect_click)
        # Poll feeder relay status until received
        self._relay_status_poll_tries = 0
        def _ask_status():
            try:
                if self.mc.connected:
                    self.mc.publish_to(comm_topic+'feeder/sub', 'STATUS?')
                    # stop polling if we already have a status
                    if getattr(self.mc, 'last_relay_status', None):
                        return
                if self._relay_status_poll_tries < 5:
                    self._relay_status_poll_tries += 1
                    QTimer.singleShot(1000, _ask_status)
            except Exception:
                if self._relay_status_poll_tries < 5:
                    self._relay_status_poll_tries += 1
                    QTimer.singleShot(1000, _ask_status)
        QTimer.singleShot(1500, _ask_status)

    def closeEvent(self, event):
        try:
            self.mc.stop_listening()
            self.mc.disconnect_from()
        except Exception:
            pass
        super().closeEvent(event)

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        # Apply global stylesheet
        try:
            app.setStyleSheet(APP_STYLESHEET)
        except Exception:
            pass
        mainwin = MainWindow()
        mainwin.show()
        app.exec_()

    except Exception:
        logger.exception("GUI Crash!")
