"""Manager for Smart Pet Feeder
Collects MQTT messages, stores to SQLite, and emits alarms.
"""

import paho.mqtt.client as mqtt
import time
import random
import logging
from .config import *
from .config import logs_dir
from . import config as cfg
import socket

# module-specific logging to file
_fh = logging.FileHandler(str(logs_dir / 'manager.log'))
_fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s | %(message)s'))
logging.getLogger(__name__).addHandler(_fh)
from . import data_acq as da

# Define callback functions
def on_log(client, userdata, level, buf):
        logging.getLogger(__name__).debug("log: %s", buf)
            
def on_connect(client, userdata, flags, rc):    
    if rc==0:
        logging.getLogger(__name__).info("connected OK")
    else:
        logging.getLogger(__name__).error("Bad connection Returned code=%s", rc)
        
def on_disconnect(client, userdata, flags, rc=0):    
    logging.getLogger(__name__).info("Disconnected result code %s", rc)
        
def on_message(client, userdata, msg):
    topic=msg.topic
    m_decode=str(msg.payload.decode("utf-8","ignore"))
    logging.getLogger(__name__).debug("message from %s %s", topic, m_decode)
    # Runtime config updates via MQTT
    try:
        if topic == comm_topic + 'config' or m_decode.startswith('Config:'):
            payload = m_decode.replace('Config:', '').strip()
            for pair in payload.split(','):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    k = k.strip(); v = v.strip()
                    if k in (
                        'Food_min_percent', 'Water_min_percent', 'Portion_max_g',
                        'Food_capacity_g', 'Water_capacity_ml',
                        'Food_tray_capacity_g', 'Water_tray_capacity_ml',
                        'Food_tray_min_percent', 'Water_tray_min_percent',
                    ):
                        _update_config_value(k, v)
            return
    except Exception as e:
        logging.getLogger(__name__).exception("Failed to process config: %s", e)
    insert_DB(topic, m_decode)

def send_msg(client, topic, message):
    logging.getLogger(__name__).info("Sending message: %s", message)
    #tnow=time.localtime(time.time())
    client.publish(topic,message)   

def client_init(cname):
    r=random.randrange(1,10000000)
    ID=str(cname+str(r+21))
    client = mqtt.Client(
        client_id=ID,
        clean_session=True,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
    )  # create new client instance compatible with paho-mqtt v2
    try:
        client.enable_logger(logging.getLogger('paho.mqtt.client'))
    except Exception:
        pass
    # define callback function       
    client.on_connect=on_connect  #bind callback function
    client.on_disconnect=on_disconnect
    client.on_log=on_log
    client.on_message=on_message        
    if username !="":
        client.username_pw_set(username, password)        
    logging.getLogger(__name__).info("Connecting to broker %s", broker_ip)
    client.connect(broker_ip, int(broker_port))     #connect to broker
    return client

