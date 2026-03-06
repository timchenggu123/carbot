# Vehicle State Logging Implementation Summary

## Features Implemented

### 1. **Vehicle State Logger Utility** (`utils/vehicle_logger.py`)
   - **CSV Logging**: Logs vehicle state to CSV files with configurable interval
   - **Fields**: timestamp, state, speed, cam_pan, cam_tilt, target_detected
   - **Location**: Saves to home directory (`~/vehicle_state_fly_hunt_YYYYMMDD_HHMMSS.csv`)
   - **Detection Images**: Saves JPG frames when flies are detected to `~/fly_detections_fly_hunt/`
   - **Thread-Safe**: Uses locks for concurrent access
   - **Configurable**: Log interval can be adjusted (0 = log every call, default = 1.0 seconds)

### 2. **Fly Hunt Worker Updates** (`webcontroller/demos/fly_hunt_worker.py`)
   - Integrated `VehicleStateLogger` for automatic state tracking
   - Logs state (PATROL, SCANNING, ATTACKING) with speed and camera angles
   - **Automatic Image Capture**: Saves JPG frames when a fly is detected during scanning
   - Detection images include timestamp and detection count in filename
   - Logs file paths in the text output for reference

### 3. **Web Server API Routes** (`webcontroller/local_server.py`)
   - **GET `/fly_hunt/files`**: Opens file management interface
   - **GET `/fly_hunt/files/list`**: Returns JSON list of all CSV logs and detection images
   - **GET `/fly_hunt/files/download/log/<filename>`**: Download vehicle state CSV file
   - **GET `/fly_hunt/files/download/image/<filename>`**: Download detected fly JPG image
   - File lists are sorted by date (newest first)

### 4. **Web Interface Template** (`webcontroller/templates/fly_hunt_files.html`)
   - **Vehicle State Logs Section**: Lists all CSV files with download links
   - **Detection Images Section**: Lists all detected fly JPG images with preview capability
   - **Image Preview**: Click to view selected detection images inline
   - **File Information**: Shows filename and file size
   - **Auto-Refresh**: Lists update every 5 seconds to show new files
   - **Responsive Design**: Matches existing robot control UI

### 5. **Updated Fly Hunt Template** (`webcontroller/templates/fly_hunt.html`)
   - Added "View Logs & Files" button for quick access to file management page

## Configuration

### Log Interval
The CSV logging interval is controlled by the constant in `fly_hunt_worker.py`:
```python
STATE_LOG_INTERVAL = 1.0  # Seconds between CSV log entries (0 = log every frame)
```

To change the interval, modify this value before starting the fly hunt worker.

## File Organization

```
~/vehicle_state_fly_hunt_YYYYMMDD_HHMMSS.csv   # Vehicle state logs
~/fly_detections_fly_hunt/                      # Detected fly images directory
  └── detection_1_YYYYMMDD_HHMMSS_mmm.jpg
  └── detection_2_YYYYMMDD_HHMMSS_mmm.jpg
  └── ... (more detected flies)
```

## CSV File Format

The CSV files contain:
- **timestamp**: ISO 8601 format (YYYY-MM-DDTHH:MM:SS.ssssss)
- **state**: Vehicle state (PATROL, SCANNING, ATTACKING)
- **speed**: Current vehicle speed (0 during scanning)
- **cam_pan**: Camera pan angle in degrees
- **cam_tilt**: Camera tilt angle in degrees
- **target_detected**: 1 if target detected, 0 otherwise

Example:
```
timestamp,state,speed,cam_pan,cam_tilt,target_detected
2024-01-15T10:30:45.123456,PATROL,35,0,0,0
2024-01-15T10:30:46.123456,PATROL,35,0,0,0
2024-01-15T10:30:47.123456,SCANNING,0,-35,0,0
2024-01-15T10:30:48.123456,SCANNING,0,-32,0,0
2024-01-15T10:30:49.123456,SCANNING,0,-25,0,1
```

## Usage

1. Start the fly hunt worker from the web interface
2. The worker automatically logs state to CSV and saves images when flies are detected
3. Click "📁 View Logs & Files" button to view and download logs and detection images
4. CSV files can be imported into Excel, Python (pandas), or other analysis tools
5. Detection images can be reviewed to verify fly detection accuracy

## Security Notes

- Downloaded files are restricted to home directory and specific subdirectories
- CSV downloads only allow `vehicle_state_*` files
- Image downloads only allow `.jpg` files from the fly_detections directory
- All file paths are validated to prevent directory traversal attacks
