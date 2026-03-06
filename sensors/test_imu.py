import time
import board
import adafruit_lsm303dlh_mag
import adafruit_lsm303_accel
import adafruit_l3gd20

# Initialize I2C bus
i2c = board.I2C()

# 1. Initialize Magnetometer (0x1e)
try:
    sensor_mag = adafruit_lsm303dlh_mag.LSM303DLH_Mag(i2c)
    print("Magnetometer (0x1e) initialized.")
except Exception as e:
    print(f"Mag Error: {e}")

# 2. Initialize Accelerometer (0x19)
try:
    sensor_accel = adafruit_lsm303_accel.LSM303_Accel(i2c)
    print("Accelerometer (0x19) initialized.")
except Exception as e:
    print(f"Accel Error: {e}")

# 3. Initialize Gyroscope (0x69) - PATCHED FOR ID 0xd3
try:
    # We "monkey patch" the library to accept your L3G4200D chip ID
    adafruit_l3gd20._L3GD20_CHIP_ID = 0xd3 
    
    sensor_gyro = adafruit_l3gd20.L3GD20_I2C(i2c, address=0x69)
    print("Gyroscope (0x69) initialized (L3G4200D detected).")
except Exception as e:
    print(f"Gyro Error: {e}")

print("-" * 30)

while True:
    try:
        acc_x, acc_y, acc_z = sensor_accel.acceleration
        mag_x, mag_y, mag_z = sensor_mag.magnetic
        gyro_x, gyro_y, gyro_z = sensor_gyro.gyro

        print(f"Accel (m/s^2): {acc_x:6.2f}, {acc_y:6.2f}, {acc_z:6.2f}")
        print(f"Mag (microT):  {mag_x:6.2f}, {mag_y:6.2f}, {mag_z:6.2f}")
        print(f"Gyro (rad/s):  {gyro_x:6.2f}, {gyro_y:6.2f}, {gyro_z:6.2f}")
    except Exception as e:
        print(f"Read Error: {e}")
        
    print("-" * 40)
    time.sleep(0.5)
