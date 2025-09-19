import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from driver.picarx import Picarx
from time import time

px = Picarx()
def main():
    px.left_motor_base_power=100
    px.right_motor_base_power=100

    start_time = time()

    px.update_motor()

    input("Press Enter to stop...")

    px.stop()
    end_time = time()
    duration = end_time - start_time
    print(f"Duration: {duration:.2f} seconds")

if __name__ == "__main__":
    try:
       main()
    finally:
        px.stop()
        print("stop and exit")
