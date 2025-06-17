import serial
import time

ser = serial.Serial("/dev/serial0", 115200, timeout=0.01)

def read_tfluna():
    while True:
        # Look for start of frame (0x59 0x59)
        ser.reset_input_buffer()
        if ser.read(1) == b'\x59':
            if ser.read(1) == b'\x59':
                raw = ser.read(7)
                if len(raw) != 7:
                    continue
                distance = raw[0] + (raw[1] << 8)
                strength = raw[2] + (raw[3] << 8)
                temp = (raw[4] + (raw[5] << 8)) / 8 - 256
                print(f"{time.time():.3f} → Distance: {distance} cm, Strength: {strength}, Temp: {temp:.1f}°C")
        time.sleep(0.05)

if __name__ == "__main__":
    try:
        read_tfluna()
    except KeyboardInterrupt:
        ser.close()
