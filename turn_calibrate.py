from driver.picarx import Picarx

px = Picarx()

from time import time, sleep

px.set_dir_servo_angle(30)
px.left_motor_differential_power = -50
px.right_motor_differential_power = 50

start_time = time()
px.update_motor()

#listen for ctrl-c to stop

try:
    while True:
        current_angle = px.dir_current_angle
        elapsed_time = time() - start_time
        sleep(0.1)  # Adjust the sleep time as needed
except KeyboardInterrupt:
    print("Stopped")
finally:
    end_time = time()
    px.left_motor_differential_power = 0
    px.right_motor_differential_power = 0
    px.update_motor()
    px.set_dir_servo_angle(0)
    print(f"Total time: {end_time - start_time:.2f} seconds")
    
##About 3 seconds for 360 degrees at 100% power
##