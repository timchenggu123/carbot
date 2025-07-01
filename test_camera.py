#!/usr/bin/env python3
import cv2
import sys

def test_camera(device_id):
    """Test a specific camera device"""
    print(f"\n=== Testing /dev/video{device_id} ===")
    
    cap = cv2.VideoCapture(device_id)
    
    if not cap.isOpened():
        print(f"❌ Could not open /dev/video{device_id}")
        return False
    
    print(f"✅ Opened /dev/video{device_id}")
    
    # Get camera properties
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"   Resolution: {int(width)}x{int(height)}")
    print(f"   FPS: {fps}")
    
    # Try to read a frame
    ret, frame = cap.read()
    
    if ret:
        print(f"✅ Successfully captured frame: {frame.shape}")
        print(f"   Frame type: {frame.dtype}")
        success = True
    else:
        print("❌ Failed to capture frame")
        success = False
    
    cap.release()
    return success

def main():
    print("Testing Raspberry Pi Camera devices...")
    
    working_devices = []
    
    # Test the main camera devices (0-7 from rp1-cfe)
    for device_id in range(8):
        if test_camera(device_id):
            working_devices.append(device_id)
    
    print(f"\n=== SUMMARY ===")
    if working_devices:
        print(f"✅ Working camera devices: {working_devices}")
        print(f"💡 Use cv2.VideoCapture({working_devices[0]}) in your script")
    else:
        print("❌ No working camera devices found")
        print("💡 Try enabling the camera with: sudo raspi-config")

if __name__ == "__main__":
    main()
