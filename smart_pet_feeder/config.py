"""Configuration module with sane, portable defaults.

- Reads env vars where present (no network/DNS resolution required)
- Uses local MQTT by default: 127.0.0.1:1883
- Stores SQLite DB at data/petfeeder.db
"""

import os
import pathlib
import json
import logging
from logging import handlers

# MQTT configuration (override via env vars)
broker_ip = os.getenv('SMARTPETFEEDER_BROKER_HOST', 'broker.hivemq.com')
broker_port = os.getenv('SMARTPETFEEDER_BROKER_PORT', '1883')
username = os.getenv('SMARTPETFEEDER_BROKER_USER', '')
password = os.getenv('SMARTPETFEEDER_BROKER_PASS', '')

# Common
conn_time = 0  # 0 stands for endless loop
comm_topic = os.getenv('SMARTPETFEEDER_TOPIC_PREFIX', 'pr/PetFeeder/')

msg_system = ['normal', 'issue', 'No issue']
wait_time = 5

# FFT module init data
isplot = False
issave = False

# DSP init data
percen_thr = 0.05  # 5% of max energy holds
Fs = 2048.0
deviation_percentage = 10
max_eucl = 0.5

# Acq init data
acqtime = 60.0  # sec
manag_time = 10  # sec

# DB init data
data_dir = pathlib.Path('data')
data_dir.mkdir(parents=True, exist_ok=True)
db_name = os.getenv('SMARTPETFEEDER_DB_PATH', str(data_dir / 'petfeeder.db'))  # SQLite
settings_path = data_dir / 'settings.json'

# Feeder capacities (for emulation and UI)
Food_capacity_g = int(os.getenv('SMARTPETFEEDER_FOOD_CAPACITY_G', '500'))
Water_capacity_ml = int(os.getenv('SMARTPETFEEDER_WATER_CAPACITY_ML', '1000'))
# Tray capacities (smaller than tanks)
Food_tray_capacity_g = int(os.getenv('SMARTPETFEEDER_FOOD_TRAY_CAPACITY_G', '150'))
Water_tray_capacity_ml = int(os.getenv('SMARTPETFEEDER_WATER_TRAY_CAPACITY_ML', '400'))

# Limits (Pet Feeder)
# Portion max defaults to total food capacity; override via env if desired
Portion_max_g = int(os.getenv('SMARTPETFEEDER_PORTION_MAX_G', str(Food_capacity_g)))
# Alert thresholds expressed as percent of capacity (0-100)
Food_min_percent = int(os.getenv('SMARTPETFEEDER_FOOD_MIN_PERCENT', '20'))
Water_min_percent = int(os.getenv('SMARTPETFEEDER_WATER_MIN_PERCENT', '20'))
Food_tray_min_percent = int(os.getenv('SMARTPETFEEDER_FOOD_TRAY_MIN_PERCENT', '20'))
Water_tray_min_percent = int(os.getenv('SMARTPETFEEDER_WATER_TRAY_MIN_PERCENT', '20'))

# Simple, consistent Qt stylesheet for the app
APP_STYLESHEET = """
QMainWindow { background: #FAFAFA; }
QDockWidget::title { background: #1976D2; color: white; padding: 4px; }
QLabel { color: #212121; }
QLineEdit, QTextEdit, QComboBox { padding: 4px; border: 1px solid #BDBDBD; border-radius: 4px; }
QPushButton { background: #E0E0E0; padding: 6px 10px; border: 1px solid #BDBDBD; border-radius: 4px; }
QPushButton:hover { background: #D5D5D5; }
QPushButton:pressed { background: #C8E6C9; }
QToolTip { color: #212121; background-color: #FFFDE7; border: 1px solid #FBC02D; }
"""

# Dark theme stylesheet
DARK_STYLESHEET = """
QMainWindow { background: #121212; }
QDockWidget::title { background: #263238; color: #ECEFF1; padding: 4px; }
QLabel { color: #ECEFF1; }
QLineEdit, QTextEdit, QComboBox { padding: 4px; border: 1px solid #455A64; border-radius: 4px; background: #263238; color: #ECEFF1; }
QPushButton { background: #37474F; color: #ECEFF1; padding: 6px 10px; border: 1px solid #455A64; border-radius: 4px; }
QPushButton:hover { background: #455A64; }
QPushButton:pressed { background: #1B5E20; }
QToolTip { color: #212121; background-color: #FFF59D; border: 1px solid #FBC02D; }
"""

# Settings persistence helpers
def load_settings():
    try:
        if settings_path.exists():
            with open(settings_path, 'r') as f:
                cfg = json.load(f)
            # update known keys if present
            globals().update({
                'Food_capacity_g': int(cfg.get('Food_capacity_g', Food_capacity_g)),
                'Water_capacity_ml': int(cfg.get('Water_capacity_ml', Water_capacity_ml)),
                'Portion_max_g': int(cfg.get('Portion_max_g', Portion_max_g)),
                'Food_min_percent': int(cfg.get('Food_min_percent', Food_min_percent)),
                'Water_min_percent': int(cfg.get('Water_min_percent', Water_min_percent)),
                'Food_tray_capacity_g': int(cfg.get('Food_tray_capacity_g', Food_tray_capacity_g)),
                'Water_tray_capacity_ml': int(cfg.get('Water_tray_capacity_ml', Water_tray_capacity_ml)),
                'Food_tray_min_percent': int(cfg.get('Food_tray_min_percent', Food_tray_min_percent)),
                'Water_tray_min_percent': int(cfg.get('Water_tray_min_percent', Water_tray_min_percent)),
            })
    except Exception:
        # ignore settings load errors
        pass

def save_settings():
    try:
        with open(settings_path, 'w') as f:
            json.dump({
                'Food_capacity_g': int(Food_capacity_g),
                'Water_capacity_ml': int(Water_capacity_ml),
                'Portion_max_g': int(Portion_max_g),
                'Food_min_percent': int(Food_min_percent),
                'Water_min_percent': int(Water_min_percent),
                'Food_tray_capacity_g': int(Food_tray_capacity_g),
                'Water_tray_capacity_ml': int(Water_tray_capacity_ml),
                'Food_tray_min_percent': int(Food_tray_min_percent),
                'Water_tray_min_percent': int(Water_tray_min_percent),
            }, f, indent=2)
    except Exception:
        pass

# Load persisted settings on import
load_settings()

# Logging configuration
LOG_LEVEL = os.getenv('SMARTPETFEEDER_LOG_LEVEL', 'INFO').upper()
logs_dir = pathlib.Path('logs')
logs_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s %(levelname)s %(name)s | %(message)s'
)

# Root file logger capturing everything to logs/app.log (rotating)
_root = logging.getLogger()
if not any(isinstance(h, handlers.RotatingFileHandler) for h in _root.handlers):
    _rfh = handlers.RotatingFileHandler(
        filename=str(logs_dir / 'app.log'), maxBytes=1_000_000, backupCount=3
    )
    _rfh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s | %(message)s'))
    _root.addHandler(_rfh)
