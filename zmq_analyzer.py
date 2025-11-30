import json
import os
import threading
import time
import wx
import wx.adv
import wx.dataview
import zmq

# Constants
CONFIG_FILE = os.path.expanduser("~/.zmqanalyzer-config.json")
CONFIG_PUBLISHER_PORT_KEY = "publisher_port"
CONFIG_PUBLISHER_TOPIC_KEY = "publisher_last_topic"
CONFIG_SUBSCRIBER_TOPICS_KEY = "subscriber_last_topic"
CONFIG_SUBSCRIBER_ADDRESS_KEY = "subscriber_address"
CONFIG_REQUESTER_ADDRESS_KEY = "requester_address"
CONFIG_REPLYER_ADDRESS_KEY = "replyer_address"
CONFIG_RECENT_SENT_MSGS_PUB_KEY = "publisher_recent_messages"
CONFIG_RECENT_SENT_MSGS_REQ_KEY = "requester_recent_messages"
CONFIG_RECENT_SENT_MSGS_REP_KEY = "replyer_recent_messages"
# PUSH/PULL pattern
CONFIG_PUSHER_PORT_KEY = "pusher_port"
CONFIG_PULLER_ADDRESS_KEY = "puller_address"
CONFIG_RECENT_SENT_MSGS_PUSH_KEY = "pusher_recent_messages"
# DEALER/ROUTER pattern
CONFIG_DEALER_ADDRESS_KEY = "dealer_address"
CONFIG_ROUTER_PORT_KEY = "router_port"
CONFIG_RECENT_SENT_MSGS_DEALER_KEY = "dealer_recent_messages"
CONFIG_RECENT_SENT_MSGS_ROUTER_KEY = "router_recent_messages"
# PAIR pattern
CONFIG_PAIR_ADDRESS_KEY = "pair_address"
CONFIG_PAIR_MODE_KEY = "pair_mode"
CONFIG_RECENT_SENT_MSGS_PAIR_KEY = "pair_recent_messages"
# XPUB/XSUB pattern (broker/proxy)
CONFIG_XPUB_PORT_KEY = "xpub_port"
CONFIG_XSUB_ADDRESS_KEY = "xsub_address"
CONFIG_RECENT_SENT_MSGS_XPUB_KEY = "xpub_recent_messages"
# STREAM pattern (raw TCP)
CONFIG_STREAM_ADDRESS_KEY = "stream_address"
CONFIG_STREAM_MODE_KEY = "stream_mode"
CONFIG_RECENT_SENT_MSGS_STREAM_KEY = "stream_recent_messages"
# CLIENT/SERVER pattern (draft)
CONFIG_CLIENT_ADDRESS_KEY = "client_address"
CONFIG_SERVER_PORT_KEY = "server_port"
CONFIG_RECENT_SENT_MSGS_CLIENT_KEY = "client_recent_messages"
CONFIG_RECENT_SENT_MSGS_SERVER_KEY = "server_recent_messages"
# RADIO/DISH pattern (draft)
CONFIG_RADIO_PORT_KEY = "radio_port"
CONFIG_RADIO_GROUP_KEY = "radio_group"
CONFIG_DISH_ADDRESS_KEY = "dish_address"
CONFIG_DISH_GROUP_KEY = "dish_group"
CONFIG_RECENT_SENT_MSGS_RADIO_KEY = "radio_recent_messages"
# SCATTER/GATHER pattern (draft)
CONFIG_SCATTER_PORT_KEY = "scatter_port"
CONFIG_GATHER_ADDRESS_KEY = "gather_address"
CONFIG_RECENT_SENT_MSGS_SCATTER_KEY = "scatter_recent_messages"


# --- Config Class ---
class Config:
    _config = {}

    @staticmethod
    def load():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    Config._config = json.load(f)
                print(f"Config loaded from {CONFIG_FILE}")
            except Exception as e:
                print(f"Failed to load config: {e}")
                Config._config = {}
        else:
            Config._config = {}

    @staticmethod
    def save():
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(Config._config, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")

    @staticmethod
    def get(key, default=None):
        return Config._config.get(key, default)

    @staticmethod
    def set(key, value):
        Config._config[key] = value
        Config.save()

    @staticmethod
    def add_to_list(key, value):
        if key not in Config._config:
            Config._config[key] = []
        if value not in Config._config[key]:
            Config._config[key].insert(0, value)  # Add to front
            Config.save()

    @staticmethod
    def remove_from_list(key, value):
        if key in Config._config and value in Config._config[key]:
            Config._config[key].remove(value)
            Config.save()

    @staticmethod
    def get_list(key):
        return Config._config.get(key, [])


# --- ZMQ Logic Classes ---


class Publisher:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Publisher, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.port = ""
            cls._instance.is_bound = False
            cls._instance.lock = threading.Lock()
        return cls._instance

    def bind(self, port):
        """Bind the publisher socket to the specified port."""
        with self.lock:
            if self.is_bound:
                return False, "Publisher already bound"

            try:
                self.socket = self.context.socket(zmq.PUB)
                self.socket.bind(f"tcp://*:{port}")
                self.port = port
                self.is_bound = True
                print(f"Publisher bound to port {port}")
                return True, f"Publisher bound to port {port}"
            except zmq.ZMQError as e:
                print(f"Publisher bind error: {e}")
                if self.socket:
                    self.socket.close()
                    self.socket = None
                return False, f"Bind error: {e}"

    def unbind(self):
        """Unbind the publisher socket."""
        with self.lock:
            if not self.is_bound:
                return False, "Publisher not bound"

            try:
                if self.socket:
                    self.socket.close()
                    self.socket = None
                self.is_bound = False
                print(f"Publisher unbound from port {self.port}")
                return True, f"Publisher unbound from port {self.port}"
            except Exception as e:
                print(f"Publisher unbind error: {e}")
                return False, f"Unbind error: {e}"

    def send_message(self, topic, message):
        """Send a message on the specified topic."""
        with self.lock:
            if not self.is_bound or not self.socket:
                return False, "Publisher not bound"

            try:
                self.socket.send_multipart([topic.encode("utf-8"), message.encode("utf-8")])
                print(f"Published to {topic}: {message}")
                return True, "Message published"
            except zmq.ZMQError as e:
                print(f"Publish error: {e}")
                return False, f"Publish error: {e}"


class Subscriber:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Subscriber, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.running = False
            cls._instance.thread = None
            cls._instance.callback = None
            cls._instance.latest_messages = {}
            cls._instance.lock = threading.Lock()
        return cls._instance

    def start(self, topics, address):
        """Start subscribing to topics at the specified address."""
        self.stop()

        try:
            self.socket = self.context.socket(zmq.SUB)
            self.socket.connect(address)
            for topic in topics:
                self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)

            self.running = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"Subscriber started on {address} for topics {topics}")
            return True, f"Subscribed to {len(topics)} topic(s)"
        except zmq.ZMQError as e:
            print(f"Subscriber connect error: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False, f"Connection error: {e}"

    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.thread:
            self.thread.join(timeout=0.5)
            self.thread = None

    def set_callback(self, callback):
        self.callback = callback

    def _receive_loop(self):
        while self.running and self.socket:
            try:
                if self.socket.poll(100):
                    parts = self.socket.recv_multipart()
                    if len(parts) >= 2:
                        topic = parts[0].decode("utf-8")
                        message = parts[1].decode("utf-8")

                        with self.lock:
                            self.latest_messages[topic] = message

                        if self.callback:
                            # Try to parse JSON
                            try:
                                msg_json = json.loads(message)
                                wx.CallAfter(self.callback, topic, msg_json)
                            except json.JSONDecodeError:
                                wx.CallAfter(self.callback, topic, message)
            except zmq.ZMQError:
                break
            except Exception as e:
                print(f"Subscriber loop error: {e}")

    def get_latest_message(self, topic):
        with self.lock:
            return self.latest_messages.get(topic, "")


class Requester:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Requester, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.callback = None
            cls._instance.address = ""
        return cls._instance

    def set_callback(self, callback):
        self.callback = callback

    def request(self, message, address):
        # In ZMQ REQ/REP, we must follow send/recv pattern strictly.
        # For simplicity in this tool, we'll create a new socket for each request
        # or manage state carefully. The C++ code seems to reset socket often.
        # Let's try to keep one socket if address matches, but REQ sockets can get stuck if no reply.
        # Safest for a tool like this is to recreate socket or use lazy pirate pattern.
        # We'll recreate for robustness.

        def _do_request():
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.LINGER, 0)
            socket.connect(address)
            try:
                socket.send_string(message)
                if socket.poll(2000):  # 2 second timeout
                    reply = socket.recv_string()
                    if self.callback:
                        wx.CallAfter(self.callback, reply)
                else:
                    if self.callback:
                        wx.CallAfter(self.callback, "Error: Timeout waiting for reply")
            except zmq.ZMQError as e:
                if self.callback:
                    wx.CallAfter(self.callback, f"Error: {e}")
            finally:
                socket.close()

        threading.Thread(target=_do_request, daemon=True).start()


