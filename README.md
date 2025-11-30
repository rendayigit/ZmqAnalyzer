# ZmqAnalyzer

<p align="center">
  <img src="zmqanalyzer.png" alt="ZmqAnalyzer Logo" width="128">
</p>

A desktop GUI application for testing and debugging ZeroMQ messaging — like Postman, but for ZMQ.

## Features

### Supported ZeroMQ Patterns

| Pattern | Description |
|---------|-------------|
| **PUB/SUB** | Publish/Subscribe - one-to-many message broadcast with topic filtering |
| **REQ/REP** | Request/Reply - synchronous RPC-style communication |
| **PUSH/PULL** | Pipeline - task distribution with load balancing |
| **DEALER/ROUTER** | Advanced async request/reply - handle multiple clients without blocking |
| **PAIR** | Exclusive pair - simple 1:1 bidirectional connection |

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

### Pusher Tab (PUSH)

1. Enter a **Port** number (e.g., `5557`)
2. Click **Bind** to start the pusher
3. Type your **Message**
4. Click **Push** — messages are distributed to connected pullers in round-robin

### Puller Tab (PULL)

1. Enter the pusher **Address** (e.g., `tcp://localhost:5557`)
2. Click **Start** to begin receiving messages
3. Messages appear in the list as they arrive

### Dealer Tab (DEALER)

1. Enter a router **Address** (e.g., `tcp://localhost:5558`)
2. Click **Connect** to establish connection
3. Send multiple messages without waiting for replies (async)
4. Replies appear in the received panel

### Router Tab (ROUTER)

1. Enter a **Port** number (e.g., `5558`)
2. Click **Bind** to start listening
3. Incoming requests from dealers appear automatically
4. Type a **Reply** and click **Send** to respond

### Pair Tab (PAIR)

1. Select **Mode**: Connect (client) or Bind (server)
2. Enter **Address** (e.g., `tcp://localhost:5559`) or port number for bind mode
3. Click **Start** to establish exclusive 1:1 connection
4. Send and receive messages bidirectionally

## Configuration

Settings are automatically saved to `~/.zmqanalyzer-config.json` and restored on startup, including:

- Last used addresses and ports
- Recent messages for quick reuse
- Topic subscriptions

## Requirements

- Python 3.x
- wxPython
- pyzmq
