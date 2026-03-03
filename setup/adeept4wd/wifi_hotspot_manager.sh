#!/bin/bash

# Configuration parameters - modify these values according to your needs
HOTSPOT_SSID="Adeept_Robot"
HOTSPOT_PASSWORD="12345678"  # At least 8 characters
HOTSPOT_INTERFACE="wlan0"
WIFI_AP_GATEWAY="192.168.6.1"

# Wait for network service to be ready
echo "Waiting for network service to start..."
while ! nmcli general status > /dev/null 2>&1; do
    sleep 1
done

# Find first available saved WiFi connection (excluding hotspot)
get_available_wifi_connection() {
    nmcli connection show | grep -v "$HOTSPOT_SSID" | grep "wifi" | awk '{print $1}' | head -n 1
}

# Check if currently connected to a WiFi network
check_wifi_connection() {
    nmcli connection show --active | grep -q "wifi"
    return $?
}

# Connect to an available saved WiFi connection
connect_wifi() {
    local conn_name=$(get_available_wifi_connection)
    
    if [ -z "$conn_name" ]; then
        echo "No saved WiFi connections found"
        return 1
    fi
    
    echo "Attempting to connect to WiFi: $conn_name"
    
    # Attempt connection
    nmcli connection up "$conn_name" ifname "$HOTSPOT_INTERFACE"
    
    # Wait for connection to complete
    sleep 10
    
    # Check if connection was successful
    if check_wifi_connection; then
        echo "WiFi connected successfully"
        return 0
    else
        echo "Failed to connect to WiFi"
        return 1
    fi
}

# Start hotspot
start_hotspot() {
    echo "Starting hotspot: $HOTSPOT_SSID"
    
    # First shut down any existing hotspot connection
    if nmcli connection show | grep -q "$HOTSPOT_SSID"; then
        nmcli connection down "$HOTSPOT_SSID"
    fi
    
    # Create or modify hotspot configuration
    if ! nmcli connection show | grep -q "$HOTSPOT_SSID"; then
        nmcli connection add type wifi con-name "$HOTSPOT_SSID" ifname "$HOTSPOT_INTERFACE" ssid "$HOTSPOT_SSID"
    fi
    
    # Configure hotspot parameters
    nmcli connection modify "$HOTSPOT_SSID" connection.autoconnect no 
    nmcli connection modify "$HOTSPOT_SSID" wifi.mode ap
    nmcli connection modify "$HOTSPOT_SSID" wifi-sec.key-mgmt wpa-psk
    nmcli connection modify "$HOTSPOT_SSID" wifi-sec.psk "$HOTSPOT_PASSWORD"
    nmcli connection modify "$HOTSPOT_SSID" ipv4.addresses "$WIFI_AP_GATEWAY/24"
    nmcli connection modify "$HOTSPOT_SSID" ipv4.method shared
    nmcli connection modify "$HOTSPOT_SSID" ipv6.method ignore
    
    # Start the hotspot
    nmcli connection up "$HOTSPOT_SSID" ifname "$HOTSPOT_INTERFACE"
    
    echo "Hotspot started successfully"
}

# Main logic
main() {
    # First disconnect all possible connections
    nmcli connection down id "$SYSTEM_WIFI_CONN" > /dev/null 2>&1
    nmcli connection down id "$HOTSPOT_SSID" > /dev/null 2>&1
    
    # Attempt to connect to system preconfigured WiFi
    if connect_wifi; then
        exit 0
    fi
    
    # If WiFi connection fails, start hotspot
    start_hotspot
}

# Execute main logic
main