class Replyer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Replyer, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.running = False
            cls._instance.is_bound = False
            cls._instance.address = ""
            cls._instance.thread = None
            cls._instance.callback = None
            cls._instance.pending_reply = None
            cls._instance.reply_event = threading.Event()
        return cls._instance

    def set_callback(self, callback):
        self.callback = callback

    def bind(self, address):
        """Bind the replyer socket to the specified address."""
        if self.is_bound:
            return False, "Replyer already bound"

        try:
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(address)
            self.address = address
            self.running = True
            self.is_bound = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"Replyer bound to {address}")
            return True, f"Replyer bound to {address}"
        except zmq.ZMQError as e:
            print(f"Replyer bind error: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False, f"Bind error: {e}"

    def unbind(self):
        """Unbind the replyer socket."""
        if not self.is_bound:
            return False, "Replyer not bound"

        self.running = False
        self.is_bound = False
        self.reply_event.set()  # Wake up any waiting thread

        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

        print(f"Replyer unbound from {self.address}")
        return True, f"Replyer unbound from {self.address}"

    def send_reply(self, message):
        self.pending_reply = message
        self.reply_event.set()

    def _receive_loop(self):
        while self.running and self.socket:
            try:
                if self.socket.poll(100):
                    message = self.socket.recv_string()
                    if self.callback:
                        wx.CallAfter(self.callback, message)

                    # Wait for reply
                    self.reply_event.clear()
                    # We wait indefinitely or until stopped?
                    # The C++ code uses a condition variable.
                    while self.running and not self.reply_event.is_set():
                        time.sleep(0.1)

                    if self.running and self.pending_reply is not None:
                        self.socket.send_string(self.pending_reply)
                        self.pending_reply = None
            except zmq.ZMQError:
                break
            except Exception as e:
                print(f"Replyer loop error: {e}")


class Pusher:
    """PUSH socket - sends messages to connected PULLers in round-robin fashion."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Pusher, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.port = ""
            cls._instance.is_bound = False
            cls._instance.lock = threading.Lock()
        return cls._instance

    def bind(self, port):
        """Bind the pusher socket to the specified port."""
        with self.lock:
            if self.is_bound:
                return False, "Pusher already bound"

            try:
                self.socket = self.context.socket(zmq.PUSH)
                self.socket.bind(f"tcp://*:{port}")
                self.port = port
                self.is_bound = True
                print(f"Pusher bound to port {port}")
                return True, f"Pusher bound to port {port}"
            except zmq.ZMQError as e:
                print(f"Pusher bind error: {e}")
                if self.socket:
                    self.socket.close()
                    self.socket = None
                return False, f"Bind error: {e}"

    def unbind(self):
        """Unbind the pusher socket."""
        with self.lock:
            if not self.is_bound:
                return False, "Pusher not bound"

            try:
                if self.socket:
                    self.socket.close()
                    self.socket = None
                self.is_bound = False
                print(f"Pusher unbound from port {self.port}")
                return True, f"Pusher unbound from port {self.port}"
            except Exception as e:
                print(f"Pusher unbind error: {e}")
                return False, f"Unbind error: {e}"

    def send_message(self, message):
        """Send a message to connected pullers."""
        with self.lock:
            if not self.is_bound or not self.socket:
                return False, "Pusher not bound"

            try:
                self.socket.send_string(message)
                print(f"Pushed: {message[:100]}...")
                return True, "Message pushed"
            except zmq.ZMQError as e:
                print(f"Push error: {e}")
                return False, f"Push error: {e}"


class Puller:
    """PULL socket - receives messages from PUSHers."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Puller, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.running = False
            cls._instance.thread = None
            cls._instance.callback = None
            cls._instance.lock = threading.Lock()
        return cls._instance

    def start(self, address):
        """Start pulling messages from the specified address."""
        self.stop()

        try:
            self.socket = self.context.socket(zmq.PULL)
            self.socket.connect(address)
            self.running = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"Puller connected to {address}")
            return True, f"Puller connected to {address}"
        except zmq.ZMQError as e:
            print(f"Puller connect error: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False, f"Connection error: {e}"

    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.thread:
            self.thread.join(timeout=0.5)
            self.thread = None

    def set_callback(self, callback):
        self.callback = callback

    def _receive_loop(self):
        while self.running and self.socket:
            try:
                if self.socket.poll(100):
                    message = self.socket.recv_string()
                    if self.callback:
                        try:
                            msg_json = json.loads(message)
                            wx.CallAfter(self.callback, msg_json)
                        except json.JSONDecodeError:
                            wx.CallAfter(self.callback, message)
            except zmq.ZMQError:
                break
            except Exception as e:
                print(f"Puller loop error: {e}")


class Dealer:
    """DEALER socket - async REQ that can send multiple requests without waiting."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Dealer, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.running = False
            cls._instance.is_connected = False
            cls._instance.address = ""
            cls._instance.thread = None
            cls._instance.callback = None
            cls._instance.lock = threading.Lock()
        return cls._instance

    def set_callback(self, callback):
        self.callback = callback

    def connect(self, address):
        """Connect to a ROUTER socket."""
        self.disconnect()

        try:
            self.socket = self.context.socket(zmq.DEALER)
            self.socket.setsockopt(zmq.LINGER, 0)
            self.socket.connect(address)
            self.address = address
            self.running = True
            self.is_connected = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"Dealer connected to {address}")
            return True, f"Dealer connected to {address}"
        except zmq.ZMQError as e:
            print(f"Dealer connect error: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False, f"Connection error: {e}"

    def disconnect(self):
        """Disconnect the dealer socket."""
        self.running = False
        self.is_connected = False

        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        if self.thread:
            self.thread.join(timeout=0.5)
            self.thread = None

        print(f"Dealer disconnected from {self.address}")
        return True, f"Dealer disconnected"

    def send(self, message):
        """Send a message asynchronously."""
        with self.lock:
            if not self.is_connected or not self.socket:
                return False, "Dealer not connected"

            try:
                # DEALER sends with empty delimiter frame
                self.socket.send_multipart([b"", message.encode("utf-8")])
                print(f"Dealer sent: {message[:100]}...")
                return True, "Message sent"
            except zmq.ZMQError as e:
                print(f"Dealer send error: {e}")
                return False, f"Send error: {e}"

    def _receive_loop(self):
        while self.running and self.socket:
            try:
                if self.socket.poll(100):
                    parts = self.socket.recv_multipart()
                    # DEALER receives with empty delimiter frame
                    if len(parts) >= 2:
                        message = parts[-1].decode("utf-8")
                    else:
                        message = parts[0].decode("utf-8") if parts else ""

                    if self.callback and message:
                        try:
                            msg_json = json.loads(message)
                            wx.CallAfter(self.callback, msg_json)
                        except json.JSONDecodeError:
                            wx.CallAfter(self.callback, message)
            except zmq.ZMQError:
                break
            except Exception as e:
                print(f"Dealer loop error: {e}")


class Router:
    """ROUTER socket - async REP that can handle multiple clients."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Router, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.running = False
            cls._instance.is_bound = False
            cls._instance.port = ""
            cls._instance.thread = None
            cls._instance.callback = None
            cls._instance.pending_replies = {}  # {identity: message}
            cls._instance.current_identity = None
            cls._instance.lock = threading.Lock()
        return cls._instance

    def set_callback(self, callback):
        self.callback = callback

    def bind(self, port):
        """Bind the router socket to the specified port."""
        if self.is_bound:
            return False, "Router already bound"

        try:
            self.socket = self.context.socket(zmq.ROUTER)
            self.socket.bind(f"tcp://*:{port}")
            self.port = port
            self.running = True
            self.is_bound = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"Router bound to port {port}")
            return True, f"Router bound to port {port}"
        except zmq.ZMQError as e:
            print(f"Router bind error: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False, f"Bind error: {e}"

    def unbind(self):
        """Unbind the router socket."""
        if not self.is_bound:
            return False, "Router not bound"

        self.running = False
        self.is_bound = False

        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

        print(f"Router unbound from port {self.port}")
        return True, f"Router unbound from port {self.port}"

    def send_reply(self, message):
        """Send a reply to the current client."""
        with self.lock:
            if not self.is_bound or not self.socket or not self.current_identity:
                return False, "No client to reply to"

            try:
                self.socket.send_multipart([self.current_identity, b"", message.encode("utf-8")])
                print(f"Router replied: {message[:100]}...")
                return True, "Reply sent"
            except zmq.ZMQError as e:
                print(f"Router send error: {e}")
                return False, f"Send error: {e}"

    def _receive_loop(self):
        while self.running and self.socket:
            try:
                if self.socket.poll(100):
                    parts = self.socket.recv_multipart()
                    # ROUTER receives: [identity, empty, message]
                    if len(parts) >= 3:
                        identity = parts[0]
                        message = parts[-1].decode("utf-8")
                        with self.lock:
                            self.current_identity = identity

                        if self.callback and message:
                            try:
                                msg_json = json.loads(message)
                                wx.CallAfter(self.callback, msg_json)
                            except json.JSONDecodeError:
                                wx.CallAfter(self.callback, message)
            except zmq.ZMQError:
                break
            except Exception as e:
                print(f"Router loop error: {e}")


class PairSocket:
    """PAIR socket - exclusive 1:1 bidirectional connection."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PairSocket, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.running = False
            cls._instance.is_active = False
            cls._instance.address = ""
            cls._instance.mode = ""  # "bind" or "connect"
            cls._instance.thread = None
            cls._instance.callback = None
            cls._instance.lock = threading.Lock()
        return cls._instance

    def set_callback(self, callback):
        self.callback = callback

    def bind(self, port):
        """Bind the pair socket to the specified port."""
        self.stop()

        try:
            self.socket = self.context.socket(zmq.PAIR)
            self.socket.setsockopt(zmq.LINGER, 0)
            self.socket.setsockopt(zmq.SNDTIMEO, 1000)  # 1 second send timeout
            self.socket.bind(f"tcp://*:{port}")
            self.address = f"tcp://*:{port}"
            self.mode = "bind"
            self.running = True
            self.is_active = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"Pair bound to port {port}")
            return True, f"Pair bound to port {port}"
        except zmq.ZMQError as e:
            print(f"Pair bind error: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False, f"Bind error: {e}"

    def connect(self, address):
        """Connect to another pair socket."""
        self.stop()

        try:
            self.socket = self.context.socket(zmq.PAIR)
            self.socket.setsockopt(zmq.LINGER, 0)
            self.socket.setsockopt(zmq.SNDTIMEO, 1000)  # 1 second send timeout
            self.socket.connect(address)
            self.address = address
            self.mode = "connect"
            self.running = True
            self.is_active = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"Pair connected to {address}")
            return True, f"Pair connected to {address}"
        except zmq.ZMQError as e:
            print(f"Pair connect error: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False, f"Connection error: {e}"

    def stop(self):
        """Stop the pair socket."""
        self.running = False
        self.is_active = False

        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        if self.thread:
            self.thread.join(timeout=0.5)
            self.thread = None

        print(f"Pair stopped")
        return True, "Pair stopped"

    def send(self, message):
        """Send a message to the peer."""
        with self.lock:
            if not self.is_active or not self.socket:
                return False, "Pair not active"

            try:
                self.socket.send_string(message)
                print(f"Pair sent: {message[:100]}...")
                return True, "Message sent"
            except zmq.Again:
                print("Pair send timeout: peer not connected or not ready")
                return False, "Send timeout: peer not connected"
            except zmq.ZMQError as e:
                print(f"Pair send error: {e}")
                return False, f"Send error: {e}"

    def _receive_loop(self):
        while self.running and self.socket:
            try:
                if self.socket.poll(100):
                    message = self.socket.recv_string()
                    if self.callback:
                        try:
                            msg_json = json.loads(message)
                            wx.CallAfter(self.callback, msg_json)
                        except json.JSONDecodeError:
                            wx.CallAfter(self.callback, message)
            except zmq.ZMQError:
                break
            except Exception as e:
                print(f"Pair loop error: {e}")


class XPublisher:
    """XPUB socket - like PUB but receives subscription messages from clients."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(XPublisher, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.port = ""
            cls._instance.is_bound = False
            cls._instance.running = False
            cls._instance.thread = None
            cls._instance.subscription_callback = None
            cls._instance.lock = threading.Lock()
        return cls._instance

    def set_subscription_callback(self, callback):
        self.subscription_callback = callback

    def bind(self, port):
        """Bind the XPUB socket to the specified port."""
        with self.lock:
            if self.is_bound:
                return False, "XPublisher already bound"

            try:
                self.socket = self.context.socket(zmq.XPUB)
                self.socket.bind(f"tcp://*:{port}")
                self.port = port
                self.is_bound = True
                self.running = True
                self.thread = threading.Thread(target=self._receive_loop, daemon=True)
                self.thread.start()
                print(f"XPublisher bound to port {port}")
                return True, f"XPublisher bound to port {port}"
            except zmq.ZMQError as e:
                print(f"XPublisher bind error: {e}")
                if self.socket:
                    self.socket.close()
                    self.socket = None
                return False, f"Bind error: {e}"

    def unbind(self):
        """Unbind the XPUB socket."""
        with self.lock:
            if not self.is_bound:
                return False, "XPublisher not bound"

            self.running = False
            try:
                if self.socket:
                    self.socket.close()
                    self.socket = None
                self.is_bound = False
                if self.thread:
                    self.thread.join(timeout=0.5)
                    self.thread = None
                print(f"XPublisher unbound from port {self.port}")
                return True, f"XPublisher unbound from port {self.port}"
            except Exception as e:
                print(f"XPublisher unbind error: {e}")
                return False, f"Unbind error: {e}"

    def send_message(self, topic, message):
        """Send a message on the specified topic."""
        with self.lock:
            if not self.is_bound or not self.socket:
                return False, "XPublisher not bound"

            try:
                self.socket.send_multipart([topic.encode("utf-8"), message.encode("utf-8")])
                print(f"XPublished to {topic}: {message[:100]}...")
                return True, "Message published"
            except zmq.ZMQError as e:
                print(f"XPublish error: {e}")
                return False, f"Publish error: {e}"

    def _receive_loop(self):
        """Receive subscription events from clients."""
        while self.running and self.socket:
            try:
                if self.socket.poll(100):
                    event = self.socket.recv()
                    # First byte: 1 = subscribe, 0 = unsubscribe
                    # Remaining bytes: topic
                    if len(event) > 0:
                        is_subscribe = event[0] == 1
                        topic = event[1:].decode("utf-8", errors="replace")
                        action = "subscribed" if is_subscribe else "unsubscribed"
                        if self.subscription_callback:
                            wx.CallAfter(self.subscription_callback, action, topic)
            except zmq.ZMQError:
                break
            except Exception as e:
                print(f"XPublisher loop error: {e}")


class XSubscriber:
    """XSUB socket - like SUB but can send subscription messages."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(XSubscriber, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.running = False
            cls._instance.thread = None
            cls._instance.callback = None
            cls._instance.lock = threading.Lock()
        return cls._instance

    def start(self, topics, address):
        """Start subscribing to topics at the specified address."""
        self.stop()

        try:
            self.socket = self.context.socket(zmq.XSUB)
            self.socket.connect(address)
            # XSUB requires explicit subscription messages
            for topic in topics:
                # Send subscribe message: 0x01 + topic
                self.socket.send(b"\x01" + topic.encode("utf-8"))

            self.running = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"XSubscriber started on {address} for topics {topics}")
            return True, f"XSubscribed to {len(topics)} topic(s)"
        except zmq.ZMQError as e:
            print(f"XSubscriber connect error: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False, f"Connection error: {e}"

    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.thread:
            self.thread.join(timeout=0.5)
            self.thread = None

    def set_callback(self, callback):
        self.callback = callback

    def subscribe(self, topic):
        """Subscribe to a new topic."""
        with self.lock:
            if self.socket:
                try:
                    self.socket.send(b"\x01" + topic.encode("utf-8"))
                    return True
                except zmq.ZMQError:
                    return False
        return False

    def unsubscribe(self, topic):
        """Unsubscribe from a topic."""
        with self.lock:
            if self.socket:
                try:
                    self.socket.send(b"\x00" + topic.encode("utf-8"))
                    return True
                except zmq.ZMQError:
                    return False
        return False

    def _receive_loop(self):
        while self.running and self.socket:
            try:
                if self.socket.poll(100):
                    parts = self.socket.recv_multipart()
                    if len(parts) >= 2:
                        topic = parts[0].decode("utf-8")
                        message = parts[1].decode("utf-8")

                        if self.callback:
                            try:
                                msg_json = json.loads(message)
                                wx.CallAfter(self.callback, topic, msg_json)
                            except json.JSONDecodeError:
                                wx.CallAfter(self.callback, topic, message)
            except zmq.ZMQError:
                break
            except Exception as e:
                print(f"XSubscriber loop error: {e}")


class StreamSocket:
    """STREAM socket - raw TCP connection for non-ZMQ peers."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StreamSocket, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.running = False
            cls._instance.is_active = False
            cls._instance.address = ""
            cls._instance.mode = ""  # "bind" or "connect"
            cls._instance.thread = None
            cls._instance.callback = None
            cls._instance.current_identity = None
            cls._instance.lock = threading.Lock()
        return cls._instance

    def set_callback(self, callback):
        self.callback = callback

    def bind(self, port):
        """Bind the stream socket to accept raw TCP connections."""
        self.stop()

        try:
            self.socket = self.context.socket(zmq.STREAM)
            self.socket.bind(f"tcp://*:{port}")
            self.address = f"tcp://*:{port}"
            self.mode = "bind"
            self.running = True
            self.is_active = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"Stream bound to port {port}")
            return True, f"Stream bound to port {port}"
        except zmq.ZMQError as e:
            print(f"Stream bind error: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False, f"Bind error: {e}"

    def connect(self, address):
        """Connect to a raw TCP server."""
        self.stop()

        try:
            self.socket = self.context.socket(zmq.STREAM)
            self.socket.connect(address)
            self.address = address
            self.mode = "connect"
            self.running = True
            self.is_active = True
            # Get the routing identity for sending
            self.socket.setsockopt(zmq.LINGER, 0)
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"Stream connected to {address}")
            return True, f"Stream connected to {address}"
        except zmq.ZMQError as e:
            print(f"Stream connect error: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False, f"Connection error: {e}"

    def stop(self):
        """Stop the stream socket."""
        self.running = False
        self.is_active = False

        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        if self.thread:
            self.thread.join(timeout=0.5)
            self.thread = None

        self.current_identity = None
        print("Stream stopped")
        return True, "Stream stopped"

    def send(self, message):
        """Send raw data to the peer."""
        with self.lock:
            if not self.is_active or not self.socket:
                return False, "Stream not active"

            if not self.current_identity:
                return False, "No peer connected"

            try:
                # STREAM requires identity frame + data frame
                self.socket.send(self.current_identity, zmq.SNDMORE)
                self.socket.send_string(message)
                print(f"Stream sent: {message[:100]}...")
                return True, "Data sent"
            except zmq.ZMQError as e:
                print(f"Stream send error: {e}")
                return False, f"Send error: {e}"

    def _receive_loop(self):
        while self.running and self.socket:
            try:
                if self.socket.poll(100):
                    # STREAM always receives: [identity, data]
                    identity = self.socket.recv()
                    data = self.socket.recv()

                    # Store identity for replies
                    if data:  # Non-empty data means actual message
                        with self.lock:
                            self.current_identity = identity

                        message = data.decode("utf-8", errors="replace")
                        if self.callback and message:
                            wx.CallAfter(self.callback, identity.hex()[:16], message)
                    elif identity and not data:
                        # Empty data with identity means connect/disconnect event
                        with self.lock:
                            if self.current_identity == identity:
                                pass  # Keep identity on disconnect for now
                            else:
                                self.current_identity = identity
                        if self.callback:
                            wx.CallAfter(self.callback, identity.hex()[:16], "[Connected]")
            except zmq.ZMQError:
                break
            except Exception as e:
                print(f"Stream loop error: {e}")


class Client:
    """CLIENT socket - thread-safe async request socket (draft API)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Client, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.running = False
            cls._instance.thread = None
            cls._instance.callback = None
        return cls._instance

    def set_callback(self, callback):
        self.callback = callback

    def connect(self, address):
        self.disconnect()
        try:
            self.socket = self.context.socket(zmq.CLIENT)
            self.socket.connect(address)
            self.running = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"Client connected to {address}")
            return True, f"Connected to {address}"
        except zmq.ZMQError as e:
            print(f"Client connect error: {e}")
            return False, f"Connection error: {e}"

    def disconnect(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        if self.thread:
            self.thread.join(timeout=0.5)
            self.thread = None
        return True, "Disconnected"

    def send(self, message):
        if not self.socket:
            return False, "Not connected"
        try:
            self.socket.send_string(message)
            print(f"Client sent: {message[:100]}...")
            return True, "Message sent"
        except zmq.ZMQError as e:
            print(f"Client send error: {e}")
            return False, f"Send error: {e}"

    def _receive_loop(self):
        while self.running and self.socket:
            try:
                if self.socket.poll(100):
                    message = self.socket.recv_string()
                    if self.callback:
                        wx.CallAfter(self.callback, message)
            except zmq.ZMQError:
                break
            except Exception as e:
                print(f"Client receive error: {e}")


class Server:
    """SERVER socket - thread-safe async reply socket (draft API)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Server, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.running = False
            cls._instance.thread = None
            cls._instance.callback = None
            cls._instance.current_routing_id = None
            cls._instance.lock = threading.Lock()
        return cls._instance

    def set_callback(self, callback):
        self.callback = callback

    def bind(self, port):
        self.unbind()
        try:
            self.socket = self.context.socket(zmq.SERVER)
            self.socket.bind(f"tcp://*:{port}")
            self.running = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"Server bound to port {port}")
            return True, f"Bound to port {port}"
        except zmq.ZMQError as e:
            print(f"Server bind error: {e}")
            return False, f"Bind error: {e}"

    def unbind(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        if self.thread:
            self.thread.join(timeout=0.5)
            self.thread = None
        self.current_routing_id = None
        return True, "Unbound"

    def send_reply(self, message):
        with self.lock:
            if not self.socket:
                return False, "Not bound"
            if not self.current_routing_id:
                return False, "No client to reply to"
            try:
                # Use send() with routing_id for SERVER socket
                self.socket.send(message.encode("utf-8"), routing_id=self.current_routing_id)
                print(f"Server sent reply: {message[:100]}...")
                return True, "Reply sent"
            except zmq.ZMQError as e:
                print(f"Server send error: {e}")
                return False, f"Send error: {e}"

    def _receive_loop(self):
        while self.running and self.socket:
            try:
                if self.socket.poll(100):
                    # Use recv() to get Frame with routing_id
                    frame = self.socket.recv(copy=False)
                    message = bytes(frame.buffer).decode("utf-8", errors="replace")
                    with self.lock:
                        self.current_routing_id = frame.routing_id
                    if self.callback:
                        wx.CallAfter(self.callback, message)
            except zmq.ZMQError:
                break
            except Exception as e:
                print(f"Server receive error: {e}")


class Radio:
    """RADIO socket - UDP-like one-to-many with groups (draft API)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Radio, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.is_bound = False
        return cls._instance

    def bind(self, port):
        self.unbind()
        try:
            self.socket = self.context.socket(zmq.RADIO)
            self.socket.bind(f"tcp://*:{port}")
            self.is_bound = True
            print(f"Radio bound to port {port}")
            return True, f"Bound to port {port}"
        except zmq.ZMQError as e:
            print(f"Radio bind error: {e}")
            return False, f"Bind error: {e}"

    def unbind(self):
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.is_bound = False
        return True, "Unbound"

    def send_message(self, group, message):
        if not self.socket or not self.is_bound:
            return False, "Not bound"
        try:
            # RADIO sends to a group
            self.socket.send_string(message, group=group)
            print(f"Radio sent to group '{group}': {message[:100]}...")
            return True, "Message sent"
        except zmq.ZMQError as e:
            print(f"Radio send error: {e}")
            return False, f"Send error: {e}"


class Dish:
    """DISH socket - receives from RADIO groups (draft API)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Dish, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.running = False
            cls._instance.thread = None
            cls._instance.callback = None
        return cls._instance

    def set_callback(self, callback):
        self.callback = callback

    def start(self, groups, address):
        self.stop()
        try:
            self.socket = self.context.socket(zmq.DISH)
            self.socket.connect(address)
            # Join groups
            for group in groups:
                if group:
                    self.socket.join(group)
            self.running = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"Dish connected to {address}, joined groups: {groups}")
            return True, f"Connected and joined groups: {groups}"
        except zmq.ZMQError as e:
            print(f"Dish start error: {e}")
            return False, f"Connection error: {e}"

    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        if self.thread:
            self.thread.join(timeout=0.5)
            self.thread = None
        return True, "Stopped"

    def _receive_loop(self):
        while self.running and self.socket:
            try:
                if self.socket.poll(100):
                    # Use recv() to get Frame with group info
                    frame = self.socket.recv(copy=False)
                    message = bytes(frame.buffer).decode("utf-8", errors="replace")
                    group = frame.group
                    if self.callback:
                        wx.CallAfter(self.callback, group, message)
            except zmq.ZMQError:
                break
            except Exception as e:
                print(f"Dish receive error: {e}")


class Scatter:
    """SCATTER socket - round-robin to all peers (draft API)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Scatter, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.is_bound = False
        return cls._instance

    def bind(self, port):
        self.unbind()
        try:
            self.socket = self.context.socket(zmq.SCATTER)
            self.socket.bind(f"tcp://*:{port}")
            self.is_bound = True
            print(f"Scatter bound to port {port}")
            return True, f"Bound to port {port}"
        except zmq.ZMQError as e:
            print(f"Scatter bind error: {e}")
            return False, f"Bind error: {e}"

    def unbind(self):
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.is_bound = False
        return True, "Unbound"

    def send_message(self, message):
        if not self.socket or not self.is_bound:
            return False, "Not bound"
        try:
            self.socket.send_string(message)
            print(f"Scatter sent: {message[:100]}...")
            return True, "Message sent"
        except zmq.ZMQError as e:
            print(f"Scatter send error: {e}")
            return False, f"Send error: {e}"


class Gather:
    """GATHER socket - fair-queued receive from all peers (draft API)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Gather, cls).__new__(cls)
            cls._instance.context = zmq.Context()
            cls._instance.socket = None
            cls._instance.running = False
            cls._instance.thread = None
            cls._instance.callback = None
            cls._instance.message_count = 0
            cls._instance.total_bytes = 0
            cls._instance.start_time = None
        return cls._instance

    def set_callback(self, callback):
        self.callback = callback

    def start(self, address):
        self.stop()
        try:
            self.socket = self.context.socket(zmq.GATHER)
            self.socket.connect(address)
            self.running = True
            self.message_count = 0
            self.total_bytes = 0
            self.start_time = time.time()
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            print(f"Gather connected to {address}")
            return True, f"Connected to {address}"
        except zmq.ZMQError as e:
            print(f"Gather start error: {e}")
            return False, f"Connection error: {e}"

    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        if self.thread:
            self.thread.join(timeout=0.5)
            self.thread = None
        return True, "Stopped"

    def _receive_loop(self):
        while self.running and self.socket:
            try:
                if self.socket.poll(100):
                    message = self.socket.recv_string()
                    self.message_count += 1
                    self.total_bytes += len(message.encode("utf-8"))
                    if self.callback:
                        wx.CallAfter(self.callback, message)
            except zmq.ZMQError:
                break
            except Exception as e:
                print(f"Gather receive error: {e}")


