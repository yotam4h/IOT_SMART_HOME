import paho.mqtt.client as mqtt
from .config import *
import logging


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
    def get_username(self):
        return self.username
    def set_username(self, value):
        self.username= value     
    def get_password(self):
        return self.password
    def set_password(self, value):
        self.password= value         
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
            if callable(self.on_connected_callback):
                self.on_connected_callback()
        else:
            logging.getLogger(__name__).error("Bad connection Returned code=%s", rc)
            
    def on_disconnect(self, client, userdata, flags, rc=0):
        self.connected = False
        self.subscribed = False
        logging.getLogger(__name__).info("Disconnected result code %s", rc)
            
    def on_message(self, client, userdata, msg):
        topic=msg.topic
        m_decode=str(msg.payload.decode("utf-8","ignore"))
        logging.getLogger(__name__).debug("message from %s %s", topic, m_decode)
        #mainwin.subscribeDock.update_mess_win(m_decode)

    def connect_to(self):
        # Init paho mqtt client class        
        self.client = mqtt.Client(
            client_id=self.client_name,
            clean_session=True,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        )  # paho-mqtt v2 compatible       
        # Also enable internal paho logging for deeper diagnostics
        try:
            self.client.enable_logger(logging.getLogger('paho.mqtt.client'))
        except Exception:
            pass
        self.client.on_connect=self.on_connect  #bind call back function
        self.client.on_disconnect=self.on_disconnect
        self.client.on_log=self.on_log
        self.client.on_message=self.on_message
        self.client.username_pw_set(self.username,self.password)        
        # Last will (announce unexpected disconnects)
        try:
            if self._lwt_topic and self._lwt_payload is not None:
                self.client.will_set(self._lwt_topic, self._lwt_payload, qos=0, retain=False)
        except Exception:
            pass
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
        # ensure port is an int
        port = int(self.port) if isinstance(self.port, str) else self.port
        self.client.connect(self.broker, port)     #connect to broker
    
    def disconnect_from(self):
        self.client.disconnect()                   
    
    def start_listening(self):        
        self.client.loop_start()        
    
    def stop_listening(self):        
        self.client.loop_stop()    
    
    def subscribe_to(self, topic):
        if self.connected:
            self.client.subscribe(topic)
            self.subscribed = True
            logging.getLogger(__name__).info("Subscribed to %s", topic)
        else:
            logging.getLogger(__name__).warning("Can't subscribe. Connection should be established first")         
        
              
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
