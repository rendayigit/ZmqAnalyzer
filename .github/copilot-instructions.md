# ZmqAnalyzer AI Coding Instructions

## Project Overview

ZmqAnalyzer is a Python desktop application acting as a "Postman for ZeroMQ". It allows users to interact with ZeroMQ sockets via a GUI built with wxPython.

### Supported ZMQ Patterns

- **PUB/SUB**: Publish/Subscribe - one-to-many message broadcast with topic filtering
- **REQ/REP**: Request/Reply - synchronous RPC-style communication
- **PUSH/PULL**: Pipeline - task distribution with load balancing
- **DEALER/ROUTER**: Advanced async request/reply - handle multiple clients without blocking
- **CLIENT/SERVER**: Thread-safe async request/reply (draft API)
- **RADIO/DISH**: Group-based multicast messaging (draft API)
- **SCATTER/GATHER**: Round-robin distribution with fair-queued collection (draft API)
- **PAIR**: Exclusive pair - simple 1:1 bidirectional connection
- **XPUB/XSUB**: Extended PUB/SUB - for building brokers, shows subscription events
- **STREAM**: Raw TCP - connect to non-ZMQ peers (HTTP servers, etc.)

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
  - `ClientPanel`: Standalone panel for CLIENT pattern (draft API) with async send/receive.
  - `ServerPanel`: Standalone panel for SERVER pattern (draft API) with port-based binding.
  - `RadioPanel`: Standalone panel for RADIO pattern (draft API) with group-based broadcast.
  - `DishPanel`: Standalone panel for DISH pattern (draft API) with group-based receive.
  - `ScatterPanel`: Standalone panel for SCATTER pattern (draft API) with round-robin distribution.
  - `GatherPanel`: Standalone panel for GATHER pattern (draft API) with fair-queued receive.
  - `PairPanel`: Standalone panel for PAIR pattern with bind/connect mode selection.
  - `XPublisherPanel`: Standalone panel for XPUB pattern with subscription event display.
  - `XSubscriberPanel`: Standalone panel for XSUB pattern with explicit subscription control.
  - `StreamPanel`: Standalone panel for STREAM pattern for raw TCP connections.
  - `TopicFrame`: Popup window for viewing individual topic messages in Subscriber/XSubscriber.
- **Mixins**:
  - `RecentMessagesMixin`: Provides recent messages functionality (load/save, double-click to use, right-click context menu).
  - `SplitterInitMixin`: Handles splitter initialization on panel size events (avoids code duplication across panels).
- **ZMQ Logic**:
  - Encapsulated in Singleton classes (`Publisher`, `Subscriber`, `Requester`, `Replyer`, `Pusher`, `Puller`, `Dealer`, `Router`, `Client`, `Server`, `Radio`, `Dish`, `Scatter`, `Gather`, `PairSocket`, `XPublisher`, `XSubscriber`, `StreamSocket`).
  - Uses `pyzmq` for ZeroMQ interactions.
  - Threading is used for receiving messages to avoid blocking the UI.
  - `wx.CallAfter` is used to update UI from background threads.
  - Timer-based throttling in `TopicFrame` to handle rapid message updates.
  - Send timeouts used where appropriate (e.g., PAIR socket) to prevent blocking.
  - Draft API sockets (CLIENT, SERVER, RADIO, DISH, SCATTER, GATHER) use Frame objects for routing_id and group handling.

### Statistics System

- **Sliding Window Approach**: Rate and speed statistics use a 1-second sliding window (`STATS_WINDOW_SEC = 1.0`) for instant measurements.
- **Cumulative Statistics**: Total message count and bytes are tracked cumulatively.
- **Instant Statistics**: Rate (msg/s) and speed (B/s) are calculated from data in the last 1 second only.
- **Data Structures**:
  - `topic_stats`: Cumulative stats per topic (count, bytes, first_time, last_time).
  - `recent_data`: Sliding window data as `[(timestamp, bytes), ...]` for instant rate calculation.
- **Behavior**: When communication stops, rate and speed drop to 0 immediately (within 1 second).

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
- **wxPython** (>=4.0.0)
- **pyzmq** (>=22.0.0)

### Installation

- `install.sh`: Installs the application system-wide with desktop shortcut (requires sudo).
- `uninstall.sh`: Removes the installation (requires sudo).

## Coding Conventions

- **Language**: Python 3.
- **UI Library**: wxPython.
- **Threading**: Use `threading` module for blocking ZMQ operations. Always use `wx.CallAfter` for UI updates from threads.
- **Logging**: Use `print()` statements for console output (no logging module).
- **Error Handling**: Show user-facing errors via `wx.MessageBox`, print technical details to console.
- **Exception Handling**: Always use specific exception types (e.g., `except Exception:`) instead of bare `except:`.
- **Code Style**: Use Black formatter with 150 character line length.