# --- UI Utility Functions ---


def format_bytes(num_bytes):
    """Format bytes to human readable string."""
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    elif num_bytes >= 1024:
        return f"{num_bytes / 1024:.2f} KB"
    else:
        return f"{num_bytes} bytes"


def format_speed(bytes_per_sec):
    """Format bytes/sec to human readable string."""
    if bytes_per_sec >= 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"
    elif bytes_per_sec >= 1024:
        return f"{bytes_per_sec / 1024:.2f} KB/s"
    else:
        return f"{bytes_per_sec:.2f} B/s"


def format_json_message(message):
    """Format a message, pretty-printing JSON if valid."""
    try:
        if isinstance(message, dict):
            return json.dumps(message, indent=2)
        elif isinstance(message, str):
            parsed = json.loads(message)
            return json.dumps(parsed, indent=2)
        else:
            return str(message)
    except json.JSONDecodeError:
        return str(message)


def to_single_line(msg):
    """Convert a message to single line for display."""
    return " ".join(msg.split())


class RecentMessagesMixin:
    """Mixin class providing recent messages functionality for panels with send capability."""

    def setup_recent_messages(self, recent_msgs_key, msg_txt_ctrl, recent_list_ctrl):
        """Initialize recent messages functionality. Call this in __init__."""
        self.recent_msgs_key = recent_msgs_key
        self.msg_txt = msg_txt_ctrl
        self.recent_list = recent_list_ctrl
        self.recent_messages = []

        # Bind events
        self.recent_list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_recent_selected)
        self.recent_list.Bind(wx.EVT_RIGHT_DOWN, self._on_recent_right_click)

        # Load saved messages
        self._load_recent_messages()

    def _load_recent_messages(self):
        """Load recent messages from config."""
        msgs = Config.get_list(self.recent_msgs_key)
        for msg in reversed(msgs):
            self.recent_messages.insert(0, msg)
            self.recent_list.Insert(to_single_line(msg), 0)

    def add_to_recent(self, message):
        """Add a message to recent list if not already present."""
        if message not in self.recent_messages:
            self.recent_messages.insert(0, message)
            self.recent_list.Insert(to_single_line(message), 0)
            Config.add_to_list(self.recent_msgs_key, message)

    def _on_recent_selected(self, event):
        """Handle double-click on recent message."""
        selection = self.recent_list.GetSelection()
        if selection != wx.NOT_FOUND:
            self.msg_txt.SetValue(self.recent_messages[selection])

    def _on_recent_right_click(self, event):
        """Show context menu for recent messages."""
        item = self.recent_list.HitTest(event.GetPosition())
        if item != wx.NOT_FOUND:
            self.recent_list.SetSelection(item)

        menu = wx.Menu()
        use_item = menu.Append(wx.ID_ANY, "Use Message")
        copy_item = menu.Append(wx.ID_COPY, "Copy Message")
        del_item = menu.Append(wx.ID_DELETE, "Delete Message")

        self.Bind(wx.EVT_MENU, self._on_use_recent, use_item)
        self.Bind(wx.EVT_MENU, self._on_copy_recent, copy_item)
        self.Bind(wx.EVT_MENU, self._on_delete_recent, del_item)

        self.recent_list.PopupMenu(menu, event.GetPosition())
        menu.Destroy()

    def _on_use_recent(self, event):
        """Use selected recent message."""
        selection = self.recent_list.GetSelection()
        if selection != wx.NOT_FOUND:
            self.msg_txt.SetValue(self.recent_messages[selection])

    def _on_copy_recent(self, event):
        """Copy selected recent message to clipboard."""
        selection = self.recent_list.GetSelection()
        if selection != wx.NOT_FOUND:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(self.recent_messages[selection]))
                wx.TheClipboard.Close()

    def _on_delete_recent(self, event):
        """Delete selected recent message."""
        selection = self.recent_list.GetSelection()
        if selection != wx.NOT_FOUND:
            msg = self.recent_messages[selection]
            self.recent_messages.pop(selection)
            self.recent_list.Delete(selection)
            Config.remove_from_list(self.recent_msgs_key, msg)


class SplitterInitMixin:
    """Mixin class providing splitter initialization functionality for panels with splitters."""

    def setup_splitter_init(self, h_splitter, v_splitter=None, h_ratio=0.5, v_ratio=0.5):
        """Initialize splitter handling. Call this in __init__ after creating splitters."""
        self._h_splitter = h_splitter
        self._v_splitter = v_splitter
        self._h_ratio = h_ratio
        self._v_ratio = v_ratio
        self._splitters_initialized = False
        self.Bind(wx.EVT_SIZE, self._on_splitter_size)

    def _on_splitter_size(self, event):
        """Handle size event for splitter initialization."""
        event.Skip()
        if not self._splitters_initialized and self.GetSize().GetWidth() > 0:
            wx.CallAfter(self._do_init_splitter_positions)
            self._splitters_initialized = True

    def _do_init_splitter_positions(self):
        """Initialize splitter positions based on ratios."""
        if self._h_splitter:
            h_size = self._h_splitter.GetSize().GetWidth()
            if h_size > 0:
                self._h_splitter.SetSashPosition(int(h_size * self._h_ratio))
        if self._v_splitter:
            v_size = self._v_splitter.GetSize().GetHeight()
            if v_size > 0:
                self._v_splitter.SetSashPosition(int(v_size * self._v_ratio))


# --- UI Classes ---