def insert_DB(topic, m_decode):
    if 'alarm' in topic.lower():
        try:
            da.add_IOT_data('Alarm', da.timestamp(), m_decode)
        except Exception:
            logging.getLogger(__name__).exception("Failed to store alarm message")
        return
    # Env sensor: 'From: Env-1 Temperature: X Humidity: Y'
    if 'Temperature:' in m_decode and 'Humidity:' in m_decode:
        try:
            name = m_decode.split('From: ')[1].split(' Temperature: ')[0]
            value = m_decode.split(' Temperature: ')[1].split(' Humidity: ')[0]
        except Exception:
            name, value = 'Env', 'NA'
        if value != 'NA':
            da.add_IOT_data(name, da.timestamp(), value)
    # Food tank: 'From: FoodTank-1 Level: X g'
    elif 'FoodTank' in m_decode and 'Level:' in m_decode:
        try:
            value = m_decode.split('Level:')[1]
            for token in ['%', 'g', 'G', 'ml', 'ML', 'mL']:
                value = value.replace(token, '')
            value = value.strip()
        except Exception:
            value = 'NA'
        if value != 'NA':
            da.add_IOT_data('FoodTank', da.timestamp(), value)
    # Water tank: 'From: WaterTank-1 Level: X ml'
    elif 'WaterTank' in m_decode and 'Level:' in m_decode:
        try:
            value = m_decode.split('Level:')[1]
            for token in ['%', 'g', 'G', 'ml', 'ML', 'mL']:
                value = value.replace(token, '')
            value = value.strip()
        except Exception:
            value = 'NA'
        if value != 'NA':
            da.add_IOT_data('WaterTank', da.timestamp(), value)
    # Feeder dispensed: 'Dispensed: X g/ml'
    elif 'Dispensed:' in m_decode:
        try:
            grams = m_decode.split('Dispensed:')[1].strip().replace('g','').replace('G','').strip()
        except Exception:
            grams = '0'
        da.add_IOT_data('MealsDispensed', da.timestamp(), grams)
    # FoodTray level
    elif 'FoodTray' in m_decode and 'Level:' in m_decode:
        try:
            value = m_decode.split('Level:')[1]
            for token in ['%', 'g', 'G']:
                value = value.replace(token, '')
            value = value.strip()
        except Exception:
            value = 'NA'
        if value != 'NA':
            da.add_IOT_data('FoodTray', da.timestamp(), value)
    # WaterTray level
    elif 'WaterTray' in m_decode and 'Level:' in m_decode:
        try:
            value = m_decode.split('Level:')[1]
            for token in ['%', 'ml', 'ML', 'mL']:
                value = value.replace(token, '')
            value = value.strip()
        except Exception:
            value = 'NA'
        if value != 'NA':
            da.add_IOT_data('WaterTray', da.timestamp(), value)

def parse_data(m_decode):
    try:
        return m_decode.split(' Temperature: ')[1].split(' Humidity: ')[0]
    except Exception:
        return 'NA'

def enable(client, topic, msg):
    logging.getLogger(__name__).info("%s %s", topic, msg)
    client.publish(topic, msg)

def airconditioner(client,topic, msg):
    logging.getLogger(__name__).info("%s", topic)
    enable(client, topic, msg)
    pass

def actuator(client,topic, msg):
    enable(client, topic, msg)
    pass

def _update_config_value(key, value):
    global Food_min_percent, Water_min_percent, Portion_max_g, Food_capacity_g, Water_capacity_ml, Food_tray_capacity_g, Water_tray_capacity_ml, Food_tray_min_percent, Water_tray_min_percent
    try:
        ivalue = int(float(value))
    except Exception:
        logging.getLogger(__name__).warning("Invalid config value for %s: %s", key, value)
        return
    if key == 'Food_min_percent':
        Food_min_percent = ivalue; cfg.Food_min_percent = ivalue
    elif key == 'Water_min_percent':
        Water_min_percent = ivalue; cfg.Water_min_percent = ivalue
    elif key == 'Portion_max_g':
        Portion_max_g = ivalue; cfg.Portion_max_g = ivalue
    elif key == 'Food_capacity_g':
        Food_capacity_g = ivalue; cfg.Food_capacity_g = ivalue
    elif key == 'Water_capacity_ml':
        Water_capacity_ml = ivalue; cfg.Water_capacity_ml = ivalue
    elif key == 'Food_tray_capacity_g':
        Food_tray_capacity_g = ivalue; cfg.Food_tray_capacity_g = ivalue
    elif key == 'Water_tray_capacity_ml':
        Water_tray_capacity_ml = ivalue; cfg.Water_tray_capacity_ml = ivalue
    elif key == 'Food_tray_min_percent':
        Food_tray_min_percent = ivalue; cfg.Food_tray_min_percent = ivalue
    elif key == 'Water_tray_min_percent':
        Water_tray_min_percent = ivalue; cfg.Water_tray_min_percent = ivalue
    logging.getLogger(__name__).info("Updated %s to %s", key, ivalue)
    # persist
    try:
        cfg.save_settings()
    except Exception:
        pass


