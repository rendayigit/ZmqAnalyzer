# wxWidgets C++ GUI Template

A simple C++ GUI application template using the wxWidgets framework.

## Project Structure

```text
├── CMakeLists.txt                  # Main CMake configuration
├── scripts/
│   ├── build.sh                    # Build script
│   ├── run.sh                      # Run application script
│   ├── clean.sh                    # Clean build artifacts
│   └── install_dependencies.sh     # Ubuntu/Debian dependency installer
└── src/
    ├── main.cpp                    # Application entry point
    ├── mainFrame.cpp               # Main window implementation
    ├── mainFrame.hpp               # Main window header
    └── SourceFiles.cmake           # Source files configuration
```

## Prerequisites

### Ubuntu/Debian

Run the provided dependency installation script:

```bash
chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh
```

### Manual Installation

Ensure you have the following installed:

- CMake (3.21 or higher)
- C++ compiler with C++17 support (GCC/Clang)
- wxWidgets development libraries
- Build tools (make, etc.)

## Building and Running

### Using VS Code Tasks

If you're using VS Code, you can use the predefined tasks:

- **Ctrl+Shift+P** → "Tasks: Run Task" → "Build App"
- **Ctrl+Shift+P** → "Tasks: Run Task" → "Run App"

### Using Scripts

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Build the application
./scripts/build.sh

# Run the application
./scripts/run.sh

# Clean build artifacts
./scripts/clean.sh
```

### Manual Build

```bash
mkdir build
cd build
cmake ..
make
./bin/app
```

## License

This is a template project - feel free to use it as a starting point for your own wxWidgets applications.
