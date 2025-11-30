import json
import os
import threading
import time
import wx
import wx.dataview
import zmq

# Constants
CONFIG_FILE = os.path.expanduser("~/.zmqanalyzer-config.json")
CONFIG_PUBLISHER_PORT_KEY = "publisher_port"
CONFIG_SUBSCRIBER_TOPICS_KEY = "subscriber_topics"
CONFIG_SUBSCRIBER_ADDRESS_KEY = "subscriber_address"
CONFIG_REQUESTER_ADDRESS_KEY = "requester_address"
CONFIG_REPLYER_ADDRESS_KEY = "replyer_address"
CONFIG_RECENT_SENT_MSGS_PUB_KEY = "recent_sent_msgs_pub"
CONFIG_RECENT_SENT_MSGS_REQ_KEY = "recent_sent_msgs_req"
CONFIG_RECENT_SENT_MSGS_REP_KEY = "recent_sent_msgs_rep"


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


# --- UI Classes ---


class BaseComPanel(wx.Panel):
    def __init__(self, parent, connection_address, recent_msgs_key, send_callback):
        super().__init__(parent)
        self.recent_msgs_key = recent_msgs_key
        self.send_callback = send_callback

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Top Sizer (Address)
        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.address_lbl = wx.StaticText(self, label="Connection address:")
        self.address_txt = wx.TextCtrl(self, value=connection_address, size=(200, -1))
        self.top_sizer.Add(self.address_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.top_sizer.Add(self.address_txt, 0, wx.EXPAND | wx.ALL, 5)

        # Msg Sizer (Send/Recv)
        self.msg_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Send Side
        self.send_sizer = wx.BoxSizer(wx.VERTICAL)
        self.send_lbl = wx.StaticText(self, label="Send:")
        self.send_txt = wx.TextCtrl(
            self,
            value="Enter your message here",
            style=wx.TE_MULTILINE,
            size=(400, 150),
        )

        self.recent_panel = wx.Panel(self, style=wx.BORDER_SUNKEN)
        self.recent_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recent_list = wx.ListCtrl(self.recent_panel, style=wx.LC_REPORT)
        self.recent_list.InsertColumn(0, "Recently Sent Messages", width=450)
        self.recent_sizer.Add(self.recent_list, 1, wx.EXPAND)
        self.recent_panel.SetSizer(self.recent_sizer)

        self.send_sizer.Add(self.send_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.send_sizer.Add(self.send_txt, 1, wx.EXPAND | wx.ALL, 5)
        self.send_sizer.Add(self.recent_panel, 1, wx.EXPAND | wx.ALL, 5)

        # Recv Side
        self.recv_sizer = wx.BoxSizer(wx.VERTICAL)
        self.recv_lbl = wx.StaticText(self, label="Received:")
        self.recv_txt = wx.TextCtrl(
            self,
            value="\n\n\n\t\t\tReceived message will be displayed here",
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self.recv_sizer.Add(self.recv_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.recv_sizer.Add(self.recv_txt, 1, wx.EXPAND | wx.ALL, 5)

        self.msg_sizer.Add(self.send_sizer, 1, wx.EXPAND | wx.ALL, 5)
        self.msg_sizer.Add(self.recv_sizer, 1, wx.EXPAND | wx.ALL, 5)

        # Control Sizer
        self.ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.send_btn = wx.Button(self, label="Send Message")
        self.ctrl_sizer.AddStretchSpacer(1)
        self.ctrl_sizer.Add(self.send_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.main_sizer.Add(self.top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.msg_sizer, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.ctrl_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        # Bindings
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send_message)
        self.recent_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_recent_selected)
        self.recent_list.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_recent_right_click)

        # Load Config
        self.load_recent_messages()

    def load_recent_messages(self):
        msgs = Config.get_list(self.recent_msgs_key)
        for msg in msgs:
            self.recent_list.InsertItem(0, msg)

    def on_send_message(self, event):
        message = self.send_txt.GetValue()
        if self.send_callback:
            self.send_callback(message)

        # Add to recent
        found = False
        for i in range(self.recent_list.GetItemCount()):
            if self.recent_list.GetItemText(i) == message:
                found = True
                break

        if not found:
            self.recent_list.InsertItem(0, message)
            Config.add_to_list(self.recent_msgs_key, message)

    def recv_message(self, message):
        """Display received message with JSON formatting if applicable."""
        try:
            # Try to format JSON
            if isinstance(message, str):
                parsed = json.loads(message)
                self.recv_txt.SetValue(json.dumps(parsed, indent=2))
            elif isinstance(message, dict):
                self.recv_txt.SetValue(json.dumps(message, indent=2))
            else:
                self.recv_txt.SetValue(str(message))
        except json.JSONDecodeError:
            self.recv_txt.SetValue(str(message))
        except Exception as e:
            print(f"Error displaying message: {e}")
            self.recv_txt.SetValue(str(message))

    def get_connection_address(self):
        return self.address_txt.GetValue()

    def on_recent_selected(self, event):
        item = event.GetIndex()
        if item != -1:
            self.send_txt.SetValue(self.recent_list.GetItemText(item))

    def on_recent_right_click(self, event):
        menu = wx.Menu()
        use_item = menu.Append(wx.ID_ANY, "Use Message")
        copy_item = menu.Append(wx.ID_COPY, "Copy Message")
        del_item = menu.Append(wx.ID_DELETE, "Delete Message")

        self.Bind(wx.EVT_MENU, self.on_use_context, use_item)
        self.Bind(wx.EVT_MENU, self.on_copy_context, copy_item)
        self.Bind(wx.EVT_MENU, self.on_delete_context, del_item)

        self.PopupMenu(menu)
        menu.Destroy()

    def on_use_context(self, event):
        item = self.recent_list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if item != -1:
            self.send_txt.SetValue(self.recent_list.GetItemText(item))

    def on_copy_context(self, event):
        item = self.recent_list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if item != -1:
            text = self.recent_list.GetItemText(item)
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.TheClipboard.Close()

    def on_delete_context(self, event):
        item = self.recent_list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if item != -1:
            msg = self.recent_list.GetItemText(item)
            self.recent_list.DeleteItem(item)
            Config.remove_from_list(self.recent_msgs_key, msg)


class RequesterPanel(BaseComPanel):
    def __init__(self, parent):
        default_addr = Config.get(CONFIG_REQUESTER_ADDRESS_KEY, "tcp://localhost:5555")
        super().__init__(parent, default_addr, CONFIG_RECENT_SENT_MSGS_REQ_KEY, self.send_request)
        Requester().set_callback(self.recv_message)

    def send_request(self, message):
        addr = self.get_connection_address()
        Config.set(CONFIG_REQUESTER_ADDRESS_KEY, addr)
        Requester().request(message, addr)


class ReplyerPanel(BaseComPanel):
    def __init__(self, parent):
        default_addr = Config.get(CONFIG_REPLYER_ADDRESS_KEY, "tcp://*:5555")
        super().__init__(parent, default_addr, CONFIG_RECENT_SENT_MSGS_REP_KEY, self.send_reply)

        # Add Bind/Unbind buttons for Replyer
        self.bind_btn = wx.Button(self, label="Bind")
        self.unbind_btn = wx.Button(self, label="Unbind")
        self.unbind_btn.Enable(False)
        self.ctrl_sizer.Insert(0, self.bind_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.ctrl_sizer.Insert(1, self.unbind_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.bind_btn.Bind(wx.EVT_BUTTON, self.on_bind)
        self.unbind_btn.Bind(wx.EVT_BUTTON, self.on_unbind)
        
        # Disable send button until bound
        self.send_btn.Enable(False)

        Replyer().set_callback(self.on_request_received)

    def on_bind(self, event):
        addr = self.get_connection_address().strip()
        if not addr:
            wx.MessageBox("Please enter a connection address", "Input Error", wx.OK | wx.ICON_WARNING)
            return
        
        Config.set(CONFIG_REPLYER_ADDRESS_KEY, addr)
        success, message = Replyer().bind(addr)
        
        if success:
            self.bind_btn.Enable(False)
            self.unbind_btn.Enable(True)
            self.send_btn.Enable(True)
            self.address_txt.Enable(False)
            wx.MessageBox(message, "Success", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox(message, "Bind Error", wx.OK | wx.ICON_ERROR)

    def on_unbind(self, event):
        success, message = Replyer().unbind()
        if success:
            self.bind_btn.Enable(True)
            self.unbind_btn.Enable(False)
            self.send_btn.Enable(False)
            self.address_txt.Enable(True)
        else:
            wx.MessageBox(message, "Unbind Error", wx.OK | wx.ICON_ERROR)

    def on_request_received(self, message):
        self.recv_message(message)
        # In Replyer, "Received" is the request, "Send" is the reply.
        # The user sees the request in "Received" box, types reply in "Send" box and clicks "Send Message".

    def send_reply(self, message):
        Replyer().send_reply(message)


class PublisherPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Controls
        self.controls_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.port_lbl = wx.StaticText(self, label="Port:")
        self.port_txt = wx.TextCtrl(self, value=Config.get(CONFIG_PUBLISHER_PORT_KEY, "5556"), size=(80, -1))

        self.topic_lbl = wx.StaticText(self, label="Topic:")
        self.topic_txt = wx.TextCtrl(self, value="test", size=(100, -1))

        self.bind_btn = wx.Button(self, label="Bind")
        self.unbind_btn = wx.Button(self, label="Unbind")
        self.unbind_btn.Enable(False)

        self.controls_sizer.Add(self.port_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.port_txt, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.bind_btn, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.unbind_btn, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.topic_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.topic_txt, 0, wx.CENTER | wx.ALL, 5)

        # Message Area
        self.msg_sizer = wx.BoxSizer(wx.VERTICAL)
        self.msg_lbl = wx.StaticText(self, label="Message:")
        self.msg_txt = wx.TextCtrl(self, value="Hello World", style=wx.TE_MULTILINE, size=(-1, 150))
        self.msg_sizer.Add(self.msg_lbl, 0, wx.EXPAND | wx.ALL, 5)
        self.msg_sizer.Add(self.msg_txt, 1, wx.EXPAND | wx.ALL, 5)

        # Recent List
        self.recent_list = wx.ListCtrl(self, style=wx.LC_REPORT)
        self.recent_list.InsertColumn(0, "Recently Published Messages", width=500)

        # Publish Button
        self.pub_btn = wx.Button(self, label="Publish Message")
        self.pub_btn.Enable(False)

        self.main_sizer.Add(self.controls_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.msg_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.recent_list, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.pub_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.bind_btn.Bind(wx.EVT_BUTTON, self.on_bind)
        self.unbind_btn.Bind(wx.EVT_BUTTON, self.on_unbind)
        self.pub_btn.Bind(wx.EVT_BUTTON, self.on_publish)
        self.recent_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_recent_selected)
        self.recent_list.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_recent_right_click)

        self.load_recent()

    def on_bind(self, event):
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
            self.bind_btn.Enable(False)
            self.unbind_btn.Enable(True)
            self.pub_btn.Enable(True)
            self.port_txt.Enable(False)
            wx.MessageBox(message, "Success", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox(message, "Bind Error", wx.OK | wx.ICON_ERROR)

    def on_unbind(self, event):
        success, message = Publisher().unbind()
        if success:
            self.bind_btn.Enable(True)
            self.unbind_btn.Enable(False)
            self.pub_btn.Enable(False)
            self.port_txt.Enable(True)
        else:
            wx.MessageBox(message, "Unbind Error", wx.OK | wx.ICON_ERROR)

    def load_recent(self):
        msgs = Config.get_list(CONFIG_RECENT_SENT_MSGS_PUB_KEY)
        for msg in msgs:
            self.recent_list.InsertItem(0, msg)

    def on_publish(self, event):
        topic = self.topic_txt.GetValue().strip()
        message = self.msg_txt.GetValue()

        if not topic:
            wx.MessageBox("Please enter a topic", "Input Error", wx.OK | wx.ICON_WARNING)
            return

        success, msg = Publisher().send_message(topic, message)
        if not success:
            wx.MessageBox(msg, "Publish Error", wx.OK | wx.ICON_ERROR)
            return

        # Add to recent
        found = False
        for i in range(self.recent_list.GetItemCount()):
            if self.recent_list.GetItemText(i) == message:
                found = True
                break
        if not found:
            self.recent_list.InsertItem(0, message)
            Config.add_to_list(CONFIG_RECENT_SENT_MSGS_PUB_KEY, message)

    def on_recent_selected(self, event):
        item = event.GetIndex()
        if item != -1:
            self.msg_txt.SetValue(self.recent_list.GetItemText(item))

    def on_recent_right_click(self, event):
        menu = wx.Menu()
        use_item = menu.Append(wx.ID_ANY, "Use Message")
        copy_item = menu.Append(wx.ID_COPY, "Copy Message")
        del_item = menu.Append(wx.ID_DELETE, "Delete Message")

        self.Bind(wx.EVT_MENU, self.on_use_context, use_item)
        self.Bind(wx.EVT_MENU, self.on_copy_context, copy_item)
        self.Bind(wx.EVT_MENU, self.on_delete_context, del_item)

        self.PopupMenu(menu)
        menu.Destroy()

    def on_use_context(self, event):
        item = self.recent_list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if item != -1:
            self.msg_txt.SetValue(self.recent_list.GetItemText(item))

    def on_copy_context(self, event):
        item = self.recent_list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if item != -1:
            text = self.recent_list.GetItemText(item)
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.TheClipboard.Close()

    def on_delete_context(self, event):
        item = self.recent_list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if item != -1:
            msg = self.recent_list.GetItemText(item)
            self.recent_list.DeleteItem(item)
            Config.remove_from_list(CONFIG_RECENT_SENT_MSGS_PUB_KEY, msg)


class TopicFrame(wx.Frame):
    def __init__(self, parent, topic):
        super().__init__(parent, title=f"Topic: {topic}", size=(400, 300))
        self.topic = topic
        self.panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.text = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 5)
        self.panel.SetSizer(self.sizer)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Show()

    def update_message(self, message):
        if isinstance(message, dict):
            self.text.SetValue(json.dumps(message, indent=2))
        else:
            self.text.SetValue(str(message))

    def on_close(self, event):
        self.Destroy()


class SubscriberPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.topic_frames = {}

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

        self.start_btn = wx.Button(self, label="Start")
        self.stop_btn = wx.Button(self, label="Stop")

        self.controls_sizer.Add(self.addr_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.addr_txt, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.topic_lbl, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.topic_txt, 1, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.start_btn, 0, wx.CENTER | wx.ALL, 5)
        self.controls_sizer.Add(self.stop_btn, 0, wx.CENTER | wx.ALL, 5)

        # Message List
        self.msg_list = wx.dataview.DataViewListCtrl(self)
        self.msg_list.AppendTextColumn("Topic", width=100)
        self.msg_list.AppendTextColumn("Message", width=400)

        self.main_sizer.Add(self.controls_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.msg_list, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.main_sizer)

        self.start_btn.Bind(wx.EVT_BUTTON, self.on_start)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.on_stop)
        self.msg_list.Bind(wx.dataview.EVT_DATAVIEW_ITEM_ACTIVATED, self.on_item_activated)

        Subscriber().set_callback(self.on_message_received)

    def on_start(self, event):
        addr = self.addr_txt.GetValue().strip()
        topics_str = self.topic_txt.GetValue().strip()
        
        if not addr:
            wx.MessageBox("Please enter an address", "Input Error", wx.OK | wx.ICON_WARNING)
            return
        
        if not topics_str:
            wx.MessageBox("Please enter at least one topic", "Input Error", wx.OK | wx.ICON_WARNING)
            return
        
        topics = [t.strip() for t in topics_str.split(",") if t.strip()]

        Config.set(CONFIG_SUBSCRIBER_ADDRESS_KEY, addr)
        Config.set(CONFIG_SUBSCRIBER_TOPICS_KEY, topics_str)

        success, message = Subscriber().start(topics, addr)
        if success:
            wx.MessageBox(message, "Success", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox(message, "Connection Error", wx.OK | wx.ICON_ERROR)

    def on_stop(self, event):
        Subscriber().stop()

    def on_message_received(self, topic, message):
        # Update list
        # Check if topic exists in list, update it, or add new
        found = False
        msg_str = json.dumps(message) if isinstance(message, dict) else str(message)

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


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="ZmqAnalyzer (Python)", size=(800, 600))

        self.notebook = wx.Notebook(self)

        self.publisher_panel = PublisherPanel(self.notebook)
        self.subscriber_panel = SubscriberPanel(self.notebook)
        self.requester_panel = RequesterPanel(self.notebook)
        self.replyer_panel = ReplyerPanel(self.notebook)

        self.notebook.AddPage(self.publisher_panel, "Publisher")
        self.notebook.AddPage(self.subscriber_panel, "Subscriber")
        self.notebook.AddPage(self.requester_panel, "Requester")
        self.notebook.AddPage(self.replyer_panel, "Replyer")

        # Menu
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        exit_item = file_menu.Append(wx.ID_EXIT, "Exit", "Exit application")
        menubar.Append(file_menu, "&File")
        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_exit(self, event):
        self.Close()

    def on_close(self, event):
        # Clean shutdown of all sockets
        print("Shutting down ZmqAnalyzer...")
        Subscriber().stop()
        Publisher().unbind()
        Replyer().unbind()
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