def check_DB_for_change(client):
    # Food level low alert (values now in grams; compare as percent of capacity)
    df = da.fetch_data(db_name, 'data', 'FoodTank')
    if len(df.value) > 0:
        try:
            last_g = float(df.value.iloc[-1])
            perc = (last_g / float(Food_capacity_g)) * 100.0 if Food_capacity_g else 0.0
            if perc < float(Food_min_percent):
                msg = f'Food level low! Current: {int(last_g)} g ({perc:.0f}%)'
                logging.getLogger(__name__).warning(msg)
                client.publish(comm_topic+'alarm', msg)
        except Exception:
            pass
    # Water level low alert (values now in ml; compare as percent of capacity)
    df = da.fetch_data(db_name, 'data', 'WaterTank')
    if len(df.value) > 0:
        try:
            last_ml = float(df.value.iloc[-1])
            perc = (last_ml / float(Water_capacity_ml)) * 100.0 if Water_capacity_ml else 0.0
            if perc < float(Water_min_percent):
                msg = f'Water level low! Current: {int(last_ml)} ml ({perc:.0f}%)'
                logging.getLogger(__name__).warning(msg)
                client.publish(comm_topic+'alarm', msg)
        except Exception:
            pass
    # Portion too large warning
    df = da.fetch_data(db_name, 'data', 'MealsDispensed')
    if len(df.value) > 0:
        try:
            last = float(df.value.iloc[-1])
            if last > Portion_max_g:
                msg = f'Warning: Portion exceeds max! Portion: {last} g'
                logging.getLogger(__name__).warning(msg)
                client.publish(comm_topic+'alarm', msg)
        except Exception:
            pass
    # Food tray low alert
    df = da.fetch_data(db_name, 'data', 'FoodTray')
    if len(df.value) > 0:
        try:
            last_g = float(df.value.iloc[-1])
            perc = (last_g / float(Food_tray_capacity_g)) * 100.0 if Food_tray_capacity_g else 0.0
            if perc < float(Food_tray_min_percent):
                msg = f'Food tray low! Current: {int(last_g)} g ({perc:.0f}%)'
                logging.getLogger(__name__).warning(msg)
                client.publish(comm_topic+'alarm', msg)
        except Exception:
            pass
    # Water tray low alert
    df = da.fetch_data(db_name, 'data', 'WaterTray')
    if len(df.value) > 0:
        try:
            last_ml = float(df.value.iloc[-1])
            perc = (last_ml / float(Water_tray_capacity_ml)) * 100.0 if Water_tray_capacity_ml else 0.0
            if perc < float(Water_tray_min_percent):
                msg = f'Water tray low! Current: {int(last_ml)} ml ({perc:.0f}%)'
                logging.getLogger(__name__).warning(msg)
                client.publish(comm_topic+'alarm', msg)
        except Exception:
            pass


def check_Data(client):
    # No DB-triggered actuator flow needed for the pet feeder template.
    # Keep as a placeholder for future features (e.g., scheduled feedings).
    return

def main():    
    # Ensure DB schema exists (idempotent)
    try:
        da.init_db(db_name)
    except Exception as e:
        logging.getLogger(__name__).exception("DB init failed: %s", e)
    # Quick broker connectivity check
    try:
        with socket.create_connection((broker_ip, int(broker_port)), timeout=3):
            logging.getLogger(__name__).info("Broker reachable at %s:%s", broker_ip, broker_port)
    except Exception as e:
        logging.getLogger(__name__).warning(
            "Broker not reachable at %s:%s (%s). Ensure network/broker are accessible or set SMARTPETFEEDER_BROKER_HOST.",
            broker_ip, broker_port, e,
        )
    cname = "Manager-"
    client = client_init(cname)
    # main monitoring loop
    client.loop_start()  # Start loop
    client.subscribe(comm_topic+'#')
    try:
        while conn_time==0:
            check_DB_for_change(client)
            time.sleep(conn_time+manag_time)
            # Placeholder for DB-triggered actions
            check_Data(client) 
            time.sleep(3)       
        logging.getLogger(__name__).info("con_time ending") 
    except KeyboardInterrupt:
        client.disconnect() # disconnect from broker
        logging.getLogger(__name__).info("interrupted by keyboard")

    client.loop_stop()    #Stop loop
    # end session
    client.disconnect() # disconnect from broker
    logging.getLogger(__name__).info("End manager run script")

if __name__ == "__main__":
    main()
