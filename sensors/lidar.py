import serial
import time

ser = serial.Serial("/dev/serial0", 115200, timeout=0.01)

def read():
    """
    Single read from the serial port.
    Returns a tuple of (distance, strength, temperature).
    """
    ser.reset_input_buffer()
    for i in range(10):
        if ser.read(1) == b'\x59':
            if ser.read(1) == b'\x59':
                raw = ser.read(7)
                if len(raw) != 7:
                    return None
                distance = raw[0] + (raw[1] << 8)
                strength = raw[2] + (raw[3] << 8)
                temp = (raw[4] + (raw[5] << 8)) / 8 - 256
                return distance, strength, temp
    return None