class BaseComPanel(wx.Panel, RecentMessagesMixin, SplitterInitMixin):
    def __init__(self, parent, connection_address, recent_msgs_key, send_callback):
        super().__init__(parent)
        self.send_callback = send_callback

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Top Sizer (Address)
        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.address_lbl = wx.StaticText(self, label="Address:")
        self.address_txt = wx.TextCtrl(self, value=connection_address, size=(200, -1))
        self.top_sizer.Add(self.address_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.address_txt, 0, wx.EXPAND | wx.ALL, 5)

        # Create horizontal splitter for Send/Recv
        self.h_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Send Side Panel
        self.send_panel = wx.Panel(self.h_splitter)
        self.send_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_lbl = wx.StaticText(self.send_panel, label="Send:")

        # Vertical splitter for message and recent list
        self.v_splitter = wx.SplitterWindow(self.send_panel, style=wx.SP_LIVE_UPDATE)

        # Message panel (in vertical splitter)
        self.msg_panel = wx.Panel(self.v_splitter)
        self.msg_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_txt = wx.TextCtrl(
            self.msg_panel,
            value="Enter your message here",
            style=wx.TE_MULTILINE,
        )
        self.msg_panel_sizer.Add(self.send_txt, 1, wx.EXPAND)
        self.msg_panel.SetSizer(self.msg_panel_sizer)

        # Recent panel (in vertical splitter)
        self.recent_panel = wx.Panel(self.v_splitter)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_lbl = wx.StaticText(self.recent_panel, label="Recent Messages:")
        self.recent_list = wx.ListBox(self.recent_panel)
        self.recent_sizer.Add(self.recent_lbl, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.v_splitter.SplitHorizontally(self.msg_panel, self.recent_panel)
        self.v_splitter.SetSashGravity(0.5)
        self.v_splitter.SetMinimumPaneSize(80)

        self.send_sizer.Add(self.send_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.send_sizer.Add(self.v_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.send_panel.SetSizer(self.send_sizer)

        # Recv Side Panel
        self.recv_panel = wx.Panel(self.h_splitter)
        self.recv_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recv_lbl = wx.StaticText(self.recv_panel, label="Received:")
        self.recv_txt = wx.TextCtrl(
            self.recv_panel,
            value="\n\n\n\t\tReceived message will be displayed here",
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self.recv_sizer.Add(self.recv_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.recv_sizer.Add(self.recv_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.recv_panel.SetSizer(self.recv_sizer)

        # Setup horizontal splitter
        self.h_splitter.SplitVertically(self.send_panel, self.recv_panel)
        self.h_splitter.SetSashGravity(0.5)
        self.h_splitter.SetMinimumPaneSize(200)

        # Control Sizer
        self.ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.send_btn = wx.Button(self, label="Send Message")
        self.ctrl_sizer.AddStretchSpacer(1)
        self.ctrl_sizer.Add(self.send_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.main_sizer.Add(self.top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.h_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.ctrl_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        # Bindings
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send_message)

        # Setup mixins
        self.msg_txt = self.send_txt
        self.setup_recent_messages(recent_msgs_key, self.send_txt, self.recent_list)
        self.setup_splitter_init(self.h_splitter, self.v_splitter)

    def on_send_message(self, event):
        message = self.send_txt.GetValue()

        # Try to format as JSON if valid
        try:
            parsed = json.loads(message)
            formatted = json.dumps(parsed, indent=2)
            self.send_txt.SetValue(formatted)
            message = formatted
        except json.JSONDecodeError:
            pass

        if self.send_callback:
            self.send_callback(message)

        self.add_to_recent(message)

    def recv_message(self, message):
        """Display received message with JSON formatting if applicable."""
        self.recv_txt.SetValue(format_json_message(message))

    def get_connection_address(self):
        return self.address_txt.GetValue()


class RequesterPanel(BaseComPanel):
    def __init__(self, parent):
        default_addr = Config.get(CONFIG_REQUESTER_ADDRESS_KEY, "tcp://localhost:5555")
        super().__init__(parent, default_addr, CONFIG_RECENT_SENT_MSGS_REQ_KEY, self.send_request)
        Requester().set_callback(self.recv_message)

    def send_request(self, message):
        addr = self.get_connection_address()
        Config.set(CONFIG_REQUESTER_ADDRESS_KEY, addr)
        Requester().request(message, addr)


class ReplyerPanel(wx.Panel, RecentMessagesMixin, SplitterInitMixin):
    def __init__(self, parent):
        super().__init__(parent)

        # Extract port from config (remove tcp://*: prefix if present)
        default_addr = Config.get(CONFIG_REPLYER_ADDRESS_KEY, "tcp://*:5555")
        default_port = default_addr.replace("tcp://*:", "")

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.is_bound = False

        # Top Sizer (Port and Bind button)
        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.port_lbl = wx.StaticText(self, label="Port:")
        self.port_txt = wx.TextCtrl(self, value=default_port, size=(80, -1))
        self.bind_toggle_btn = wx.Button(self, label="Bind")

        self.top_sizer.Add(self.port_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.port_txt, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.bind_toggle_btn, 0, wx.CENTER | wx.ALL, 5)

        # Create horizontal splitter for Send/Recv
        self.h_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Send Side Panel
        self.send_panel = wx.Panel(self.h_splitter)
        self.send_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_lbl = wx.StaticText(self.send_panel, label="Send:")

        # Vertical splitter for message and recent list
        self.v_splitter = wx.SplitterWindow(self.send_panel, style=wx.SP_LIVE_UPDATE)

        # Message panel (in vertical splitter)
        self.msg_panel = wx.Panel(self.v_splitter)
        self.msg_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_txt = wx.TextCtrl(self.msg_panel, value="Enter your message here", style=wx.TE_MULTILINE)
        self.msg_panel_sizer.Add(self.send_txt, 1, wx.EXPAND)
        self.msg_panel.SetSizer(self.msg_panel_sizer)

        # Recent panel (in vertical splitter)
        self.recent_panel = wx.Panel(self.v_splitter)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_lbl = wx.StaticText(self.recent_panel, label="Recent Messages:")
        self.recent_list = wx.ListBox(self.recent_panel)
        self.recent_sizer.Add(self.recent_lbl, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.v_splitter.SplitHorizontally(self.msg_panel, self.recent_panel)
        self.v_splitter.SetSashGravity(0.5)
        self.v_splitter.SetMinimumPaneSize(80)

        self.send_sizer.Add(self.send_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.send_sizer.Add(self.v_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.send_panel.SetSizer(self.send_sizer)

        # Recv Side Panel
        self.recv_panel = wx.Panel(self.h_splitter)
        self.recv_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recv_lbl = wx.StaticText(self.recv_panel, label="Received:")
        self.recv_txt = wx.TextCtrl(
            self.recv_panel,
            value="\n\n\n\t\tReceived message will be displayed here",
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self.recv_sizer.Add(self.recv_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.recv_sizer.Add(self.recv_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.recv_panel.SetSizer(self.recv_sizer)

        # Setup horizontal splitter
        self.h_splitter.SplitVertically(self.send_panel, self.recv_panel)
        self.h_splitter.SetSashGravity(0.5)
        self.h_splitter.SetMinimumPaneSize(200)

        # Control Sizer
        self.ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.send_btn = wx.Button(self, label="Send Message")
        self.send_btn.Enable(False)
        self.ctrl_sizer.AddStretchSpacer(1)
        self.ctrl_sizer.Add(self.send_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.main_sizer.Add(self.top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.h_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.ctrl_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        # Bindings
        self.bind_toggle_btn.Bind(wx.EVT_BUTTON, self.on_bind_toggle)
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send_message)

        # Setup mixins
        self.msg_txt = self.send_txt
        self.setup_recent_messages(CONFIG_RECENT_SENT_MSGS_REP_KEY, self.send_txt, self.recent_list)
        self.setup_splitter_init(self.h_splitter, self.v_splitter)

        Replyer().set_callback(self.on_request_received)

    def on_bind_toggle(self, event):
        if self.is_bound:
            success, message = Replyer().unbind()
            if success:
                self.is_bound = False
                self.bind_toggle_btn.SetLabel("Bind")
                self.send_btn.Enable(False)
                self.port_txt.Enable(True)
            else:
                wx.MessageBox(message, "Unbind Error", wx.OK | wx.ICON_ERROR)
        else:
            port = self.port_txt.GetValue().strip()
            if not port:
                wx.MessageBox("Please enter a port number", "Input Error", wx.OK | wx.ICON_WARNING)
                return
            if not port.isdigit():
                wx.MessageBox("Port must be a number", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            addr = f"tcp://*:{port}"
            Config.set(CONFIG_REPLYER_ADDRESS_KEY, addr)
            success, message = Replyer().bind(addr)
            if success:
                self.is_bound = True
                self.bind_toggle_btn.SetLabel("Unbind")
                self.send_btn.Enable(True)
                self.port_txt.Enable(False)
            else:
                wx.MessageBox(message, "Bind Error", wx.OK | wx.ICON_ERROR)

    def on_send_message(self, event):
        message = self.send_txt.GetValue()
        try:
            parsed = json.loads(message)
            formatted = json.dumps(parsed, indent=2)
            self.send_txt.SetValue(formatted)
            message = formatted
        except json.JSONDecodeError:
            pass

        Replyer().send_reply(message)
        self.add_to_recent(message)

    def recv_message(self, message):
        self.recv_txt.SetValue(format_json_message(message))

    def on_request_received(self, message):
        self.recv_message(message)


class PublisherPanel(wx.Panel, RecentMessagesMixin, SplitterInitMixin):
    def __init__(self, parent):
        super().__init__(parent)
        self.is_bound = False

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Controls
        self.controls_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.port_lbl = wx.StaticText(self, label="Port:")
        self.port_txt = wx.TextCtrl(self, value=Config.get(CONFIG_PUBLISHER_PORT_KEY, "5556"), size=(80, -1))
        self.bind_toggle_btn = wx.Button(self, label="Bind")
        self.topic_lbl = wx.StaticText(self, label="Topic:")
        self.topic_txt = wx.TextCtrl(self, value=Config.get(CONFIG_PUBLISHER_TOPIC_KEY, "test"), size=(100, -1))

        self.controls_sizer.Add(self.port_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.port_txt, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.bind_toggle_btn, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.topic_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.topic_txt, 0, wx.CENTER | wx.ALL, 5)

        # Create splitter for message area and recent list
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Message Area Panel
        self.msg_panel = wx.Panel(self.splitter)
        self.msg_sizer = wx.BoxSizer(wx.VERTICAL)
        self.msg_lbl = wx.StaticText(self.msg_panel, label="Message:")
        self.msg_txt = wx.TextCtrl(self.msg_panel, value="Enter your message here", style=wx.TE_MULTILINE)
        self.msg_sizer.Add(self.msg_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.msg_sizer.Add(self.msg_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.msg_panel.SetSizer(self.msg_sizer)

        # Recent List Panel
        self.recent_panel = wx.Panel(self.splitter)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_lbl = wx.StaticText(self.recent_panel, label="Recent Messages:")
        self.recent_list = wx.ListBox(self.recent_panel)
        self.recent_sizer.Add(self.recent_lbl, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.splitter.SplitHorizontally(self.msg_panel, self.recent_panel)
        self.splitter.SetSashGravity(0.5)
        self.splitter.SetMinimumPaneSize(80)

        # Publish Button
        self.pub_btn = wx.Button(self, label="Publish Message")
        self.pub_btn.Enable(False)

        self.main_sizer.Add(self.controls_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.pub_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.bind_toggle_btn.Bind(wx.EVT_BUTTON, self.on_bind_toggle)
        self.pub_btn.Bind(wx.EVT_BUTTON, self.on_publish)

        # Setup mixins - use v_splitter parameter since it's a vertical split
        self.setup_recent_messages(CONFIG_RECENT_SENT_MSGS_PUB_KEY, self.msg_txt, self.recent_list)
        self.setup_splitter_init(None, self.splitter)

    def on_bind_toggle(self, event):
        if self.is_bound:
            success, message = Publisher().unbind()
            if success:
                self.is_bound = False
                self.bind_toggle_btn.SetLabel("Bind")
                self.pub_btn.Enable(False)
                self.port_txt.Enable(True)
            else:
                wx.MessageBox(message, "Unbind Error", wx.OK | wx.ICON_ERROR)
        else:
            port = self.port_txt.GetValue().strip()
            if not port:
                wx.MessageBox("Please enter a port number", "Input Error", wx.OK | wx.ICON_WARNING)
                return
            if not port.isdigit():
                wx.MessageBox("Port must be a number", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            success, message = Publisher().bind(port)
            if success:
                Config.set(CONFIG_PUBLISHER_PORT_KEY, port)
                self.is_bound = True
                self.bind_toggle_btn.SetLabel("Unbind")
                self.pub_btn.Enable(True)
                self.port_txt.Enable(False)
            else:
                wx.MessageBox(message, "Bind Error", wx.OK | wx.ICON_ERROR)

    def on_publish(self, event):
        topic = self.topic_txt.GetValue().strip()
        message = self.msg_txt.GetValue()

        if not topic:
            wx.MessageBox("Please enter a topic", "Input Error", wx.OK | wx.ICON_WARNING)
            return

        try:
            parsed = json.loads(message)
            formatted = json.dumps(parsed, indent=2)
            self.msg_txt.SetValue(formatted)
            message = formatted
        except json.JSONDecodeError:
            pass

        success, msg = Publisher().send_message(topic, message)
        if not success:
            wx.MessageBox(msg, "Publish Error", wx.OK | wx.ICON_ERROR)
            return

        Config.set(CONFIG_PUBLISHER_TOPIC_KEY, topic)
        self.add_to_recent(message)


class TopicFrame(wx.Frame):
    # Maximum message size to display (100KB)
    MAX_DISPLAY_SIZE = 100 * 1024

    def __init__(self, parent, topic):
        super().__init__(parent, title=f"Topic: {topic}", size=(400, 300))
        self.topic = topic
        self.panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.text = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 5)
        self.panel.SetSizer(self.sizer)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        # Throttle updates to avoid UI freezing
        self.pending_message = None
        self.update_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_update_timer, self.update_timer)

        self.Show()

    def update_message(self, message):
        """Queue a message update (throttled to avoid UI freezing)."""
        self.pending_message = message
        # Only start timer if not already running
        if not self.update_timer.IsRunning():
            self.update_timer.StartOnce(50)  # 50ms delay, updates max 20 times/sec

    def on_update_timer(self, event):
        """Actually update the display with the pending message."""
        if self.pending_message is None:
            return

        message = self.pending_message
        self.pending_message = None

        try:
            if isinstance(message, dict):
                display_text = json.dumps(message, indent=2)
            elif isinstance(message, str):
                # Try to parse and pretty-print JSON
                try:
                    parsed = json.loads(message)
                    display_text = json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    display_text = message
            else:
                display_text = str(message)

            # Truncate if too large to prevent UI freeze
            if len(display_text) > self.MAX_DISPLAY_SIZE:
                display_text = display_text[: self.MAX_DISPLAY_SIZE] + f"\n\n... [Truncated - message is {len(display_text)} bytes]"

            self.text.SetValue(display_text)
        except Exception as e:
            self.text.SetValue(f"Error displaying message: {e}")

    def on_close(self, event):
        if self.update_timer.IsRunning():
            self.update_timer.Stop()
        self.Destroy()


class SubscriberPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.topic_frames = {}
        self.is_running = False

        # Statistics tracking
        self.topic_stats = {}  # {topic: {"count": int, "bytes": int, "first_time": float, "last_time": float}}
        self.start_time = None

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Controls
        self.controls_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.addr_lbl = wx.StaticText(self, label="Address:")
        self.addr_txt = wx.TextCtrl(
            self,
            value=Config.get(CONFIG_SUBSCRIBER_ADDRESS_KEY, "tcp://localhost:5556"),
            size=(200, -1),
        )
        self.topic_lbl = wx.StaticText(self, label="Topics (comma sep):")
        self.topic_txt = wx.TextCtrl(self, value=Config.get(CONFIG_SUBSCRIBER_TOPICS_KEY, ""), size=(200, -1))

        self.toggle_btn = wx.Button(self, label="Start")

        self.controls_sizer.Add(self.addr_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.addr_txt, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.topic_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.topic_txt, 1, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.toggle_btn, 0, wx.CENTER | wx.ALL, 5)

        # Create a splitter for messages and statistics
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Message List Panel
        self.msg_panel = wx.Panel(self.splitter)
        self.msg_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.msg_list = wx.dataview.DataViewListCtrl(self.msg_panel)
        self.msg_list.AppendTextColumn("Topic", width=100)
        self.msg_list.AppendTextColumn("Message", width=400)
        self.msg_panel_sizer.Add(self.msg_list, 1, wx.EXPAND)
        self.msg_panel.SetSizer(self.msg_panel_sizer)

        # Statistics Panel
        self.stats_panel = wx.Panel(self.splitter)
        self.stats_sizer = wx.BoxSizer(wx.VERTICAL)

        # Stats header with reset button
        stats_header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        stats_header = wx.StaticText(self.stats_panel, label="Statistics")
        stats_header.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        stats_header_sizer.Add(stats_header, 0, wx.CENTER | wx.ALL, 5)
        stats_header_sizer.AddStretchSpacer(1)
        self.reset_stats_btn = wx.Button(self.stats_panel, label="Reset Stats")
        stats_header_sizer.Add(self.reset_stats_btn, 0, wx.ALL, 2)
        self.stats_sizer.Add(stats_header_sizer, 0, wx.EXPAND | wx.ALL, 2)

        # Totals section title
        totals_title = wx.StaticText(self.stats_panel, label="Totals")
        totals_title.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.stats_sizer.Add(totals_title, 0, wx.LEFT | wx.TOP, 5)

        # Summary stats grid
        summary_grid = wx.FlexGridSizer(2, 5, 5, 20)  # 2 rows, 5 cols, vgap=5, hgap=20
        # Make all columns growable with equal proportion
        for i in range(5):
            summary_grid.AddGrowableCol(i, 1)

        # Row 1: Labels
        for label in ["Messages", "Data Size", "Topics", "Rate", "Speed"]:
            lbl = wx.StaticText(self.stats_panel, label=label)
            lbl.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            summary_grid.Add(lbl, 0, wx.ALIGN_CENTER)

        # Row 2: Values
        self.summary_msgs = wx.StaticText(self.stats_panel, label="0")
        self.summary_bytes = wx.StaticText(self.stats_panel, label="0 bytes")
        self.summary_topics = wx.StaticText(self.stats_panel, label="0")
        self.summary_rate = wx.StaticText(self.stats_panel, label="-")
        self.summary_speed = wx.StaticText(self.stats_panel, label="-")

        summary_grid.Add(self.summary_msgs, 0, wx.ALIGN_CENTER)
        summary_grid.Add(self.summary_bytes, 0, wx.ALIGN_CENTER)
        summary_grid.Add(self.summary_topics, 0, wx.ALIGN_CENTER)
        summary_grid.Add(self.summary_rate, 0, wx.ALIGN_CENTER)
        summary_grid.Add(self.summary_speed, 0, wx.ALIGN_CENTER)

        self.stats_sizer.Add(summary_grid, 0, wx.EXPAND | wx.ALL, 5)

        # Per-Topic section title
        per_topic_title = wx.StaticText(self.stats_panel, label="Per Topic")
        per_topic_title.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.stats_sizer.Add(per_topic_title, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 5)

        # Stats list
        self.stats_list = wx.dataview.DataViewListCtrl(self.stats_panel)
        self.stats_list.AppendTextColumn("Topic", width=150)
        self.stats_list.AppendTextColumn("Count", width=100)
        self.stats_list.AppendTextColumn("Bytes", width=120)
        self.stats_list.AppendTextColumn("Rate (msg/s)", width=120)
        self.stats_list.AppendTextColumn("Last Received", width=150)
        self.stats_sizer.Add(self.stats_list, 1, wx.EXPAND)

        self.stats_panel.SetSizer(self.stats_sizer)

        # Setup splitter
        self.splitter.SplitHorizontally(self.msg_panel, self.stats_panel)
        self.splitter.SetSashGravity(0.5)  # Messages get 50% of space
        self.splitter.SetMinimumPaneSize(100)

        self.main_sizer.Add(self.controls_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.splitter, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.toggle_btn.Bind(wx.EVT_BUTTON, self.on_toggle)
        self.reset_stats_btn.Bind(wx.EVT_BUTTON, self.on_reset_stats)
        self.msg_list.Bind(wx.dataview.EVT_DATAVIEW_ITEM_ACTIVATED, self.on_item_activated)
        self.msg_list.Bind(wx.dataview.EVT_DATAVIEW_ITEM_CONTEXT_MENU, self.on_msg_list_right_click)
        self.Bind(wx.EVT_SIZE, self.on_size)

        self._splitter_initialized = False

        Subscriber().set_callback(self.on_message_received)

    def on_size(self, event):
        event.Skip()
        if not self._splitter_initialized and self.GetSize().GetWidth() > 0:
            wx.CallAfter(self._init_splitter_position)
            self._splitter_initialized = True

    def _init_splitter_position(self):
        # Set splitter to 50%
        size = self.splitter.GetSize().GetHeight()
        if size > 0:
            self.splitter.SetSashPosition(size // 2)
        # Force stats panel to re-layout for proper grid alignment
        self.stats_panel.Layout()

    def on_msg_list_right_click(self, event):
        """Show context menu for message list."""
        menu = wx.Menu()
        clear_item = menu.Append(wx.ID_ANY, "Clear Messages")
        self.Bind(wx.EVT_MENU, self.on_clear_messages, clear_item)
        self.PopupMenu(menu)
        menu.Destroy()

    def on_clear_messages(self, event):
        """Clear all messages from the list."""
        self.msg_list.DeleteAllItems()

    def on_reset_stats(self, event):
        """Reset all statistics."""
        self.topic_stats = {}
        self.start_time = time.time() if self.is_running else None
        self.stats_list.DeleteAllItems()
        self.update_summary_stats()

    def on_toggle(self, event):
        if self.is_running:
            # Stop
            Subscriber().stop()
            self.is_running = False
            self.toggle_btn.SetLabel("Start")
            self.addr_txt.Enable(True)
            self.topic_txt.Enable(True)
        else:
            # Start
            addr = self.addr_txt.GetValue().strip()
            topics_str = self.topic_txt.GetValue().strip()

            if not addr:
                wx.MessageBox("Please enter an address", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            # If topics_str is empty, subscribe to all (empty topic filter)
            if topics_str:
                topics = [t.strip() for t in topics_str.split(",") if t.strip()]
            else:
                topics = [""]  # Empty string subscribes to all messages

            Config.set(CONFIG_SUBSCRIBER_ADDRESS_KEY, addr)
            Config.set(CONFIG_SUBSCRIBER_TOPICS_KEY, topics_str)

            success, message = Subscriber().start(topics, addr)
            if success:
                self.is_running = True
                self.start_time = time.time()
                self.toggle_btn.SetLabel("Stop")
                self.addr_txt.Enable(False)
                self.topic_txt.Enable(False)
                # Force layout to fix grid alignment
                wx.CallAfter(self.stats_panel.Layout)
            else:
                wx.MessageBox(message, "Connection Error", wx.OK | wx.ICON_ERROR)

    def update_summary_stats(self):
        """Update the summary statistics labels."""
        total_msgs = sum(s["count"] for s in self.topic_stats.values())
        total_bytes = sum(s["bytes"] for s in self.topic_stats.values())
        total_topics = len(self.topic_stats)

        # Calculate overall rate and speed
        rate_str = "-"
        speed_str = "-"
        if self.start_time and self.topic_stats:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                rate_str = f"{total_msgs / elapsed:.2f} msg/s"
                speed_str = format_speed(total_bytes / elapsed)

        self.summary_msgs.SetLabel(str(total_msgs))
        self.summary_bytes.SetLabel(format_bytes(total_bytes))
        self.summary_topics.SetLabel(str(total_topics))
        self.summary_rate.SetLabel(rate_str)
        self.summary_speed.SetLabel(speed_str)

    def update_topic_stats_display(self, topic):
        """Update the statistics list for a specific topic."""
        stats = self.topic_stats.get(topic)
        if not stats:
            return

        # Calculate rate
        elapsed = stats["last_time"] - stats["first_time"]
        rate_str = f"{stats['count'] / elapsed:.2f}" if elapsed > 0 else "-"
        bytes_str = format_bytes(stats["bytes"]).replace(" bytes", " B")
        last_time = time.strftime("%H:%M:%S", time.localtime(stats["last_time"]))

        # Find or add row
        found = False
        for i in range(self.stats_list.GetItemCount()):
            if self.stats_list.GetTextValue(i, 0) == topic:
                self.stats_list.SetTextValue(str(stats["count"]), i, 1)
                self.stats_list.SetTextValue(bytes_str, i, 2)
                self.stats_list.SetTextValue(rate_str, i, 3)
                self.stats_list.SetTextValue(last_time, i, 4)
                found = True
                break

        if not found:
            self.stats_list.AppendItem([topic, str(stats["count"]), bytes_str, rate_str, last_time])

    def on_message_received(self, topic, message):
        # Update statistics
        current_time = time.time()
        msg_str = json.dumps(message) if isinstance(message, dict) else str(message)
        msg_bytes = len(msg_str.encode("utf-8"))

        if topic not in self.topic_stats:
            self.topic_stats[topic] = {"count": 0, "bytes": 0, "first_time": current_time, "last_time": current_time}

        self.topic_stats[topic]["count"] += 1
        self.topic_stats[topic]["bytes"] += msg_bytes
        self.topic_stats[topic]["last_time"] = current_time

        # Update stats display
        self.update_topic_stats_display(topic)
        self.update_summary_stats()

        # Update message list
        # Check if topic exists in list, update it, or add new
        found = False

        for i in range(self.msg_list.GetItemCount()):
            if self.msg_list.GetTextValue(i, 0) == topic:
                self.msg_list.SetTextValue(msg_str, i, 1)
                found = True
                break

        if not found:
            self.msg_list.AppendItem([topic, msg_str])

        # Update topic frame if exists
        if topic in self.topic_frames:
            if self.topic_frames[topic]:
                self.topic_frames[topic].update_message(message)
            else:
                del self.topic_frames[topic]

    def on_item_activated(self, event):
        selection = self.msg_list.GetSelectedRow()
        if selection != wx.NOT_FOUND:
            topic = self.msg_list.GetTextValue(selection, 0)
            msg_str = self.msg_list.GetTextValue(selection, 1)

            if topic not in self.topic_frames or not self.topic_frames[topic]:
                self.topic_frames[topic] = TopicFrame(self, topic)

            self.topic_frames[topic].update_message(msg_str)
            self.topic_frames[topic].Raise()


class PusherPanel(wx.Panel, RecentMessagesMixin, SplitterInitMixin):
    """UI Panel for PUSH socket - sends messages to connected PULLers."""

    def __init__(self, parent):
        super().__init__(parent)
        self.is_bound = False

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Controls
        self.controls_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.port_lbl = wx.StaticText(self, label="Port:")
        self.port_txt = wx.TextCtrl(self, value=Config.get(CONFIG_PUSHER_PORT_KEY, "5557"), size=(80, -1))
        self.bind_toggle_btn = wx.Button(self, label="Bind")

        self.controls_sizer.Add(self.port_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.port_txt, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.bind_toggle_btn, 0, wx.CENTER | wx.ALL, 5)

        # Create splitter for message area and recent list
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Message Area Panel
        self.msg_panel = wx.Panel(self.splitter)
        self.msg_sizer = wx.BoxSizer(wx.VERTICAL)
        self.msg_lbl = wx.StaticText(self.msg_panel, label="Message:")
        self.msg_txt = wx.TextCtrl(self.msg_panel, value="Enter your message here", style=wx.TE_MULTILINE)
        self.msg_sizer.Add(self.msg_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.msg_sizer.Add(self.msg_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.msg_panel.SetSizer(self.msg_sizer)

        # Recent List Panel
        self.recent_panel = wx.Panel(self.splitter)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_lbl = wx.StaticText(self.recent_panel, label="Recent Messages:")
        self.recent_list = wx.ListBox(self.recent_panel)
        self.recent_sizer.Add(self.recent_lbl, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.splitter.SplitHorizontally(self.msg_panel, self.recent_panel)
        self.splitter.SetSashGravity(0.5)
        self.splitter.SetMinimumPaneSize(80)

        # Push Button
        self.push_btn = wx.Button(self, label="Push Message")
        self.push_btn.Enable(False)

        self.main_sizer.Add(self.controls_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.push_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.bind_toggle_btn.Bind(wx.EVT_BUTTON, self.on_bind_toggle)
        self.push_btn.Bind(wx.EVT_BUTTON, self.on_push)

        # Setup mixins
        self.setup_recent_messages(CONFIG_RECENT_SENT_MSGS_PUSH_KEY, self.msg_txt, self.recent_list)
        self.setup_splitter_init(None, self.splitter)

    def on_bind_toggle(self, event):
        if self.is_bound:
            success, message = Pusher().unbind()
            if success:
                self.is_bound = False
                self.bind_toggle_btn.SetLabel("Bind")
                self.push_btn.Enable(False)
                self.port_txt.Enable(True)
            else:
                wx.MessageBox(message, "Unbind Error", wx.OK | wx.ICON_ERROR)
        else:
            port = self.port_txt.GetValue().strip()
            if not port:
                wx.MessageBox("Please enter a port number", "Input Error", wx.OK | wx.ICON_WARNING)
                return
            if not port.isdigit():
                wx.MessageBox("Port must be a number", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            success, message = Pusher().bind(port)
            if success:
                Config.set(CONFIG_PUSHER_PORT_KEY, port)
                self.is_bound = True
                self.bind_toggle_btn.SetLabel("Unbind")
                self.push_btn.Enable(True)
                self.port_txt.Enable(False)
            else:
                wx.MessageBox(message, "Bind Error", wx.OK | wx.ICON_ERROR)

    def on_push(self, event):
        message = self.msg_txt.GetValue()
        try:
            parsed = json.loads(message)
            formatted = json.dumps(parsed, indent=2)
            self.msg_txt.SetValue(formatted)
            message = formatted
        except json.JSONDecodeError:
            pass

        success, msg = Pusher().send_message(message)
        if not success:
            wx.MessageBox(msg, "Push Error", wx.OK | wx.ICON_ERROR)
            return

        self.add_to_recent(message)


class PullerPanel(wx.Panel, SplitterInitMixin):
    """UI Panel for PULL socket - receives messages from PUSHers."""

    def __init__(self, parent):
        super().__init__(parent)
        self.is_running = False
        self.message_count = 0
        self.total_bytes = 0
        self.start_time = None

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Controls
        self.controls_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.addr_lbl = wx.StaticText(self, label="Address:")
        self.addr_txt = wx.TextCtrl(
            self,
            value=Config.get(CONFIG_PULLER_ADDRESS_KEY, "tcp://localhost:5557"),
            size=(200, -1),
        )
        self.toggle_btn = wx.Button(self, label="Start")

        self.controls_sizer.Add(self.addr_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.addr_txt, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.toggle_btn, 0, wx.CENTER | wx.ALL, 5)

        # Create splitter for messages and stats
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Message List Panel
        self.msg_panel = wx.Panel(self.splitter)
        self.msg_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.msg_lbl = wx.StaticText(self.msg_panel, label="Received Messages:")
        self.msg_list = wx.dataview.DataViewListCtrl(self.msg_panel)
        self.msg_list.AppendTextColumn("#", width=50)
        self.msg_list.AppendTextColumn("Message", width=500)
        self.msg_panel_sizer.Add(self.msg_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.msg_panel_sizer.Add(self.msg_list, 1, wx.EXPAND)
        self.msg_panel.SetSizer(self.msg_panel_sizer)

        # Stats Panel
        self.stats_panel = wx.Panel(self.splitter)
        self.stats_sizer = wx.BoxSizer(wx.VERTICAL)
        stats_header = wx.StaticText(self.stats_panel, label="Statistics")
        stats_header.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.stats_sizer.Add(stats_header, 0, wx.ALL, 5)

        stats_grid = wx.FlexGridSizer(2, 5, 5, 20)
        for i in range(5):
            stats_grid.AddGrowableCol(i, 1)

        for label in ["Messages", "Data Size", "Rate", "Speed", "Running Time"]:
            lbl = wx.StaticText(self.stats_panel, label=label)
            lbl.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            stats_grid.Add(lbl, 0, wx.ALIGN_CENTER)

        self.stats_msgs = wx.StaticText(self.stats_panel, label="0")
        self.stats_bytes = wx.StaticText(self.stats_panel, label="0 bytes")
        self.stats_rate = wx.StaticText(self.stats_panel, label="-")
        self.stats_speed = wx.StaticText(self.stats_panel, label="-")
        self.stats_time = wx.StaticText(self.stats_panel, label="-")

        stats_grid.Add(self.stats_msgs, 0, wx.ALIGN_CENTER)
        stats_grid.Add(self.stats_bytes, 0, wx.ALIGN_CENTER)
        stats_grid.Add(self.stats_rate, 0, wx.ALIGN_CENTER)
        stats_grid.Add(self.stats_speed, 0, wx.ALIGN_CENTER)
        stats_grid.Add(self.stats_time, 0, wx.ALIGN_CENTER)

        self.stats_sizer.Add(stats_grid, 0, wx.EXPAND | wx.ALL, 5)
        self.stats_panel.SetSizer(self.stats_sizer)

        self.splitter.SplitHorizontally(self.msg_panel, self.stats_panel)
        self.splitter.SetSashGravity(0.7)
        self.splitter.SetMinimumPaneSize(80)

        self.main_sizer.Add(self.controls_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.splitter, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.toggle_btn.Bind(wx.EVT_BUTTON, self.on_toggle)
        self.msg_list.Bind(wx.dataview.EVT_DATAVIEW_ITEM_CONTEXT_MENU, self.on_msg_list_right_click)

        # Setup mixin with 0.7 ratio
        self.setup_splitter_init(None, self.splitter, v_ratio=0.7)
        Puller().set_callback(self.on_message_received)

    def on_toggle(self, event):
        if self.is_running:
            Puller().stop()
            self.is_running = False
            self.toggle_btn.SetLabel("Start")
            self.addr_txt.Enable(True)
        else:
            addr = self.addr_txt.GetValue().strip()
            if not addr:
                wx.MessageBox("Please enter an address", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            Config.set(CONFIG_PULLER_ADDRESS_KEY, addr)
            success, message = Puller().start(addr)
            if success:
                self.is_running = True
                self.start_time = time.time()
                self.message_count = 0
                self.total_bytes = 0
                self.toggle_btn.SetLabel("Stop")
                self.addr_txt.Enable(False)
            else:
                wx.MessageBox(message, "Connection Error", wx.OK | wx.ICON_ERROR)

    def on_message_received(self, message):
        self.message_count += 1
        msg_str = json.dumps(message) if isinstance(message, dict) else str(message)
        self.total_bytes += len(msg_str.encode("utf-8"))
        self.msg_list.AppendItem([str(self.message_count), msg_str])
        self.update_stats()

    def update_stats(self):
        self.stats_msgs.SetLabel(str(self.message_count))
        self.stats_bytes.SetLabel(format_bytes(self.total_bytes))
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                rate = self.message_count / elapsed
                self.stats_rate.SetLabel(f"{rate:.2f} msg/s")
                self.stats_speed.SetLabel(format_speed(self.total_bytes / elapsed))
                mins, secs = divmod(int(elapsed), 60)
                self.stats_time.SetLabel(f"{mins}m {secs}s")

    def on_msg_list_right_click(self, event):
        menu = wx.Menu()
        clear_item = menu.Append(wx.ID_ANY, "Clear Messages")
        self.Bind(wx.EVT_MENU, self.on_clear_messages, clear_item)
        self.PopupMenu(menu)
        menu.Destroy()

    def on_clear_messages(self, event):
        self.msg_list.DeleteAllItems()
        self.message_count = 0
        self.start_time = time.time() if self.is_running else None
        self.update_stats()


class DealerPanel(wx.Panel, RecentMessagesMixin, SplitterInitMixin):
    """UI Panel for DEALER socket - async REQ that can send multiple requests."""

    def __init__(self, parent):
        super().__init__(parent)
        self.is_connected = False

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Top Sizer (Address)
        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.address_lbl = wx.StaticText(self, label="Address:")
        self.address_txt = wx.TextCtrl(
            self,
            value=Config.get(CONFIG_DEALER_ADDRESS_KEY, "tcp://localhost:5558"),
            size=(200, -1),
        )
        self.connect_toggle_btn = wx.Button(self, label="Connect")

        self.top_sizer.Add(self.address_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.address_txt, 0, wx.EXPAND | wx.ALL, 5)
        self.top_sizer.Add(self.connect_toggle_btn, 0, wx.CENTER | wx.ALL, 5)

        # Create horizontal splitter for Send/Recv
        self.h_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Send Side Panel
        self.send_panel = wx.Panel(self.h_splitter)
        self.send_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_lbl = wx.StaticText(self.send_panel, label="Send:")

        self.v_splitter = wx.SplitterWindow(self.send_panel, style=wx.SP_LIVE_UPDATE)

        self.msg_panel = wx.Panel(self.v_splitter)
        self.msg_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_txt = wx.TextCtrl(self.msg_panel, value="Enter your message here", style=wx.TE_MULTILINE)
        self.msg_panel_sizer.Add(self.send_txt, 1, wx.EXPAND)
        self.msg_panel.SetSizer(self.msg_panel_sizer)

        self.recent_panel = wx.Panel(self.v_splitter)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_lbl = wx.StaticText(self.recent_panel, label="Recent Messages:")
        self.recent_list = wx.ListBox(self.recent_panel)
        self.recent_sizer.Add(self.recent_lbl, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.v_splitter.SplitHorizontally(self.msg_panel, self.recent_panel)
        self.v_splitter.SetSashGravity(0.5)
        self.v_splitter.SetMinimumPaneSize(80)

        self.send_sizer.Add(self.send_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.send_sizer.Add(self.v_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.send_panel.SetSizer(self.send_sizer)

        # Recv Side Panel
        self.recv_panel = wx.Panel(self.h_splitter)
        self.recv_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recv_lbl = wx.StaticText(self.recv_panel, label="Received:")
        self.recv_txt = wx.TextCtrl(
            self.recv_panel,
            value="\n\n\n\t\tReceived message will be displayed here",
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self.recv_sizer.Add(self.recv_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.recv_sizer.Add(self.recv_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.recv_panel.SetSizer(self.recv_sizer)

        self.h_splitter.SplitVertically(self.send_panel, self.recv_panel)
        self.h_splitter.SetSashGravity(0.5)
        self.h_splitter.SetMinimumPaneSize(200)

        # Control Sizer
        self.ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.send_btn = wx.Button(self, label="Send Message")
        self.send_btn.Enable(False)
        self.ctrl_sizer.AddStretchSpacer(1)
        self.ctrl_sizer.Add(self.send_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.main_sizer.Add(self.top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.h_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.ctrl_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.connect_toggle_btn.Bind(wx.EVT_BUTTON, self.on_connect_toggle)
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send_message)

        # Setup mixins
        self.setup_recent_messages(CONFIG_RECENT_SENT_MSGS_DEALER_KEY, self.send_txt, self.recent_list)
        self.setup_splitter_init(self.h_splitter, self.v_splitter)
        Dealer().set_callback(self.recv_message)

    def on_connect_toggle(self, event):
        if self.is_connected:
            Dealer().disconnect()
            self.is_connected = False
            self.connect_toggle_btn.SetLabel("Connect")
            self.send_btn.Enable(False)
            self.address_txt.Enable(True)
        else:
            addr = self.address_txt.GetValue().strip()
            if not addr:
                wx.MessageBox("Please enter an address", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            Config.set(CONFIG_DEALER_ADDRESS_KEY, addr)
            success, message = Dealer().connect(addr)
            if success:
                self.is_connected = True
                self.connect_toggle_btn.SetLabel("Disconnect")
                self.send_btn.Enable(True)
                self.address_txt.Enable(False)
            else:
                wx.MessageBox(message, "Connection Error", wx.OK | wx.ICON_ERROR)

    def on_send_message(self, event):
        message = self.send_txt.GetValue()

        try:
            parsed = json.loads(message)
            formatted = json.dumps(parsed, indent=2)
            self.send_txt.SetValue(formatted)
            message = formatted
        except json.JSONDecodeError:
            pass

        success, msg = Dealer().send(message)
        if not success:
            wx.MessageBox(msg, "Send Error", wx.OK | wx.ICON_ERROR)
            return

        self.add_to_recent(message)

    def recv_message(self, message):
        try:
            if isinstance(message, str):
                parsed = json.loads(message)
                self.recv_txt.SetValue(json.dumps(parsed, indent=2))
            elif isinstance(message, dict):
                self.recv_txt.SetValue(json.dumps(message, indent=2))
            else:
                self.recv_txt.SetValue(str(message))
        except json.JSONDecodeError:
            self.recv_txt.SetValue(str(message))


class RouterPanel(wx.Panel, RecentMessagesMixin, SplitterInitMixin):
    """UI Panel for ROUTER socket - async REP that handles multiple clients."""

    def __init__(self, parent):
        super().__init__(parent)
        self.is_bound = False

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Top Sizer (Port and Bind button)
        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.port_lbl = wx.StaticText(self, label="Port:")
        default_port = Config.get(CONFIG_ROUTER_PORT_KEY, "5558")
        self.port_txt = wx.TextCtrl(self, value=default_port, size=(80, -1))
        self.bind_toggle_btn = wx.Button(self, label="Bind")

        self.top_sizer.Add(self.port_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.port_txt, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.bind_toggle_btn, 0, wx.CENTER | wx.ALL, 5)

        # Create horizontal splitter for Send/Recv
        self.h_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Send Side Panel
        self.send_panel = wx.Panel(self.h_splitter)
        self.send_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_lbl = wx.StaticText(self.send_panel, label="Reply:")

        self.v_splitter = wx.SplitterWindow(self.send_panel, style=wx.SP_LIVE_UPDATE)

        self.msg_panel = wx.Panel(self.v_splitter)
        self.msg_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_txt = wx.TextCtrl(self.msg_panel, value="Enter your reply here", style=wx.TE_MULTILINE)
        self.msg_panel_sizer.Add(self.send_txt, 1, wx.EXPAND)
        self.msg_panel.SetSizer(self.msg_panel_sizer)

        self.recent_panel = wx.Panel(self.v_splitter)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_lbl = wx.StaticText(self.recent_panel, label="Recent Replies:")
        self.recent_list = wx.ListBox(self.recent_panel)
        self.recent_sizer.Add(self.recent_lbl, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.v_splitter.SplitHorizontally(self.msg_panel, self.recent_panel)
        self.v_splitter.SetSashGravity(0.5)
        self.v_splitter.SetMinimumPaneSize(80)

        self.send_sizer.Add(self.send_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.send_sizer.Add(self.v_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.send_panel.SetSizer(self.send_sizer)

        # Recv Side Panel
        self.recv_panel = wx.Panel(self.h_splitter)
        self.recv_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recv_lbl = wx.StaticText(self.recv_panel, label="Received Request:")
        self.recv_txt = wx.TextCtrl(
            self.recv_panel,
            value="\n\n\n\t\tReceived request will be displayed here",
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self.recv_sizer.Add(self.recv_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.recv_sizer.Add(self.recv_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.recv_panel.SetSizer(self.recv_sizer)

        self.h_splitter.SplitVertically(self.send_panel, self.recv_panel)
        self.h_splitter.SetSashGravity(0.5)
        self.h_splitter.SetMinimumPaneSize(200)

        # Control Sizer
        self.ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.send_btn = wx.Button(self, label="Send Reply")
        self.send_btn.Enable(False)
        self.ctrl_sizer.AddStretchSpacer(1)
        self.ctrl_sizer.Add(self.send_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.main_sizer.Add(self.top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.h_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.ctrl_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.bind_toggle_btn.Bind(wx.EVT_BUTTON, self.on_bind_toggle)
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send_reply)

        # Setup mixins
        self.setup_recent_messages(CONFIG_RECENT_SENT_MSGS_ROUTER_KEY, self.send_txt, self.recent_list)
        self.setup_splitter_init(self.h_splitter, self.v_splitter)
        Router().set_callback(self.on_request_received)

    def on_bind_toggle(self, event):
        if self.is_bound:
            success, message = Router().unbind()
            if success:
                self.is_bound = False
                self.bind_toggle_btn.SetLabel("Bind")
                self.send_btn.Enable(False)
                self.port_txt.Enable(True)
            else:
                wx.MessageBox(message, "Unbind Error", wx.OK | wx.ICON_ERROR)
        else:
            port = self.port_txt.GetValue().strip()
            if not port:
                wx.MessageBox("Please enter a port number", "Input Error", wx.OK | wx.ICON_WARNING)
                return
            if not port.isdigit():
                wx.MessageBox("Port must be a number", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            Config.set(CONFIG_ROUTER_PORT_KEY, port)
            success, message = Router().bind(port)
            if success:
                self.is_bound = True
                self.bind_toggle_btn.SetLabel("Unbind")
                self.send_btn.Enable(True)
                self.port_txt.Enable(False)
            else:
                wx.MessageBox(message, "Bind Error", wx.OK | wx.ICON_ERROR)

    def on_request_received(self, message):
        try:
            if isinstance(message, str):
                parsed = json.loads(message)
                self.recv_txt.SetValue(json.dumps(parsed, indent=2))
            elif isinstance(message, dict):
                self.recv_txt.SetValue(json.dumps(message, indent=2))
            else:
                self.recv_txt.SetValue(str(message))
        except json.JSONDecodeError:
            self.recv_txt.SetValue(str(message))

    def on_send_reply(self, event):
        message = self.send_txt.GetValue()

        try:
            parsed = json.loads(message)
            formatted = json.dumps(parsed, indent=2)
            self.send_txt.SetValue(formatted)
            message = formatted
        except json.JSONDecodeError:
            pass

        success, msg = Router().send_reply(message)
        if not success:
            wx.MessageBox(msg, "Send Error", wx.OK | wx.ICON_ERROR)
            return

        self.add_to_recent(message)


class PairPanel(wx.Panel, RecentMessagesMixin, SplitterInitMixin):
    """UI Panel for PAIR socket - exclusive 1:1 bidirectional connection."""

    def __init__(self, parent):
        super().__init__(parent)
        self.is_active = False

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Top Sizer (Mode, Address/Port, Connect button)
        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.mode_lbl = wx.StaticText(self, label="Mode:")
        self.mode_choice = wx.Choice(self, choices=["Connect", "Bind"])
        self.mode_choice.SetSelection(0 if Config.get(CONFIG_PAIR_MODE_KEY, "connect") == "connect" else 1)

        self.addr_lbl = wx.StaticText(self, label="Address/Port:")
        default_addr = Config.get(CONFIG_PAIR_ADDRESS_KEY, "tcp://localhost:5559")
        self.addr_txt = wx.TextCtrl(self, value=default_addr, size=(200, -1))

        self.connect_toggle_btn = wx.Button(self, label="Start")

        self.top_sizer.Add(self.mode_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.mode_choice, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.addr_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.addr_txt, 0, wx.EXPAND | wx.ALL, 5)
        self.top_sizer.Add(self.connect_toggle_btn, 0, wx.CENTER | wx.ALL, 5)

        # Create horizontal splitter for Send/Recv
        self.h_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Send Side Panel
        self.send_panel = wx.Panel(self.h_splitter)
        self.send_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_lbl = wx.StaticText(self.send_panel, label="Send:")

        self.v_splitter = wx.SplitterWindow(self.send_panel, style=wx.SP_LIVE_UPDATE)

        self.msg_panel = wx.Panel(self.v_splitter)
        self.msg_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_txt = wx.TextCtrl(self.msg_panel, value="Enter your message here", style=wx.TE_MULTILINE)
        self.msg_panel_sizer.Add(self.send_txt, 1, wx.EXPAND)
        self.msg_panel.SetSizer(self.msg_panel_sizer)

        self.recent_panel = wx.Panel(self.v_splitter)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_lbl = wx.StaticText(self.recent_panel, label="Recent Messages:")
        self.recent_list = wx.ListBox(self.recent_panel)
        self.recent_sizer.Add(self.recent_lbl, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.v_splitter.SplitHorizontally(self.msg_panel, self.recent_panel)
        self.v_splitter.SetSashGravity(0.5)
        self.v_splitter.SetMinimumPaneSize(80)

        self.send_sizer.Add(self.send_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.send_sizer.Add(self.v_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.send_panel.SetSizer(self.send_sizer)

        # Recv Side Panel
        self.recv_panel = wx.Panel(self.h_splitter)
        self.recv_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recv_lbl = wx.StaticText(self.recv_panel, label="Received:")
        self.recv_txt = wx.TextCtrl(
            self.recv_panel,
            value="\n\n\n\t\tReceived message will be displayed here",
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self.recv_sizer.Add(self.recv_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.recv_sizer.Add(self.recv_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.recv_panel.SetSizer(self.recv_sizer)

        self.h_splitter.SplitVertically(self.send_panel, self.recv_panel)
        self.h_splitter.SetSashGravity(0.5)
        self.h_splitter.SetMinimumPaneSize(200)

        # Control Sizer
        self.ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.send_btn = wx.Button(self, label="Send Message")
        self.send_btn.Enable(False)
        self.ctrl_sizer.AddStretchSpacer(1)
        self.ctrl_sizer.Add(self.send_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.main_sizer.Add(self.top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.h_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.ctrl_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.connect_toggle_btn.Bind(wx.EVT_BUTTON, self.on_connect_toggle)
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send_message)

        # Setup mixins
        self.setup_recent_messages(CONFIG_RECENT_SENT_MSGS_PAIR_KEY, self.send_txt, self.recent_list)
        self.setup_splitter_init(self.h_splitter, self.v_splitter)
        PairSocket().set_callback(self.recv_message)

    def on_connect_toggle(self, event):
        if self.is_active:
            PairSocket().stop()
            self.is_active = False
            self.connect_toggle_btn.SetLabel("Start")
            self.send_btn.Enable(False)
            self.addr_txt.Enable(True)
            self.mode_choice.Enable(True)
        else:
            addr = self.addr_txt.GetValue().strip()
            if not addr:
                wx.MessageBox("Please enter an address or port", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            mode = "connect" if self.mode_choice.GetSelection() == 0 else "bind"
            Config.set(CONFIG_PAIR_MODE_KEY, mode)
            Config.set(CONFIG_PAIR_ADDRESS_KEY, addr)

            if mode == "connect":
                success, message = PairSocket().connect(addr)
            else:
                # Extract port from address if full address given, or use as-is
                port = addr.replace("tcp://*:", "").replace("tcp://localhost:", "")
                if not port.isdigit():
                    wx.MessageBox("For bind mode, please enter a port number or tcp://*:port", "Input Error", wx.OK | wx.ICON_WARNING)
                    return
                success, message = PairSocket().bind(port)

            if success:
                self.is_active = True
                self.connect_toggle_btn.SetLabel("Stop")
                self.send_btn.Enable(True)
                self.addr_txt.Enable(False)
                self.mode_choice.Enable(False)
            else:
                wx.MessageBox(message, "Connection Error", wx.OK | wx.ICON_ERROR)

    def on_send_message(self, event):
        message = self.send_txt.GetValue()

        try:
            parsed = json.loads(message)
            formatted = json.dumps(parsed, indent=2)
            self.send_txt.SetValue(formatted)
            message = formatted
        except json.JSONDecodeError:
            pass

        success, msg = PairSocket().send(message)
        if not success:
            wx.MessageBox(msg, "Send Error", wx.OK | wx.ICON_ERROR)
            return

        self.add_to_recent(message)

    def recv_message(self, message):
        try:
            if isinstance(message, str):
                parsed = json.loads(message)
                self.recv_txt.SetValue(json.dumps(parsed, indent=2))
            elif isinstance(message, dict):
                self.recv_txt.SetValue(json.dumps(message, indent=2))
            else:
                self.recv_txt.SetValue(str(message))
        except json.JSONDecodeError:
            self.recv_txt.SetValue(str(message))


class XPublisherPanel(wx.Panel, RecentMessagesMixin, SplitterInitMixin):
    """UI Panel for XPUB socket - publishes and shows subscription events."""

    def __init__(self, parent):
        super().__init__(parent)

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.is_bound = False

        # Controls
        self.controls_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.port_lbl = wx.StaticText(self, label="Port:")
        self.port_txt = wx.TextCtrl(self, value=Config.get(CONFIG_XPUB_PORT_KEY, "5560"), size=(80, -1))

        self.bind_toggle_btn = wx.Button(self, label="Bind")

        self.topic_lbl = wx.StaticText(self, label="Topic:")
        self.topic_txt = wx.TextCtrl(self, value="test", size=(100, -1))

        self.controls_sizer.Add(self.port_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.port_txt, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.bind_toggle_btn, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.topic_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.topic_txt, 0, wx.CENTER | wx.ALL, 5)

        # Create horizontal splitter for message and subscriptions
        self.h_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Left side - Message input
        self.left_panel = wx.Panel(self.h_splitter)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)

        self.v_splitter = wx.SplitterWindow(self.left_panel, style=wx.SP_LIVE_UPDATE)

        self.msg_panel = wx.Panel(self.v_splitter)
        self.msg_sizer = wx.BoxSizer(wx.VERTICAL)
        self.msg_lbl = wx.StaticText(self.msg_panel, label="Message:")
        self.msg_txt = wx.TextCtrl(self.msg_panel, value="Enter your message here", style=wx.TE_MULTILINE)
        self.msg_sizer.Add(self.msg_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.msg_sizer.Add(self.msg_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.msg_panel.SetSizer(self.msg_sizer)

        self.recent_panel = wx.Panel(self.v_splitter)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_lbl = wx.StaticText(self.recent_panel, label="Recent Messages:")
        self.recent_list = wx.ListBox(self.recent_panel)
        self.recent_sizer.Add(self.recent_lbl, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.v_splitter.SplitHorizontally(self.msg_panel, self.recent_panel)
        self.v_splitter.SetSashGravity(0.5)
        self.v_splitter.SetMinimumPaneSize(80)

        self.left_sizer.Add(self.v_splitter, 1, wx.EXPAND)
        self.left_panel.SetSizer(self.left_sizer)

        # Right side - Subscription events
        self.right_panel = wx.Panel(self.h_splitter)
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)
        self.subs_lbl = wx.StaticText(self.right_panel, label="Subscription Events:")
        self.subs_list = wx.dataview.DataViewListCtrl(self.right_panel)
        self.subs_list.AppendTextColumn("Time", width=80)
        self.subs_list.AppendTextColumn("Action", width=100)
        self.subs_list.AppendTextColumn("Topic", width=150)
        self.right_sizer.Add(self.subs_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.right_sizer.Add(self.subs_list, 1, wx.EXPAND | wx.ALL, 5)
        self.right_panel.SetSizer(self.right_sizer)

        self.h_splitter.SplitVertically(self.left_panel, self.right_panel)
        self.h_splitter.SetSashGravity(0.5)
        self.h_splitter.SetMinimumPaneSize(200)

        # Publish Button
        self.pub_btn = wx.Button(self, label="Publish Message")
        self.pub_btn.Enable(False)

        self.main_sizer.Add(self.controls_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.h_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.pub_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.bind_toggle_btn.Bind(wx.EVT_BUTTON, self.on_bind_toggle)
        self.pub_btn.Bind(wx.EVT_BUTTON, self.on_publish)

        # Setup mixins
        self.setup_recent_messages(CONFIG_RECENT_SENT_MSGS_XPUB_KEY, self.msg_txt, self.recent_list)
        self.setup_splitter_init(self.h_splitter, self.v_splitter)
        XPublisher().set_subscription_callback(self.on_subscription_event)

    def on_bind_toggle(self, event):
        if self.is_bound:
            success, message = XPublisher().unbind()
            if success:
                self.is_bound = False
                self.bind_toggle_btn.SetLabel("Bind")
                self.pub_btn.Enable(False)
                self.port_txt.Enable(True)
            else:
                wx.MessageBox(message, "Unbind Error", wx.OK | wx.ICON_ERROR)
        else:
            port = self.port_txt.GetValue().strip()
            if not port or not port.isdigit():
                wx.MessageBox("Please enter a valid port number", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            success, message = XPublisher().bind(port)
            if success:
                Config.set(CONFIG_XPUB_PORT_KEY, port)
                self.is_bound = True
                self.bind_toggle_btn.SetLabel("Unbind")
                self.pub_btn.Enable(True)
                self.port_txt.Enable(False)
            else:
                wx.MessageBox(message, "Bind Error", wx.OK | wx.ICON_ERROR)

    def on_subscription_event(self, action, topic):
        """Handle subscription/unsubscription events from clients."""
        timestamp = time.strftime("%H:%M:%S")
        self.subs_list.AppendItem([timestamp, action, topic or "(all)"])

    def on_publish(self, event):
        topic = self.topic_txt.GetValue().strip()
        message = self.msg_txt.GetValue()

        if not topic:
            wx.MessageBox("Please enter a topic", "Input Error", wx.OK | wx.ICON_WARNING)
            return

        try:
            parsed = json.loads(message)
            formatted = json.dumps(parsed, indent=2)
            self.msg_txt.SetValue(formatted)
            message = formatted
        except json.JSONDecodeError:
            pass

        success, msg = XPublisher().send_message(topic, message)
        if not success:
            wx.MessageBox(msg, "Publish Error", wx.OK | wx.ICON_ERROR)
            return

        self.add_to_recent(message)


class XSubscriberPanel(wx.Panel):
    """UI Panel for XSUB socket - subscribes with explicit subscription control."""

    def __init__(self, parent):
        super().__init__(parent)
        self.is_running = False
        self.topic_frames = {}  # {topic: TopicFrame}
        self.topic_stats = {}  # {topic: {"count": int, "bytes": int, "first_time": float, "last_time": float}}
        self.start_time = None

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Controls
        self.controls_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.addr_lbl = wx.StaticText(self, label="Address:")
        self.addr_txt = wx.TextCtrl(
            self,
            value=Config.get(CONFIG_XSUB_ADDRESS_KEY, "tcp://localhost:5560"),
            size=(200, -1),
        )
        self.topic_lbl = wx.StaticText(self, label="Topics (comma sep):")
        self.topic_txt = wx.TextCtrl(self, value="", size=(150, -1))

        self.toggle_btn = wx.Button(self, label="Start")

        self.controls_sizer.Add(self.addr_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.addr_txt, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.topic_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.topic_txt, 1, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.toggle_btn, 0, wx.CENTER | wx.ALL, 5)

        # Create splitter for messages and stats
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Message List Panel
        self.msg_panel = wx.Panel(self.splitter)
        self.msg_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.msg_list = wx.dataview.DataViewListCtrl(self.msg_panel)
        self.msg_list.AppendTextColumn("Topic", width=100)
        self.msg_list.AppendTextColumn("Message", width=400)
        self.msg_panel_sizer.Add(self.msg_list, 1, wx.EXPAND)
        self.msg_panel.SetSizer(self.msg_panel_sizer)

        # Statistics Panel
        self.stats_panel = wx.Panel(self.splitter)
        self.stats_sizer = wx.BoxSizer(wx.VERTICAL)

        # Stats header with reset button
        stats_header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        stats_header = wx.StaticText(self.stats_panel, label="Statistics")
        stats_header.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        stats_header_sizer.Add(stats_header, 0, wx.CENTER | wx.ALL, 5)
        stats_header_sizer.AddStretchSpacer(1)
        self.reset_stats_btn = wx.Button(self.stats_panel, label="Reset Stats")
        stats_header_sizer.Add(self.reset_stats_btn, 0, wx.ALL, 2)
        self.stats_sizer.Add(stats_header_sizer, 0, wx.EXPAND | wx.ALL, 2)

        # Totals section title
        totals_title = wx.StaticText(self.stats_panel, label="Totals")
        totals_title.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.stats_sizer.Add(totals_title, 0, wx.LEFT | wx.TOP, 5)

        # Summary stats grid
        summary_grid = wx.FlexGridSizer(2, 5, 5, 20)  # 2 rows, 5 cols, vgap=5, hgap=20
        for i in range(5):
            summary_grid.AddGrowableCol(i, 1)

        # Row 1: Labels
        for label in ["Messages", "Data Size", "Topics", "Rate", "Speed"]:
            lbl = wx.StaticText(self.stats_panel, label=label)
            lbl.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            summary_grid.Add(lbl, 0, wx.ALIGN_CENTER)

        # Row 2: Values
        self.summary_msgs = wx.StaticText(self.stats_panel, label="0")
        self.summary_bytes = wx.StaticText(self.stats_panel, label="0 bytes")
        self.summary_topics = wx.StaticText(self.stats_panel, label="0")
        self.summary_rate = wx.StaticText(self.stats_panel, label="-")
        self.summary_speed = wx.StaticText(self.stats_panel, label="-")

        summary_grid.Add(self.summary_msgs, 0, wx.ALIGN_CENTER)
        summary_grid.Add(self.summary_bytes, 0, wx.ALIGN_CENTER)
        summary_grid.Add(self.summary_topics, 0, wx.ALIGN_CENTER)
        summary_grid.Add(self.summary_rate, 0, wx.ALIGN_CENTER)
        summary_grid.Add(self.summary_speed, 0, wx.ALIGN_CENTER)

        self.stats_sizer.Add(summary_grid, 0, wx.EXPAND | wx.ALL, 5)

        # Per-Topic section title
        per_topic_title = wx.StaticText(self.stats_panel, label="Per Topic")
        per_topic_title.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.stats_sizer.Add(per_topic_title, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 5)

        # Stats list
        self.stats_list = wx.dataview.DataViewListCtrl(self.stats_panel)
        self.stats_list.AppendTextColumn("Topic", width=150)
        self.stats_list.AppendTextColumn("Count", width=100)
        self.stats_list.AppendTextColumn("Bytes", width=120)
        self.stats_list.AppendTextColumn("Rate (msg/s)", width=120)
        self.stats_list.AppendTextColumn("Last Received", width=150)
        self.stats_sizer.Add(self.stats_list, 1, wx.EXPAND)

        self.stats_panel.SetSizer(self.stats_sizer)

        self.splitter.SplitHorizontally(self.msg_panel, self.stats_panel)
        self.splitter.SetSashGravity(0.5)
        self.splitter.SetMinimumPaneSize(100)

        self.main_sizer.Add(self.controls_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.splitter, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.toggle_btn.Bind(wx.EVT_BUTTON, self.on_toggle)
        self.reset_stats_btn.Bind(wx.EVT_BUTTON, self.on_reset_stats)
        self.msg_list.Bind(wx.dataview.EVT_DATAVIEW_ITEM_ACTIVATED, self.on_item_activated)
        self.msg_list.Bind(wx.dataview.EVT_DATAVIEW_ITEM_CONTEXT_MENU, self.on_msg_list_right_click)
        self.Bind(wx.EVT_SIZE, self.on_size)

        self._splitter_initialized = False
        XSubscriber().set_callback(self.on_message_received)

    def on_size(self, event):
        event.Skip()
        if not self._splitter_initialized and self.GetSize().GetWidth() > 0:
            wx.CallAfter(self._init_splitter_position)
            self._splitter_initialized = True

    def _init_splitter_position(self):
        size = self.splitter.GetSize().GetHeight()
        if size > 0:
            self.splitter.SetSashPosition(size // 2)
        self.stats_panel.Layout()

    def on_reset_stats(self, event):
        """Reset all statistics."""
        self.topic_stats = {}
        self.start_time = time.time() if self.is_running else None
        self.stats_list.DeleteAllItems()
        self.update_summary_stats()

    def on_toggle(self, event):
        if self.is_running:
            XSubscriber().stop()
            self.is_running = False
            self.toggle_btn.SetLabel("Start")
            self.addr_txt.Enable(True)
            self.topic_txt.Enable(True)
        else:
            addr = self.addr_txt.GetValue().strip()
            topics_str = self.topic_txt.GetValue().strip()

            if not addr:
                wx.MessageBox("Please enter an address", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            if topics_str:
                topics = [t.strip() for t in topics_str.split(",") if t.strip()]
            else:
                topics = [""]

            Config.set(CONFIG_XSUB_ADDRESS_KEY, addr)
            success, message = XSubscriber().start(topics, addr)
            if success:
                self.is_running = True
                self.start_time = time.time()
                self.topic_stats = {}
                self.toggle_btn.SetLabel("Stop")
                self.addr_txt.Enable(False)
                self.topic_txt.Enable(False)
                wx.CallAfter(self.stats_panel.Layout)
            else:
                wx.MessageBox(message, "Connection Error", wx.OK | wx.ICON_ERROR)

    def update_summary_stats(self):
        """Update the summary statistics labels."""
        total_msgs = sum(s["count"] for s in self.topic_stats.values())
        total_bytes = sum(s["bytes"] for s in self.topic_stats.values())
        total_topics = len(self.topic_stats)

        # Calculate overall rate and speed
        rate_str = "-"
        speed_str = "-"
        if self.start_time and self.topic_stats:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                rate_str = f"{total_msgs / elapsed:.2f} msg/s"
                speed_str = format_speed(total_bytes / elapsed)

        self.summary_msgs.SetLabel(str(total_msgs))
        self.summary_bytes.SetLabel(format_bytes(total_bytes))
        self.summary_topics.SetLabel(str(total_topics))
        self.summary_rate.SetLabel(rate_str)
        self.summary_speed.SetLabel(speed_str)

    def update_topic_stats_display(self, topic):
        """Update the statistics list for a specific topic."""
        stats = self.topic_stats.get(topic)
        if not stats:
            return

        # Calculate rate
        elapsed = stats["last_time"] - stats["first_time"]
        rate_str = f"{stats['count'] / elapsed:.2f}" if elapsed > 0 else "-"
        bytes_str = format_bytes(stats["bytes"]).replace(" bytes", " B")
        last_time = time.strftime("%H:%M:%S", time.localtime(stats["last_time"]))

        # Find or add row
        found = False
        for i in range(self.stats_list.GetItemCount()):
            if self.stats_list.GetTextValue(i, 0) == topic:
                self.stats_list.SetTextValue(str(stats["count"]), i, 1)
                self.stats_list.SetTextValue(bytes_str, i, 2)
                self.stats_list.SetTextValue(rate_str, i, 3)
                self.stats_list.SetTextValue(last_time, i, 4)
                found = True
                break

        if not found:
            self.stats_list.AppendItem([topic, str(stats["count"]), bytes_str, rate_str, last_time])

    def on_message_received(self, topic, message):
        current_time = time.time()
        msg_str = json.dumps(message) if isinstance(message, dict) else str(message)
        msg_bytes = len(msg_str.encode("utf-8"))

        if topic not in self.topic_stats:
            self.topic_stats[topic] = {"count": 0, "bytes": 0, "first_time": current_time, "last_time": current_time}

        self.topic_stats[topic]["count"] += 1
        self.topic_stats[topic]["bytes"] += msg_bytes
        self.topic_stats[topic]["last_time"] = current_time

        # Update message list
        found = False
        for i in range(self.msg_list.GetItemCount()):
            if self.msg_list.GetTextValue(i, 0) == topic:
                self.msg_list.SetTextValue(msg_str, i, 1)
                found = True
                break
        if not found:
            self.msg_list.AppendItem([topic, msg_str])

        # Update topic frame if exists
        if topic in self.topic_frames:
            if self.topic_frames[topic]:
                self.topic_frames[topic].update_message(message)
            else:
                del self.topic_frames[topic]

        # Update stats display
        self.update_topic_stats_display(topic)
        self.update_summary_stats()

    def on_item_activated(self, event):
        selection = self.msg_list.GetSelectedRow()
        if selection != wx.NOT_FOUND:
            topic = self.msg_list.GetTextValue(selection, 0)
            msg_str = self.msg_list.GetTextValue(selection, 1)

            if topic not in self.topic_frames or not self.topic_frames[topic]:
                self.topic_frames[topic] = TopicFrame(self, topic)

            self.topic_frames[topic].update_message(msg_str)
            self.topic_frames[topic].Raise()

    def on_msg_list_right_click(self, event):
        menu = wx.Menu()
        clear_item = menu.Append(wx.ID_ANY, "Clear Messages")
        self.Bind(wx.EVT_MENU, self.on_clear_messages, clear_item)
        self.PopupMenu(menu)
        menu.Destroy()

    def on_clear_messages(self, event):
        self.msg_list.DeleteAllItems()


class StreamPanel(wx.Panel, RecentMessagesMixin, SplitterInitMixin):
    """UI Panel for STREAM socket - raw TCP connection."""

    def __init__(self, parent):
        super().__init__(parent)
        self.is_active = False

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Top Sizer (Mode, Address/Port, Connect button)
        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.mode_lbl = wx.StaticText(self, label="Mode:")
        self.mode_choice = wx.Choice(self, choices=["Connect", "Bind"])
        self.mode_choice.SetSelection(0 if Config.get(CONFIG_STREAM_MODE_KEY, "connect") == "connect" else 1)

        self.addr_lbl = wx.StaticText(self, label="Address/Port:")
        default_addr = Config.get(CONFIG_STREAM_ADDRESS_KEY, "tcp://localhost:8080")
        self.addr_txt = wx.TextCtrl(self, value=default_addr, size=(200, -1))

        self.connect_toggle_btn = wx.Button(self, label="Start")

        self.top_sizer.Add(self.mode_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.mode_choice, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.addr_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.addr_txt, 0, wx.EXPAND | wx.ALL, 5)
        self.top_sizer.Add(self.connect_toggle_btn, 0, wx.CENTER | wx.ALL, 5)

        # Create horizontal splitter for Send/Recv
        self.h_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Send Side Panel
        self.send_panel = wx.Panel(self.h_splitter)
        self.send_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_lbl = wx.StaticText(self.send_panel, label="Send (raw data):")

        self.v_splitter = wx.SplitterWindow(self.send_panel, style=wx.SP_LIVE_UPDATE)

        self.msg_panel = wx.Panel(self.v_splitter)
        self.msg_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_txt = wx.TextCtrl(self.msg_panel, value="GET / HTTP/1.1\r\nHost: localhost\r\n\r\n", style=wx.TE_MULTILINE)
        self.msg_panel_sizer.Add(self.send_txt, 1, wx.EXPAND)
        self.msg_panel.SetSizer(self.msg_panel_sizer)

        self.recent_panel = wx.Panel(self.v_splitter)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_lbl = wx.StaticText(self.recent_panel, label="Recent:")
        self.recent_list = wx.ListBox(self.recent_panel)
        self.recent_sizer.Add(self.recent_lbl, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.v_splitter.SplitHorizontally(self.msg_panel, self.recent_panel)
        self.v_splitter.SetSashGravity(0.5)
        self.v_splitter.SetMinimumPaneSize(80)

        self.send_sizer.Add(self.send_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.send_sizer.Add(self.v_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.send_panel.SetSizer(self.send_sizer)

        # Recv Side Panel
        self.recv_panel = wx.Panel(self.h_splitter)
        self.recv_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recv_lbl = wx.StaticText(self.recv_panel, label="Received (raw data):")
        self.recv_txt = wx.TextCtrl(
            self.recv_panel,
            value="\n\n\n\t\tReceived data will be displayed here",
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self.recv_sizer.Add(self.recv_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.recv_sizer.Add(self.recv_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.recv_panel.SetSizer(self.recv_sizer)

        self.h_splitter.SplitVertically(self.send_panel, self.recv_panel)
        self.h_splitter.SetSashGravity(0.5)
        self.h_splitter.SetMinimumPaneSize(200)

        # Control Sizer
        self.ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.peer_lbl = wx.StaticText(self, label="Peer: None")
        self.send_btn = wx.Button(self, label="Send Data")
        self.send_btn.Enable(False)
        self.ctrl_sizer.Add(self.peer_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.ctrl_sizer.AddStretchSpacer(1)
        self.ctrl_sizer.Add(self.send_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.main_sizer.Add(self.top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.h_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.ctrl_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.connect_toggle_btn.Bind(wx.EVT_BUTTON, self.on_connect_toggle)
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send_message)

        # Setup mixins
        self.setup_recent_messages(CONFIG_RECENT_SENT_MSGS_STREAM_KEY, self.send_txt, self.recent_list)
        self.setup_splitter_init(self.h_splitter, self.v_splitter)
        StreamSocket().set_callback(self.recv_message)

    def on_connect_toggle(self, event):
        if self.is_active:
            StreamSocket().stop()
            self.is_active = False
            self.connect_toggle_btn.SetLabel("Start")
            self.send_btn.Enable(False)
            self.addr_txt.Enable(True)
            self.mode_choice.Enable(True)
            self.peer_lbl.SetLabel("Peer: None")
        else:
            addr = self.addr_txt.GetValue().strip()
            if not addr:
                wx.MessageBox("Please enter an address or port", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            mode = "connect" if self.mode_choice.GetSelection() == 0 else "bind"
            Config.set(CONFIG_STREAM_MODE_KEY, mode)
            Config.set(CONFIG_STREAM_ADDRESS_KEY, addr)

            if mode == "connect":
                success, message = StreamSocket().connect(addr)
            else:
                port = addr.replace("tcp://*:", "").replace("tcp://localhost:", "")
                if not port.isdigit():
                    wx.MessageBox("For bind mode, enter a port number", "Input Error", wx.OK | wx.ICON_WARNING)
                    return
                success, message = StreamSocket().bind(port)

            if success:
                self.is_active = True
                self.connect_toggle_btn.SetLabel("Stop")
                self.send_btn.Enable(True)
                self.addr_txt.Enable(False)
                self.mode_choice.Enable(False)
            else:
                wx.MessageBox(message, "Connection Error", wx.OK | wx.ICON_ERROR)

    def on_send_message(self, event):
        message = self.send_txt.GetValue()

        success, msg = StreamSocket().send(message)
        if not success:
            wx.MessageBox(msg, "Send Error", wx.OK | wx.ICON_ERROR)
            return

        self.add_to_recent(message)

    def recv_message(self, peer_id, message):
        self.peer_lbl.SetLabel(f"Peer: {peer_id}")
        # Append to received text
        current = self.recv_txt.GetValue()
        if current.startswith("\n\n\n\t\t"):
            current = ""
        self.recv_txt.SetValue(current + message)


class ClientPanel(wx.Panel, RecentMessagesMixin, SplitterInitMixin):
    """UI Panel for CLIENT socket - async request (draft API)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.is_connected = False

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Top Sizer (Address, Connect button)
        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.addr_lbl = wx.StaticText(self, label="Server Address:")
        default_addr = Config.get(CONFIG_CLIENT_ADDRESS_KEY, "tcp://localhost:5555")
        self.addr_txt = wx.TextCtrl(self, value=default_addr, size=(200, -1))

        self.connect_btn = wx.Button(self, label="Connect")

        self.top_sizer.Add(self.addr_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.addr_txt, 0, wx.EXPAND | wx.ALL, 5)
        self.top_sizer.Add(self.connect_btn, 0, wx.CENTER | wx.ALL, 5)

        # Create horizontal splitter for Send/Recv
        self.h_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Send Side Panel
        self.send_panel = wx.Panel(self.h_splitter)
        self.send_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_lbl = wx.StaticText(self.send_panel, label="Message to Send:")

        self.v_splitter = wx.SplitterWindow(self.send_panel, style=wx.SP_LIVE_UPDATE)

        self.msg_panel = wx.Panel(self.v_splitter)
        self.msg_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_txt = wx.TextCtrl(self.msg_panel, style=wx.TE_MULTILINE)
        self.msg_panel_sizer.Add(self.send_txt, 1, wx.EXPAND)
        self.msg_panel.SetSizer(self.msg_panel_sizer)

        self.recent_panel = wx.Panel(self.v_splitter)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_lbl = wx.StaticText(self.recent_panel, label="Recent:")
        self.recent_list = wx.ListBox(self.recent_panel)
        self.recent_sizer.Add(self.recent_lbl, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.v_splitter.SplitHorizontally(self.msg_panel, self.recent_panel)
        self.v_splitter.SetSashGravity(0.5)
        self.v_splitter.SetMinimumPaneSize(80)

        self.send_sizer.Add(self.send_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.send_sizer.Add(self.v_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.send_panel.SetSizer(self.send_sizer)

        # Recv Side Panel
        self.recv_panel = wx.Panel(self.h_splitter)
        self.recv_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recv_lbl = wx.StaticText(self.recv_panel, label="Received:")
        self.recv_txt = wx.TextCtrl(
            self.recv_panel,
            value="\n\n\n\t\tServer response will be displayed here",
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self.recv_sizer.Add(self.recv_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.recv_sizer.Add(self.recv_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.recv_panel.SetSizer(self.recv_sizer)

        self.h_splitter.SplitVertically(self.send_panel, self.recv_panel)
        self.h_splitter.SetSashGravity(0.5)
        self.h_splitter.SetMinimumPaneSize(200)

        # Control Sizer
        self.ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.send_btn = wx.Button(self, label="Send Message")
        self.send_btn.Enable(False)
        self.ctrl_sizer.AddStretchSpacer(1)
        self.ctrl_sizer.Add(self.send_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.main_sizer.Add(self.top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.h_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.ctrl_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.connect_btn.Bind(wx.EVT_BUTTON, self.on_connect_toggle)
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send_message)

        # Setup mixins
        self.setup_recent_messages(CONFIG_RECENT_SENT_MSGS_CLIENT_KEY, self.send_txt, self.recent_list)
        self.setup_splitter_init(self.h_splitter, self.v_splitter)
        Client().set_callback(self.recv_message)

    def on_connect_toggle(self, event):
        if self.is_connected:
            Client().disconnect()
            self.is_connected = False
            self.connect_btn.SetLabel("Connect")
            self.send_btn.Enable(False)
            self.addr_txt.Enable(True)
        else:
            addr = self.addr_txt.GetValue().strip()
            if not addr:
                wx.MessageBox("Please enter a server address", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            Config.set(CONFIG_CLIENT_ADDRESS_KEY, addr)
            success, message = Client().connect(addr)

            if success:
                self.is_connected = True
                self.connect_btn.SetLabel("Disconnect")
                self.send_btn.Enable(True)
                self.addr_txt.Enable(False)
            else:
                wx.MessageBox(message, "Connection Error", wx.OK | wx.ICON_ERROR)

    def on_send_message(self, event):
        message = self.send_txt.GetValue()
        if not message:
            wx.MessageBox("Please enter a message", "Input Error", wx.OK | wx.ICON_WARNING)
            return

        success, msg = Client().send(message)
        if not success:
            wx.MessageBox(msg, "Send Error", wx.OK | wx.ICON_ERROR)
            return

        self.add_to_recent(message)

    def recv_message(self, message):
        formatted = format_json_message(message)
        self.recv_txt.SetValue(formatted)


class ServerPanel(wx.Panel, RecentMessagesMixin, SplitterInitMixin):
    """UI Panel for SERVER socket - async reply (draft API)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.is_bound = False

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Top Sizer (Port, Bind button)
        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.port_lbl = wx.StaticText(self, label="Port:")
        default_port = Config.get(CONFIG_SERVER_PORT_KEY, "5555")
        self.port_txt = wx.TextCtrl(self, value=str(default_port), size=(100, -1))

        self.bind_btn = wx.Button(self, label="Bind")

        self.top_sizer.Add(self.port_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.port_txt, 0, wx.EXPAND | wx.ALL, 5)
        self.top_sizer.Add(self.bind_btn, 0, wx.CENTER | wx.ALL, 5)

        # Create horizontal splitter for Recv/Reply
        self.h_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Recv Side Panel
        self.recv_panel = wx.Panel(self.h_splitter)
        self.recv_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recv_lbl = wx.StaticText(self.recv_panel, label="Received Request:")
        self.recv_txt = wx.TextCtrl(
            self.recv_panel,
            value="\n\n\n\t\tClient requests will appear here",
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self.recv_sizer.Add(self.recv_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.recv_sizer.Add(self.recv_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.recv_panel.SetSizer(self.recv_sizer)

        # Reply Side Panel
        self.reply_panel = wx.Panel(self.h_splitter)
        self.reply_sizer = wx.BoxSizer(wx.VERTICAL)
        self.reply_lbl = wx.StaticText(self.reply_panel, label="Reply Message:")

        self.v_splitter = wx.SplitterWindow(self.reply_panel, style=wx.SP_LIVE_UPDATE)

        self.msg_panel = wx.Panel(self.v_splitter)
        self.msg_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.reply_txt = wx.TextCtrl(self.msg_panel, style=wx.TE_MULTILINE)
        self.msg_panel_sizer.Add(self.reply_txt, 1, wx.EXPAND)
        self.msg_panel.SetSizer(self.msg_panel_sizer)

        self.recent_panel = wx.Panel(self.v_splitter)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_lbl = wx.StaticText(self.recent_panel, label="Recent:")
        self.recent_list = wx.ListBox(self.recent_panel)
        self.recent_sizer.Add(self.recent_lbl, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.v_splitter.SplitHorizontally(self.msg_panel, self.recent_panel)
        self.v_splitter.SetSashGravity(0.5)
        self.v_splitter.SetMinimumPaneSize(80)

        self.reply_sizer.Add(self.reply_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.reply_sizer.Add(self.v_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.reply_panel.SetSizer(self.reply_sizer)

        self.h_splitter.SplitVertically(self.recv_panel, self.reply_panel)
        self.h_splitter.SetSashGravity(0.5)
        self.h_splitter.SetMinimumPaneSize(200)

        # Control Sizer
        self.ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.send_btn = wx.Button(self, label="Send Reply")
        self.send_btn.Enable(False)
        self.ctrl_sizer.AddStretchSpacer(1)
        self.ctrl_sizer.Add(self.send_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.main_sizer.Add(self.top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.h_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.ctrl_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.bind_btn.Bind(wx.EVT_BUTTON, self.on_bind_toggle)
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send_reply)

        # Setup mixins
        self.setup_recent_messages(CONFIG_RECENT_SENT_MSGS_SERVER_KEY, self.reply_txt, self.recent_list)
        self.setup_splitter_init(self.h_splitter, self.v_splitter)
        Server().set_callback(self.recv_message)

    def on_bind_toggle(self, event):
        if self.is_bound:
            Server().unbind()
            self.is_bound = False
            self.bind_btn.SetLabel("Bind")
            self.send_btn.Enable(False)
            self.port_txt.Enable(True)
        else:
            port = self.port_txt.GetValue().strip()
            if not port.isdigit():
                wx.MessageBox("Please enter a valid port number", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            Config.set(CONFIG_SERVER_PORT_KEY, port)
            success, message = Server().bind(port)

            if success:
                self.is_bound = True
                self.bind_btn.SetLabel("Unbind")
                self.send_btn.Enable(True)
                self.port_txt.Enable(False)
            else:
                wx.MessageBox(message, "Bind Error", wx.OK | wx.ICON_ERROR)

    def on_send_reply(self, event):
        message = self.reply_txt.GetValue()
        if not message:
            wx.MessageBox("Please enter a reply message", "Input Error", wx.OK | wx.ICON_WARNING)
            return

        success, msg = Server().send_reply(message)
        if not success:
            wx.MessageBox(msg, "Send Error", wx.OK | wx.ICON_ERROR)
            return

        self.add_to_recent(message)

    def recv_message(self, message):
        formatted = format_json_message(message)
        self.recv_txt.SetValue(formatted)
        self.send_btn.Enable(True)


class RadioPanel(wx.Panel, RecentMessagesMixin, SplitterInitMixin):
    """UI Panel for RADIO socket - group-based broadcast (draft API)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.is_bound = False

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Top Sizer (Port, Bind button)
        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.port_lbl = wx.StaticText(self, label="Port:")
        default_port = Config.get(CONFIG_RADIO_PORT_KEY, "5556")
        self.port_txt = wx.TextCtrl(self, value=str(default_port), size=(100, -1))

        self.bind_btn = wx.Button(self, label="Bind")

        self.top_sizer.Add(self.port_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.port_txt, 0, wx.EXPAND | wx.ALL, 5)
        self.top_sizer.Add(self.bind_btn, 0, wx.CENTER | wx.ALL, 5)

        # Horizontal splitter for message/recent
        self.h_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Message panel
        self.msg_panel = wx.Panel(self.h_splitter)
        self.msg_sizer = wx.BoxSizer(wx.VERTICAL)

        # Group input
        self.group_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.group_lbl = wx.StaticText(self.msg_panel, label="Group:")
        default_group = Config.get(CONFIG_RADIO_GROUP_KEY, "default")
        self.group_txt = wx.TextCtrl(self.msg_panel, value=default_group, size=(100, -1))
        self.group_sizer.Add(self.group_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.group_sizer.Add(self.group_txt, 0, wx.EXPAND | wx.ALL, 5)

        self.send_lbl = wx.StaticText(self.msg_panel, label="Message to Broadcast:")
        self.send_txt = wx.TextCtrl(self.msg_panel, style=wx.TE_MULTILINE)

        self.msg_sizer.Add(self.group_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.msg_sizer.Add(self.send_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.msg_sizer.Add(self.send_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.msg_panel.SetSizer(self.msg_sizer)

        # Recent panel
        self.recent_panel = wx.Panel(self.h_splitter)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_lbl = wx.StaticText(self.recent_panel, label="Recent Messages:")
        self.recent_list = wx.ListBox(self.recent_panel)
        self.recent_sizer.Add(self.recent_lbl, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND | wx.ALL, 5)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.h_splitter.SplitVertically(self.msg_panel, self.recent_panel)
        self.h_splitter.SetSashGravity(0.6)
        self.h_splitter.SetMinimumPaneSize(200)

        # Control Sizer
        self.ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.send_btn = wx.Button(self, label="Broadcast")
        self.send_btn.Enable(False)
        self.ctrl_sizer.AddStretchSpacer(1)
        self.ctrl_sizer.Add(self.send_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.main_sizer.Add(self.top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.h_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.ctrl_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.bind_btn.Bind(wx.EVT_BUTTON, self.on_bind_toggle)
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send_message)

        # Setup mixins with 0.6 ratio for horizontal splitter
        self.setup_recent_messages(CONFIG_RECENT_SENT_MSGS_RADIO_KEY, self.send_txt, self.recent_list)
        self.setup_splitter_init(self.h_splitter, None, h_ratio=0.6)

    def on_bind_toggle(self, event):
        if self.is_bound:
            Radio().unbind()
            self.is_bound = False
            self.bind_btn.SetLabel("Bind")
            self.send_btn.Enable(False)
            self.port_txt.Enable(True)
        else:
            port = self.port_txt.GetValue().strip()
            if not port.isdigit():
                wx.MessageBox("Please enter a valid port number", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            Config.set(CONFIG_RADIO_PORT_KEY, port)
            success, message = Radio().bind(port)

            if success:
                self.is_bound = True
                self.bind_btn.SetLabel("Unbind")
                self.send_btn.Enable(True)
                self.port_txt.Enable(False)
            else:
                wx.MessageBox(message, "Bind Error", wx.OK | wx.ICON_ERROR)

    def on_send_message(self, event):
        group = self.group_txt.GetValue().strip()
        if not group:
            wx.MessageBox("Please enter a group name", "Input Error", wx.OK | wx.ICON_WARNING)
            return

        message = self.send_txt.GetValue()
        if not message:
            wx.MessageBox("Please enter a message", "Input Error", wx.OK | wx.ICON_WARNING)
            return

        Config.set(CONFIG_RADIO_GROUP_KEY, group)
        success, msg = Radio().send_message(group, message)
        if not success:
            wx.MessageBox(msg, "Send Error", wx.OK | wx.ICON_ERROR)
            return

        self.add_to_recent(f"[{group}] {message}")


class DishPanel(wx.Panel):
    """UI Panel for DISH socket - group-based receive (draft API)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.is_running = False

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Top Sizer (Address, Groups, Start button)
        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.addr_lbl = wx.StaticText(self, label="Radio Address:")
        default_addr = Config.get(CONFIG_DISH_ADDRESS_KEY, "tcp://localhost:5556")
        self.addr_txt = wx.TextCtrl(self, value=default_addr, size=(180, -1))

        self.group_lbl = wx.StaticText(self, label="Groups:")
        default_groups = Config.get(CONFIG_DISH_GROUP_KEY, "default")
        self.group_txt = wx.TextCtrl(self, value=default_groups, size=(150, -1))
        self.group_txt.SetToolTip("Comma-separated group names to join")

        self.start_btn = wx.Button(self, label="Start")

        self.top_sizer.Add(self.addr_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.addr_txt, 0, wx.EXPAND | wx.ALL, 5)
        self.top_sizer.Add(self.group_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.group_txt, 0, wx.EXPAND | wx.ALL, 5)
        self.top_sizer.Add(self.start_btn, 0, wx.CENTER | wx.ALL, 5)

        # Received messages
        self.recv_lbl = wx.StaticText(self, label="Received Messages:")
        self.recv_txt = wx.TextCtrl(
            self,
            value="\n\n\n\t\tMessages from Radio will appear here",
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )

        # Stats
        self.stats_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.stats_lbl = wx.StaticText(self, label="Messages: 0")
        self.clear_btn = wx.Button(self, label="Clear")
        self.stats_sizer.Add(self.stats_lbl, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.stats_sizer.Add(self.clear_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.main_sizer.Add(self.top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.recv_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.recv_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.stats_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.start_btn.Bind(wx.EVT_BUTTON, self.on_start_toggle)
        self.clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)

        self.message_count = 0
        Dish().set_callback(self.recv_message)

    def on_start_toggle(self, event):
        if self.is_running:
            Dish().stop()
            self.is_running = False
            self.start_btn.SetLabel("Start")
            self.addr_txt.Enable(True)
            self.group_txt.Enable(True)
        else:
            addr = self.addr_txt.GetValue().strip()
            if not addr:
                wx.MessageBox("Please enter a Radio address", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            groups_str = self.group_txt.GetValue().strip()
            if not groups_str:
                wx.MessageBox("Please enter at least one group name", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            groups = [g.strip() for g in groups_str.split(",") if g.strip()]

            Config.set(CONFIG_DISH_ADDRESS_KEY, addr)
            Config.set(CONFIG_DISH_GROUP_KEY, groups_str)

            success, message = Dish().start(groups, addr)

            if success:
                self.is_running = True
                self.start_btn.SetLabel("Stop")
                self.addr_txt.Enable(False)
                self.group_txt.Enable(False)
                self.recv_txt.SetValue("")
            else:
                wx.MessageBox(message, "Connection Error", wx.OK | wx.ICON_ERROR)

    def on_clear(self, event):
        self.recv_txt.SetValue("")
        self.message_count = 0
        self.stats_lbl.SetLabel("Messages: 0")

    def recv_message(self, group, message):
        self.message_count += 1
        self.stats_lbl.SetLabel(f"Messages: {self.message_count}")

        formatted = format_json_message(message)
        current = self.recv_txt.GetValue()
        if current:
            current += "\n---\n"
        self.recv_txt.SetValue(current + f"[{group}] {formatted}")


class ScatterPanel(wx.Panel, RecentMessagesMixin, SplitterInitMixin):
    """UI Panel for SCATTER socket - round-robin distribution (draft API)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.is_bound = False

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Top Sizer (Port, Bind button)
        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.port_lbl = wx.StaticText(self, label="Port:")
        default_port = Config.get(CONFIG_SCATTER_PORT_KEY, "5557")
        self.port_txt = wx.TextCtrl(self, value=str(default_port), size=(100, -1))

        self.bind_btn = wx.Button(self, label="Bind")

        self.top_sizer.Add(self.port_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.port_txt, 0, wx.EXPAND | wx.ALL, 5)
        self.top_sizer.Add(self.bind_btn, 0, wx.CENTER | wx.ALL, 5)

        # Horizontal splitter for message/recent
        self.h_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # Message panel
        self.msg_panel = wx.Panel(self.h_splitter)
        self.msg_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_lbl = wx.StaticText(self.msg_panel, label="Message to Distribute:")
        self.send_txt = wx.TextCtrl(self.msg_panel, style=wx.TE_MULTILINE)
        self.msg_sizer.Add(self.send_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.msg_sizer.Add(self.send_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.msg_panel.SetSizer(self.msg_sizer)

        # Recent panel
        self.recent_panel = wx.Panel(self.h_splitter)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_lbl = wx.StaticText(self.recent_panel, label="Recent Messages:")
        self.recent_list = wx.ListBox(self.recent_panel)
        self.recent_sizer.Add(self.recent_lbl, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND | wx.ALL, 5)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.h_splitter.SplitVertically(self.msg_panel, self.recent_panel)
        self.h_splitter.SetSashGravity(0.6)
        self.h_splitter.SetMinimumPaneSize(200)

        # Control Sizer
        self.ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.send_btn = wx.Button(self, label="Scatter")
        self.send_btn.Enable(False)
        self.ctrl_sizer.AddStretchSpacer(1)
        self.ctrl_sizer.Add(self.send_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.main_sizer.Add(self.top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.h_splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.ctrl_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.bind_btn.Bind(wx.EVT_BUTTON, self.on_bind_toggle)
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send_message)

        # Setup mixins with 0.6 ratio for horizontal splitter
        self.setup_recent_messages(CONFIG_RECENT_SENT_MSGS_SCATTER_KEY, self.send_txt, self.recent_list)
        self.setup_splitter_init(self.h_splitter, None, h_ratio=0.6)

    def on_bind_toggle(self, event):
        if self.is_bound:
            Scatter().unbind()
            self.is_bound = False
            self.bind_btn.SetLabel("Bind")
            self.send_btn.Enable(False)
            self.port_txt.Enable(True)
        else:
            port = self.port_txt.GetValue().strip()
            if not port.isdigit():
                wx.MessageBox("Please enter a valid port number", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            Config.set(CONFIG_SCATTER_PORT_KEY, port)
            success, message = Scatter().bind(port)

            if success:
                self.is_bound = True
                self.bind_btn.SetLabel("Unbind")
                self.send_btn.Enable(True)
                self.port_txt.Enable(False)
            else:
                wx.MessageBox(message, "Bind Error", wx.OK | wx.ICON_ERROR)

    def on_send_message(self, event):
        message = self.send_txt.GetValue()
        if not message:
            wx.MessageBox("Please enter a message", "Input Error", wx.OK | wx.ICON_WARNING)
            return

        success, msg = Scatter().send_message(message)
        if not success:
            wx.MessageBox(msg, "Send Error", wx.OK | wx.ICON_ERROR)
            return

        self.add_to_recent(message)


class GatherPanel(wx.Panel):
    """UI Panel for GATHER socket - fair-queued receive (draft API)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.is_running = False

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Top Sizer (Address, Start button)
        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.addr_lbl = wx.StaticText(self, label="Scatter Address:")
        default_addr = Config.get(CONFIG_GATHER_ADDRESS_KEY, "tcp://localhost:5557")
        self.addr_txt = wx.TextCtrl(self, value=default_addr, size=(200, -1))

        self.start_btn = wx.Button(self, label="Start")

        self.top_sizer.Add(self.addr_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.addr_txt, 0, wx.EXPAND | wx.ALL, 5)
        self.top_sizer.Add(self.start_btn, 0, wx.CENTER | wx.ALL, 5)

        # Received messages
        self.recv_lbl = wx.StaticText(self, label="Gathered Messages:")
        self.recv_txt = wx.TextCtrl(
            self,
            value="\n\n\n\t\tMessages from Scatter will appear here",
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )

        # Stats
        self.stats_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.stats_lbl = wx.StaticText(self, label="Messages: 0 | Data: 0 B | Speed: 0 B/s")
        self.clear_btn = wx.Button(self, label="Clear")
        self.stats_sizer.Add(self.stats_lbl, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.stats_sizer.Add(self.clear_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.main_sizer.Add(self.top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.recv_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.recv_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.stats_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.start_btn.Bind(wx.EVT_BUTTON, self.on_start_toggle)
        self.clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)

        Gather().set_callback(self.recv_message)

    def on_start_toggle(self, event):
        if self.is_running:
            Gather().stop()
            self.is_running = False
            self.start_btn.SetLabel("Start")
            self.addr_txt.Enable(True)
        else:
            addr = self.addr_txt.GetValue().strip()
            if not addr:
                wx.MessageBox("Please enter a Scatter address", "Input Error", wx.OK | wx.ICON_WARNING)
                return

            Config.set(CONFIG_GATHER_ADDRESS_KEY, addr)
            success, message = Gather().start(addr)

            if success:
                self.is_running = True
                self.start_btn.SetLabel("Stop")
                self.addr_txt.Enable(False)
                self.recv_txt.SetValue("")
            else:
                wx.MessageBox(message, "Connection Error", wx.OK | wx.ICON_ERROR)

    def on_clear(self, event):
        self.recv_txt.SetValue("")
        Gather().message_count = 0
        Gather().total_bytes = 0
        Gather().start_time = time.time()
        self.stats_lbl.SetLabel("Messages: 0 | Data: 0 B | Speed: 0 B/s")

    def recv_message(self, message):
        gather = Gather()
        elapsed = time.time() - gather.start_time if gather.start_time else 1
        speed = gather.total_bytes / elapsed if elapsed > 0 else 0

        stats = f"Messages: {gather.message_count} | Data: {format_bytes(gather.total_bytes)} | Speed: {format_speed(speed)}"
        self.stats_lbl.SetLabel(stats)

        formatted = format_json_message(message)
        current = self.recv_txt.GetValue()
        if current.startswith("\n\n\n\t\t"):
            current = ""
        if current:
            current += "\n---\n"
        self.recv_txt.SetValue(current + formatted)


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="ZmqAnalyzer", size=(1200, 800))

        self.notebook = wx.Notebook(self)

        self.publisher_panel = PublisherPanel(self.notebook)
        self.subscriber_panel = SubscriberPanel(self.notebook)
        self.xpub_panel = XPublisherPanel(self.notebook)
        self.xsub_panel = XSubscriberPanel(self.notebook)
        self.requester_panel = RequesterPanel(self.notebook)
        self.replyer_panel = ReplyerPanel(self.notebook)
        self.dealer_panel = DealerPanel(self.notebook)
        self.router_panel = RouterPanel(self.notebook)
        self.client_panel = ClientPanel(self.notebook)
        self.server_panel = ServerPanel(self.notebook)
        self.pusher_panel = PusherPanel(self.notebook)
        self.puller_panel = PullerPanel(self.notebook)
        self.radio_panel = RadioPanel(self.notebook)
        self.dish_panel = DishPanel(self.notebook)
        self.scatter_panel = ScatterPanel(self.notebook)
        self.gather_panel = GatherPanel(self.notebook)
        self.pair_panel = PairPanel(self.notebook)
        self.stream_panel = StreamPanel(self.notebook)

        self.notebook.AddPage(self.publisher_panel, "Publish")
        self.notebook.AddPage(self.subscriber_panel, "Subscribe")
        self.notebook.AddPage(self.xpub_panel, "XPub")
        self.notebook.AddPage(self.xsub_panel, "XSub")
        self.notebook.AddPage(self.requester_panel, "Request")
        self.notebook.AddPage(self.replyer_panel, "Reply")
        self.notebook.AddPage(self.dealer_panel, "Dealer")
        self.notebook.AddPage(self.router_panel, "Router")
        self.notebook.AddPage(self.client_panel, "Client")
        self.notebook.AddPage(self.server_panel, "Server")
        self.notebook.AddPage(self.pusher_panel, "Push")
        self.notebook.AddPage(self.puller_panel, "Pull")
        self.notebook.AddPage(self.radio_panel, "Radio")
        self.notebook.AddPage(self.dish_panel, "Dish")
        self.notebook.AddPage(self.scatter_panel, "Scatter")
        self.notebook.AddPage(self.gather_panel, "Gather")
        self.notebook.AddPage(self.pair_panel, "Pair")
        self.notebook.AddPage(self.stream_panel, "Stream")

        # Menu
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        exit_item = file_menu.Append(wx.ID_EXIT, "Exit", "Exit application")
        menubar.Append(file_menu, "&File")

        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "About", "About ZmqAnalyzer")
        menubar.Append(help_menu, "&Help")

        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_about(self, event):
        info = wx.adv.AboutDialogInfo()
        info.SetName("ZmqAnalyzer")
        info.SetVersion("1.0.0")
        info.SetDescription(
            "A desktop GUI application for testing and debugging ZeroMQ messaging.\n"
            "Like Postman, but for ZMQ.\n\n"
            "Supports PUB/SUB, REQ/REP, PUSH/PULL, DEALER/ROUTER,\n"
            "CLIENT/SERVER, RADIO/DISH, SCATTER/GATHER, PAIR,\n"
            "XPUB/XSUB, and STREAM patterns."
        )
        info.SetCopyright("(C) 2025 Renda Yigit")
        info.SetWebSite("https://github.com/rendayigit/ZmqAnalyzer")
        info.AddDeveloper("Renda Yigit")
        info.AddDeveloper("GitHub Copilot")
        wx.adv.AboutBox(info)

    def on_exit(self, event):
        self.Close()

    def on_close(self, event):
        # Clean shutdown of all sockets
        print("Shutting down ZmqAnalyzer...")
        Subscriber().stop()
        Publisher().unbind()
        Replyer().unbind()
        Pusher().unbind()
        Puller().stop()
        Dealer().disconnect()
        Router().unbind()
        PairSocket().stop()
        XPublisher().unbind()
        XSubscriber().stop()
        StreamSocket().stop()
        # Draft API sockets
        Client().disconnect()
        Server().unbind()
        Radio().unbind()
        Dish().stop()
        Scatter().unbind()
        Gather().stop()
        event.Skip()


class ZmqAnalyzerApp(wx.App):
    def OnInit(self):
        Config.load()
        frame = MainFrame()
        frame.Show()
        return True


if __name__ == "__main__":
    app = ZmqAnalyzerApp()
    app.MainLoop()
