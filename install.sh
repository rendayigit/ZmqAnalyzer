#!/bin/bash

# ZmqAnalyzer Installation Script
# This script installs ZmqAnalyzer to standard Linux directories

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/" && pwd)"
SCRIPT_SOURCE="$PROJECT_ROOT/zmq_analyzer.py"

echo "Project root: $PROJECT_ROOT"

# Installation path
BIN_DIR="/usr/local/bin"

# Functions to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running with sudo for system installation
check_permissions() {
    if [[ -z "$SUDO_USER" ]]; then
        print_error "SUDO_USER not set. Please run this script with sudo."
        return 1
    fi
}

# Function to install binary
install_binary() {
    print_info "Installing wrapper to $BIN_DIR..."
    
    if ! mkdir -p "$BIN_DIR"; then
        print_error "Failed to create bin directory: $BIN_DIR"
        exit 1
    fi
    
    # Create wrapper script
    WRAPPER="$BIN_DIR/zmqanalyzer"
    echo "#!/bin/bash" > "$WRAPPER"
    echo "cd \"$PROJECT_ROOT\"" >> "$WRAPPER"
    echo "python3 zmq_analyzer.py \"\$@\"" >> "$WRAPPER"
    
    # Set appropriate permissions
    chmod 755 "$WRAPPER"
    
    print_success "Wrapper installed successfully"
}

# Create desktop shortcut and copy icon for the invoking (non-root) user
create_desktop_shortcut() {
    APP_DIR="/home/$SUDO_USER/.local/share/applications"
    ICON_DIR="/home/$SUDO_USER/.local/share/icons"
    USER_DESKTOP_DIR="/home/$SUDO_USER/Desktop"
    DESKTOP_FILE_CONTENT="[Desktop Entry]\nName=Run ZmqAnalyzer\nComment=Run ZmqAnalyzer UI for the ZmqAnalyzer Engine\nExec=zmqanalyzer\nIcon=$ICON_DIR/zmqanalyzer.png\nTerminal=false\nType=Application\nCategories=Utility;\n"
    DESKTOP_FILE_PATH="$APP_DIR/zmqanalyzer.desktop"
    ICON_PATH="$PROJECT_ROOT/zmqanalyzer.png"

    mkdir -p "$APP_DIR" || { print_error "Failed to create $APP_DIR"; return 1; }
    chown $SUDO_USER:$SUDO_USER "$APP_DIR" || { print_error "Failed to set ownership for $APP_DIR"; return 1; }
    mkdir -p "$ICON_DIR" || { print_error "Failed to create $ICON_DIR"; return 1; }
    chown $SUDO_USER:$SUDO_USER "$ICON_DIR" || { print_error "Failed to set ownership for $ICON_DIR"; return 1; }

    # Write desktop file
    printf "%b" "$DESKTOP_FILE_CONTENT" > "$DESKTOP_FILE_PATH" || { print_error "Failed to write $DESKTOP_FILE_PATH"; return 1; }
    chown $SUDO_USER:$SUDO_USER "$DESKTOP_FILE_PATH" || { print_error "Failed to set ownership for $DESKTOP_FILE_PATH"; return 1; }

    # Make shortcut file executable
    chmod +x "$DESKTOP_FILE_PATH" || { print_error "Failed to set executable permissions for $DESKTOP_FILE_PATH"; return 1; }

    # Create shortcut on user's desktop
    ln -s "$DESKTOP_FILE_PATH" "$USER_DESKTOP_DIR/zmqanalyzer.desktop" || { print_error "Failed to create desktop shortcut"; return 1; }

    print_info "Created desktop shortcut in: $APP_DIR"

    # Copy icon to icon directory
    if [ -f "$ICON_PATH" ]; then
        cp "$ICON_PATH" "$ICON_DIR/zmqanalyzer.png" || { print_error "Failed to copy icon to $ICON_DIR"; return 1; }
        chown $SUDO_USER:$SUDO_USER "$ICON_DIR/zmqanalyzer.png" || { print_error "Failed to set ownership for $ICON_DIR/zmqanalyzer.png"; return 1; }
        print_info "Created icon in: $ICON_DIR"
    else
        print_warning "Icon not found at $ICON_PATH, skipping icon copy."
    fi

    print_success "Desktop shortcut created: $DESKTOP_FILE_PATH"
}

# Main installation process
main() {
    print_info "ZmqAnalyzer Installation"
    check_permissions
    install_binary
    create_desktop_shortcut
    print_success "ZmqAnalyzer installed successfully!"
    print_info "You can now run the application with: zmqanalyzer"
}

# Run main function
main "$@"
