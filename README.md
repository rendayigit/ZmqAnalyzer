# ZmqAnalyzer

<p align="center">
  <img src="zmqanalyzer.png" alt="ZmqAnalyzer Logo" width="128">
</p>

A desktop GUI application for testing and debugging ZeroMQ messaging — like Postman, but for ZMQ.

## Features

- **Publisher**: Bind to a port and publish messages with custom topics
- **Subscriber**: Connect to publishers and filter messages by topic
- **Requester**: Send requests and receive responses (REQ/REP pattern)
- **Replyer**: Bind to a port and respond to incoming requests

### Additional Capabilities

- Real-time message statistics (rate, speed, message count)
- Recent message history with quick reuse
- JSON auto-formatting for readable output
- Topic-based message filtering and viewing
- Persistent configuration (addresses, ports, recent messages)

## Installation

### Option 1: Run Directly

```bash
# Clone the repository
git clone https://github.com/rendayigit/ZmqAnalyzer.git
cd ZmqAnalyzer

# Install dependencies
pip install -r requirements.txt

# Run the application
python zmq_analyzer.py
```

### Option 2: System-Wide Installation (Linux)

```bash
# Install with desktop shortcut
sudo ./install.sh

# To uninstall
sudo ./uninstall.sh
```

## Usage

### Publisher Tab

1. Enter a **Port** number (e.g., `5555`)
2. Click **Bind** to start the publisher
3. Enter a **Topic** and your **Message**
4. Click **Publish** to send

### Subscriber Tab

1. Enter the publisher **Address** (e.g., `tcp://localhost:5555`)
2. Enter a **Topic** to filter (leave empty for all messages)
3. Click **Start** to begin receiving messages
4. Double-click a topic in the list to view its messages in a separate window

### Requester Tab

1. Enter the replyer **Address** (e.g., `tcp://localhost:5556`)
2. Type your **Request** message
3. Click **Send** to send and wait for a response

### Replyer Tab

1. Enter a **Port** number (e.g., `5556`)
2. Click **Bind** to start listening
3. Incoming requests appear automatically
4. Type a **Response** and click **Send** to reply

## Configuration

Settings are automatically saved to `~/.zmqanalyzer-config.json` and restored on startup, including:

- Last used addresses and ports
- Recent messages for quick reuse
- Topic subscriptions

## Requirements

- Python 3.x
- wxPython
- pyzmq
