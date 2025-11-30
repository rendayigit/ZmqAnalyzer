# ZmqAnalyzer AI Coding Instructions

## Project Overview
ZmqAnalyzer is a Python desktop application acting as a "Postman for ZeroMQ". It allows users to interact with ZeroMQ sockets (Publisher, Subscriber, Requester, Replyer) via a GUI built with wxPython.

## Architecture & Patterns

### Core Components
- **Single Script**: `zmq_analyzer.py` contains the entire application logic.
- **Main UI**: `MainFrame` manages a `wx.Notebook` containing tabs for different ZMQ patterns.
- **Panel Hierarchy**:
  - `BaseComPanel`: Base class for communication panels (Requester, Replyer). Handles common UI elements.
  - `PublisherPanel`, `SubscriberPanel`: Specific panels for PUB/SUB patterns.
- **ZMQ Logic**:
  - Encapsulated in Singleton classes (`Publisher`, `Subscriber`, `Requester`, `Replyer`).
  - Uses `pyzmq` for ZeroMQ interactions.
  - Threading is used for receiving messages to avoid blocking the UI.
  - `wx.CallAfter` is used to update UI from background threads.

### Data Flow
1. **User Action**: User clicks "Send" or "Start".
2. **UI Event**: Event handler calls ZMQ singleton method.
3. **ZMQ Logic**: Performs socket operation (send/recv).
4. **Callback**: On receive, a callback updates the UI via `wx.CallAfter`.
5. **Configuration**: Persistent data is handled by `Config` class using `json` module, stored in `config.json`.

## Build & Workflow

### Dependencies
- **Python 3.x**
- **wxPython**
- **pyzmq**

### Scripts
- **Run**: `./scripts/run.sh` or `python zmq_analyzer.py`.
- **Install Deps**: `pip install -r requirements.txt`.

## Coding Conventions
- **Language**: Python 3.
- **UI Library**: wxPython.
- **Threading**: Use `threading` module for blocking ZMQ operations. Always use `wx.CallAfter` for UI updates from threads.
