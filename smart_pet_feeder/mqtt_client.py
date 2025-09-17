import logging
import time
import uuid

import paho.mqtt.client as mqtt

from .config import *


class MqttClient:
    
    def __init__(self):
        # broker IP adress:
        self.broker=''
        self.topic=''
        self.port='' 
        self.client_name=''
        self.username=''
        self.password=''        
        self.subscribe_topic=''
        self.publish_topic=''
        self.publish_message=''
        self.on_connected_callback = None
        self.connected = False
        self.subscribed = False
        # last will settings
        self._lwt_topic = None
        self._lwt_payload = None
        # internal paho client
        self.client = None
        self._client_id = None
        self._loop_running = False
        self._ever_connected = False
        self._last_connect_attempt = 0.0
        self._reconnect_interval = 5.0  # seconds
        self._subscriptions = set()
        
    # Setters and getters
    def set_on_connected_callback(self, callback):
        self.on_connected_callback = callback
    def get_broker(self):
        return self.broker
    def set_broker(self, value):
        self.broker= value         
    def get_port(self):
        return self.port
    def set_port(self, value):
        self.port= value     
    def get_client_name(self):
        return self.client_name
    def set_client_name(self, value):
        self.client_name= value
        if self.client and value and value != self._client_id:
            try:
                if self._loop_running:
                    self.client.loop_stop()
            except Exception:
                pass
            try:
                self.client.disconnect()
            except Exception:
                pass
            self.client = None
            self._client_id = None
            self._loop_running = False
            self.connected = False
            self.subscribed = False
            self._ever_connected = False
    def get_username(self):
        return self.username
    def set_username(self, value):
        self.username= value
        if self.client:
            try:
                self.client.username_pw_set(self.username, self.password)
            except Exception:
                pass
    def get_password(self):
        return self.password
    def set_password(self, value):
        self.password= value
        if self.client:
            try:
                self.client.username_pw_set(self.username, self.password)
            except Exception:
                pass
    def get_subscribe_topic(self):
        return self.subscribe_topic
    def set_subscribe_topic(self, value):
        self.subscribe_topic= value        
    def get_publish_topic(self):
        return self.publish_topic
    def set_publish_topic(self, value):
        self.publish_topic= value         
    def get_publish_message(self):
        return self.publish_message
    def set_publish_message(self, value):
        self.publish_message= value 
    def set_last_will(self, topic: str, payload: str):
        self._lwt_topic = topic
        self._lwt_payload = payload
        
        
    def on_log(self, client, userdata, level, buf):
        logging.getLogger(__name__).debug("log: %s", buf)
            
    def on_connect(self, client, userdata, flags, rc):
        
        if rc==0:
            logging.getLogger(__name__).info("connected OK")
            self.connected = True
            self._ever_connected = True
            # resubscribe to all known topics after reconnect
            for topic, qos in list(self._subscriptions):
                try:
                    self.client.subscribe(topic, qos=qos)
                    self.subscribed = True
                except Exception as exc:
                    logging.getLogger(__name__).warning(
                        "Failed to (re)subscribe to %s: %s", topic, exc
                    )
            if callable(self.on_connected_callback):
                self.on_connected_callback()
        else:
            logging.getLogger(__name__).error("Bad connection Returned code=%s", rc)
            
    def on_disconnect(self, client, userdata, flags, rc=0):
        self.connected = False
        self.subscribed = False
        self._loop_running = False
        logging.getLogger(__name__).info("Disconnected result code %s", rc)
            
    def on_message(self, client, userdata, msg):
        topic=msg.topic
        m_decode=str(msg.payload.decode("utf-8","ignore"))
        logging.getLogger(__name__).debug("message from %s %s", topic, m_decode)
        #mainwin.subscribeDock.update_mess_win(m_decode)

    def _ensure_client(self):
        desired_id = self.client_name or self._client_id
        if not desired_id:
            desired_id = f"iot-client-{uuid.uuid4().hex[:10]}"
        if self.client and self._client_id == desired_id:
            return
        if self.client:
            try:
                if self._loop_running:
                    self.client.loop_stop()
            except Exception:
                pass
            try:
                self.client.disconnect()
            except Exception:
                pass
        self._client_id = desired_id
        self.client = mqtt.Client(
            client_id=desired_id,
            clean_session=True,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        )
        try:
            self.client.enable_logger(logging.getLogger('paho.mqtt.client'))
        except Exception:
            pass
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_log = self.on_log
        self.client.on_message = self.on_message
        if self.username or self.password:
            self.client.username_pw_set(self.username, self.password)
        # Last will (announce unexpected disconnects)
        try:
            if self._lwt_topic and self._lwt_payload is not None:
                self.client.will_set(self._lwt_topic, self._lwt_payload, qos=0, retain=False)
        except Exception:
            pass

    def connect_to(self):
        self._ensure_client()
        now = time.monotonic()
        if self._ever_connected and (now - self._last_connect_attempt) < self._reconnect_interval:
            logging.getLogger(__name__).debug(
                "Skipping reconnect attempt; waited only %.1fs", now - self._last_connect_attempt
            )
            return
        self._last_connect_attempt = now
        # Quick connectivity check (non-blocking friendly)
        import socket
        try:
            with socket.create_connection((self.broker, int(self.port)), timeout=3):
                pass
        except Exception as e:
            logging.getLogger(__name__).warning(
                "Broker not reachable at %s:%s (%s). Will attempt MQTT connect anyway.",
                self.broker, self.port, e,
            )
        logging.getLogger(__name__).info("Connecting to broker %s", self.broker)
        port = int(self.port) if isinstance(self.port, str) else self.port
        try:
            if self._ever_connected:
                self.client.reconnect()
            else:
                self.client.connect(self.broker, port)
        except Exception as exc:
            logging.getLogger(__name__).warning("Reconnect failed, trying fresh connect: %s", exc)
            try:
                self.client.connect(self.broker, port)
            except Exception as exc_final:
                logging.getLogger(__name__).error("MQTT connect failed: %s", exc_final)
                raise

    def disconnect_from(self):
        if not self.client:
            return
        try:
            if self._loop_running:
                self.client.loop_stop()
        except Exception:
            pass
        self._loop_running = False
        self.client.disconnect()                   
    
    def start_listening(self):        
        if not self.client:
            self._ensure_client()
        if self._loop_running:
            return
        self.client.loop_start()  
        self._loop_running = True
    
    def stop_listening(self):        
        if not self.client or not self._loop_running:
            return
        self.client.loop_stop()
        self._loop_running = False
    
    def subscribe_to(self, topic):
        qos = 0
        if isinstance(topic, tuple):
            topic, qos = topic
        self._subscriptions.add((topic, qos))
        if not self.connected:
            logging.getLogger(__name__).info(
                "Queued subscription to %s until connection is ready", topic
            )
            return
        try:
            self.client.subscribe(topic, qos=qos)
            self.subscribed = True
            logging.getLogger(__name__).info("Subscribed to %s", topic)
        except Exception as exc:
            logging.getLogger(__name__).warning("Subscribe to %s failed: %s", topic, exc)
        
              
    def publish_to(self, topic, message, retain=False):
        if self.connected:
            self.client.publish(topic, message, retain=retain)
            logging.getLogger(__name__).info(
                "Published to %s | %s%s",
                topic,
                message,
                " (retained)" if retain else "",
            )
        else:
            logging.getLogger(__name__).warning("Can't publish. Connection should be established first")            
