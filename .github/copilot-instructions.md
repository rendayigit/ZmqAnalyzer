# ZmqAnalyzer AI Coding Instructions

## Project Overview
ZmqAnalyzer is a Python desktop application acting as a "Postman for ZeroMQ". It allows users to interact with ZeroMQ sockets via a GUI built with wxPython.

### Supported ZMQ Patterns
- **PUB/SUB**: Publish/Subscribe - one-to-many message broadcast with topic filtering
- **REQ/REP**: Request/Reply - synchronous RPC-style communication
- **PUSH/PULL**: Pipeline - task distribution with load balancing
- **DEALER/ROUTER**: Advanced async request/reply - handle multiple clients without blocking
- **PAIR**: Exclusive pair - simple 1:1 bidirectional connection

## Architecture & Patterns

### Core Components
- **Single Script**: `zmq_analyzer.py` contains the entire application logic.
- **Main UI**: `MainFrame` manages a `wx.Notebook` containing tabs for different ZMQ patterns.
- **Panel Hierarchy**:
  - `BaseComPanel`: Base class for Requester panel. Handles common UI elements (address input, send/receive text areas, recent messages list).
  - `PublisherPanel`: Standalone panel for PUB pattern with port-based binding.
  - `SubscriberPanel`: Standalone panel for SUB pattern with topic filtering and statistics.
  - `ReplyerPanel`: Standalone panel for REP pattern with port-based binding.
  - `PusherPanel`: Standalone panel for PUSH pattern with port-based binding.
  - `PullerPanel`: Standalone panel for PULL pattern with connect and message statistics.
  - `DealerPanel`: Standalone panel for DEALER pattern with async send/receive.
  - `RouterPanel`: Standalone panel for ROUTER pattern with port-based binding.
  - `PairPanel`: Standalone panel for PAIR pattern with bind/connect mode selection.
  - `TopicFrame`: Popup window for viewing individual topic messages in Subscriber.
- **ZMQ Logic**:
  - Encapsulated in Singleton classes (`Publisher`, `Subscriber`, `Requester`, `Replyer`, `Pusher`, `Puller`, `Dealer`, `Router`, `PairSocket`).
  - Uses `pyzmq` for ZeroMQ interactions.
  - Threading is used for receiving messages to avoid blocking the UI.
  - `wx.CallAfter` is used to update UI from background threads.
  - Timer-based throttling in `TopicFrame` to handle rapid message updates.
  - Send timeouts used where appropriate (e.g., PAIR socket) to prevent blocking.

### Data Flow
1. **User Action**: User clicks "Bind"/"Unbind", "Start"/"Stop", or "Send"/"Publish".
2. **UI Event**: Event handler calls ZMQ singleton method.
3. **ZMQ Logic**: Performs socket operation (bind/unbind/send/recv).
4. **Callback**: On receive, a callback updates the UI via `wx.CallAfter`.
5. **Configuration**: Persistent data is handled by `Config` class using `json` module, stored in `~/.zmqanalyzer-config.json`.

### UI Patterns
- **Toggle Buttons**: Single buttons that switch between states (Bind/Unbind, Start/Stop) instead of separate button pairs.
- **JSON Formatting**: Messages are automatically pretty-printed if they are valid JSON.
- **Error Dialogs**: `wx.MessageBox` is used for displaying errors and warnings to users.
- **Message Truncation**: Large messages (>100KB) are truncated in display to prevent UI freezing.

## Build & Workflow

### Dependencies
- **Python 3.x**
- **wxPython**
- **pyzmq**

### Installation
- `install.sh`: Installs the application system-wide with desktop shortcut (requires sudo).
- `uninstall.sh`: Removes the installation (requires sudo).

## Coding Conventions
- **Language**: Python 3.
- **UI Library**: wxPython.
- **Threading**: Use `threading` module for blocking ZMQ operations. Always use `wx.CallAfter` for UI updates from threads.
- **Logging**: Use `print()` statements for console output (no logging module).
- **Error Handling**: Show user-facing errors via `wx.MessageBox`, print technical details to console.
