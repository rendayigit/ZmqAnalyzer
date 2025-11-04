#!/bin/bash

# ZmqAnalyzer Uninstallation Script
# This script removes ZmqAnalyzer from standard Linux directories

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation path
ZMQ_ANALYZER_BINARY="/usr/local/bin/zmqanalyzer"

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

# Function to check if running with sudo for system uninstallation
check_permissions() {
    if [[ -z "$SUDO_USER" ]]; then
        print_error "SUDO_USER not set. Please run this script with sudo."
        return 1
    fi
}

# Function to remove binary
remove_binary() {
    if [[ -f "$ZMQ_ANALYZER_BINARY" ]]; then
        print_info "Removing binary: $ZMQ_ANALYZER_BINARY"
        if rm "$ZMQ_ANALYZER_BINARY"; then
            print_success "Binary removed successfully"
        else
            print_error "Failed to remove binary"
            exit 1
        fi
    else
        print_warning "Binary not found: $ZMQ_ANALYZER_BINARY"
    fi
}

# Function to remove desktop shortcut
remove_desktop_shortcut() {
    DESKTOP_FILE="/home/$SUDO_USER/.local/share/applications/zmqanalyzer.desktop"
    ICON_FILE="/home/$SUDO_USER/.local/share/icons/zmqanalyzer.png"
    DESKTOP_SHORTCUT="/home/$SUDO_USER/Desktop/zmqanalyzer.desktop"

    # Remove desktop file if it exists
    if [[ -f "$DESKTOP_FILE" ]]; then
        print_info "Removing desktop shortcut: $DESKTOP_FILE"
        if rm "$DESKTOP_FILE"; then
            print_success "Desktop shortcut removed successfully"
        else
            print_error "Failed to remove desktop shortcut"
            exit 1
        fi
    else
        print_warning "Desktop shortcut not found: $DESKTOP_FILE"
    fi

    # Remove icon file if it exists
    if [[ -f "$ICON_FILE" ]]; then
        print_info "Removing icon: $ICON_FILE"
        if rm "$ICON_FILE"; then
            print_success "Icon removed successfully"
        else
            print_error "Failed to remove icon"
            exit 1
        fi
    else
        print_warning "Icon not found: $ICON_FILE"
    fi

    # Remove desktop shortcut from Desktop if it exists
    if [[ -f "$DESKTOP_SHORTCUT" ]]; then
        print_info "Removing desktop shortcut from Desktop: $DESKTOP_SHORTCUT"
        if rm "$DESKTOP_SHORTCUT"; then
            print_success "Desktop shortcut on Desktop removed successfully"
        else
            print_error "Failed to remove desktop shortcut from Desktop"
            exit 1
        fi
    else
        print_warning "Desktop shortcut on Desktop not found: $DESKTOP_SHORTCUT"
    fi
}

# Main uninstallation process
main() {
    print_info "ZmqAnalyzer Uninstallation"

    check_permissions
    remove_binary
    remove_desktop_shortcut

    print_success "ZmqAnalyzer uninstalled successfully!"
}

# Run main function
main "$@"
