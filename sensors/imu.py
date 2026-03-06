import time
import board
import adafruit_lsm303dlh_mag
import adafruit_lsm303_accel
import adafruit_l3gd20

i2c = board.I2C()

class IMU():
    def __init__(self):
        # 1. Initialize Magnetometer (0x1e)
        try:
            self.sensor_mag = adafruit_lsm303dlh_mag.LSM303DLH_Mag(i2c)
            print("Magnetometer (0x1e) initialized.")
        except Exception as e:
            print(f"Mag Error: {e}")

        # 2. Initialize Accelerometer (0x19)
        try:
            self.sensor_accel = adafruit_lsm303_accel.LSM303_Accel(i2c)
            print("Accelerometer (0x19) initialized.")
        except Exception as e:
            print(f"Accel Error: {e}")

        # 3. Initialize Gyroscope (0x69) - PATCHED FOR ID 0xd3
        try:
            # We "monkey patch" the library to accept your L3G4200D chip ID
            adafruit_l3gd20._L3GD20_CHIP_ID = 0xd3 
            
            self.sensor_gyro = adafruit_l3gd20.L3GD20_I2C(i2c, address=0x69)
            print("Gyroscope (0x69) initialized (L3G4200D detected).")
        except Exception as e:
            print(f"Gyro Error: {e}")
            
        print("Calibrating accelerometer bias...")
        self.accel_bias = self.get_accel()
        
        print(f"Calibration gyroscope bias...")
        self.gyro_bias = self.get_gyro()
        
        print(f"calibrating magnetometer bias...")
        self.mag_bias = self.get_mag()

        
    def get_accel(self):
        acc_x, acc_y, acc_z = self.sensor_accel.acceleration
        corrected_acc_x = acc_x - self.accel_bias[0]
        corrected_acc_y = acc_y - self.accel_bias[1]
        corrected_acc_z = acc_z - self.accel_bias[2]
        return corrected_acc_x, corrected_acc_y, corrected_acc_z
    
    def get_mag(self):
        mag_x, mag_y, mag_z = self.sensor_mag.magnetic
        corrected_mag_x = mag_x - self.mag_bias[0]
        corrected_mag_y = mag_y - self.mag_bias[1]
        corrected_mag_z = mag_z - self.mag_bias[2]
        return corrected_mag_x, corrected_mag_y, corrected_mag_z

    def get_gyro(self):
        gyro_x, gyro_y, gyro_z = self.sensor_gyro.gyro
        corrected_gyro_x = gyro_x - self.gyro_bias[0]
        corrected_gyro_y = gyro_y - self.gyro_bias[1]
        corrected_gyro_z = gyro_z - self.gyro_bias[2]
        return corrected_gyro_x, corrected_gyro_y, corrected_gyro_z