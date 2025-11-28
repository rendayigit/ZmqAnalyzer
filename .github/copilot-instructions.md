# ZmqAnalyzer AI Coding Instructions

## Project Overview
ZmqAnalyzer is a C++17 desktop application acting as a "Postman for ZeroMQ". It allows users to interact with ZeroMQ sockets (Publisher, Subscriber, Requester) via a GUI built with wxWidgets.

## Architecture & Patterns

### Core Components
- **Entry Point**: `src/main.cpp` initializes the wxWidgets application and `MainFrame`.
- **Main UI**: `MainFrame` (`src/mainFrame.cpp`) manages a `wxNotebook` containing tabs for different ZMQ patterns.
- **Panel Hierarchy**:
  - `BaseComPanel` (`src/baseComPanel/`): Base class for all communication panels. Handles common UI elements (address bar, message history, send/receive logs) and logic.
  - Specific Panels (`PublisherPanel`, `SubscriberPanel`, `RequesterPanel`): Inherit from `BaseComPanel` and implement pattern-specific behavior.
- **ZMQ Logic**:
  - Encapsulated in Singleton classes (`Publisher`, `Subscriber`, `Requester`) located in their respective directories (e.g., `src/publisher/publisher.cpp`).
  - Accessed via `getInstance()`.
  - Decoupled from UI using `std::function` callbacks passed to panel constructors.

### Data Flow
1. **User Action**: User clicks "Send" in a panel (e.g., `PublisherPanel`).
2. **UI Event**: `BaseComPanel::onSendMessage` is triggered.
3. **Callback**: The panel invokes the `sendMessageCallback` provided during construction.
4. **Logic Execution**: The callback calls the corresponding method in the ZMQ singleton (e.g., `Publisher::queueMessage`).
5. **Configuration**: Persistent data (like recent messages) is handled by `Config` (`src/config/`) using `nlohmann/json`.

## Build & Workflow

### Build System
- **CMake**: The project uses CMake (3.21+).
- **Source Management**: Source files are listed in `src/SourceFiles.cmake`. **Always update this file when adding new source files.**
- **Scripts**: Use the provided scripts in `scripts/` for standard workflows.
  - **Build**: `./scripts/build.sh` (Configures Debug build and compiles).
  - **Run**: `./scripts/run.sh`.
  - **Clean**: `./scripts/clean.sh`.

### Dependencies
- **GUI**: wxWidgets (found via `wx-config`).
- **Messaging**: ZeroMQ (`libzmq`, `cppzmq`).
- **Utilities**: Boost (filesystem, program_options), `nlohmann/json`, `spdlog`, `fmt`.

## Coding Conventions
- **C++ Standard**: C++17.
- **Logging**: Use `spdlog` via the `Logger` class (`src/logger/`).
- **Configuration**: Use `Config::getValueFromConfig` and `Config::updateKeyInConfig` for persistent settings.
- **UI/Logic Separation**: Keep ZMQ socket management strictly within the logic classes (`Publisher`, `Subscriber`, etc.), not in the UI panels.
