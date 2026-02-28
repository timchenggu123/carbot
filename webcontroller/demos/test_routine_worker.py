import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from driver.adeept4wd import Adeept4WD 
from utils.io import AsyncTextFIFO
from time import sleep
from sensors.camera import Camera
import asyncio
import signal

text_fifo = AsyncTextFIFO("test_routine_worker")
car = None

def signal_handler(signum, frame):
    """Handle termination signals gracefully"""
    print(f"Received signal {signum}, stopping car...")
    if car is not None:
        car.stop()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

async def test_camera_pan_tilt(car, text_fifo):
    await text_fifo.write_line("Testing camera pan and tilt...")
    for i in range(0,-95,-5):
        car.set_cam_pan_angle(i)
        await asyncio.sleep(0.02)
    for i in range(-90,95,5):
        car.set_cam_pan_angle(i)
        await asyncio.sleep(0.02)
    for i in range(90,-5,-5):
        car.set_cam_pan_angle(i)
        await asyncio.sleep(0.02)

    for i in range(0,-35,-5):
        car.set_cam_tilt_angle(i)
        await asyncio.sleep(0.02)
    for i in range(-30,35,5):
        car.set_cam_tilt_angle(i)
        await asyncio.sleep(0.02)
    for i in range(30,-5,-5):
        car.set_cam_tilt_angle(i)
        await asyncio.sleep(0.02)

async def test_motor_control(car, text_fifo):
    await text_fifo.write_line("Testing motor control...")
    for turn in ["forward", "backward", "rotate-left", "rotate-right", "left", "right", "forward-left", "forward-right", "backward-left", "backward-right"]:
        await text_fifo.write_line(f"Motor command: {turn}")
        car.move(50, turn)
        car.update_motor()
        await asyncio.sleep(2)
    car.stop()

async def main():
    global car
    await text_fifo.write_line("Test routine worker starting...")
    await text_fifo.write_line("Initializing car...")

    car = None
    car_tests_passed = True
    try:
        car = Adeept4WD()
        await text_fifo.write_line("Car initialized successfully")
    except Exception as e:
        await text_fifo.write_line(f"Error initializing car: {e}")
        car_tests_passed = False
    if car_tests_passed:
        await test_camera_pan_tilt(car, text_fifo)
        await text_fifo.write_line("Camera pan and tilt test completed successfully")
        
        await test_motor_control(car, text_fifo)
        await text_fifo.write_line("Motor control test completed successfully")
        
    #Test camera 
    try:
        cam = Camera()
        await text_fifo.write_line("Camera initialized successfully")
    except Exception as e:
        await text_fifo.write_line(f"Error initializing camera: {e}")
        cam = None

    await text_fifo.write_line("Test routine worker completed")
    if car is not None:
        car.stop()
        
if __name__ == "__main__":
    asyncio.run(main())
    

