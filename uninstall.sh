#!/bin/bash

# ZmqAnalyzer Uninstallation Script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to check if running with sudo
check_permissions() {
    if [[ -z "$SUDO_USER" ]]; then
        print_error "SUDO_USER not set. Please run this script with sudo."
        return 1
    fi
}

uninstall() {
    print_info "Uninstalling ZmqAnalyzer..."

    # Remove wrapper
    WRAPPER="/usr/local/bin/zmqanalyzer"
    if [ -f "$WRAPPER" ]; then
        rm "$WRAPPER"
        print_success "Removed $WRAPPER"
    else
        print_warning "$WRAPPER not found"
    fi

    # Remove desktop shortcut (symlink - use -L to test for symlink or file)
    DESKTOP_SHORTCUT="/home/$SUDO_USER/Desktop/zmqanalyzer.desktop"
    if [ -L "$DESKTOP_SHORTCUT" ] || [ -f "$DESKTOP_SHORTCUT" ]; then
        sudo -u $SUDO_USER rm -f "$DESKTOP_SHORTCUT"
        print_success "Removed $DESKTOP_SHORTCUT"
    else
        print_warning "$DESKTOP_SHORTCUT not found"
    fi

    # Remove desktop file
    DESKTOP_FILE="/home/$SUDO_USER/.local/share/applications/zmqanalyzer.desktop"
    if [ -f "$DESKTOP_FILE" ]; then
        sudo -u $SUDO_USER rm -f "$DESKTOP_FILE"
        print_success "Removed $DESKTOP_FILE"
    else
        print_warning "$DESKTOP_FILE not found"
    fi

    # Remove icon
    ICON="/home/$SUDO_USER/.local/share/icons/zmqanalyzer.png"
    if [ -f "$ICON" ]; then
        sudo -u $SUDO_USER rm -f "$ICON"
        print_success "Removed $ICON"
    else
        print_warning "$ICON not found"
    fi

    print_success "Uninstallation complete."
}

main() {
    check_permissions
    uninstall
}

main "$@"
