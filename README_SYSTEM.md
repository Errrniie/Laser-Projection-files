# Goose Deterrence System - Operation Guide

## Quick Start

```bash
cd /home/LxSparda/Desktop/GooseProject
python SystemMain.py
```

## System Flow

### 1. Initialization (Automatic)
- Connects to Moonraker printer controller
- Homes all axes (~30 seconds)
- Moves to neutral laser position
- Initializes laser controller (OFF state)

### 2. Live Camera Calibration (Interactive)
**This is your first interaction with the system.**

A window will open showing the live camera feed with instructions:

#### Calibration Steps:
1. **Click the target's FEET** (bottom of object, where it touches ground)
2. **Enter the known distance** in feet when prompted in terminal
3. **Repeat for multiple distances** - you need at least 6 points
   - Recommended: 5ft, 10ft, 15ft, 20ft, 25ft, 30ft
4. **Press 'U'** to undo last point if you made a mistake
5. **Press 'S'** to save and continue (requires 6+ points)
6. **Press 'Q'** to abort startup

**Tips:**
- Spread calibration points across the full distance range
- Use a measuring tape or known landmarks
- Click consistently (always bottom-center of object)
- More points = better accuracy

### 3. Operational Mode (Automatic)

Once calibration is complete, the system enters operational mode.

#### SEARCH Mode (Default)
- Laser is OFF
- System scans for valid targets
- Detects both **birds** and **humans**
- **SAFETY:** Will never track humans - laser stays OFF

When a **bird** is detected for 3 consecutive frames → switches to TRACK mode

#### TRACK Mode (Active Deterrence)
- Estimates bird distance from camera calibration
- Aims laser at ground position using GroundAim physics
- **Activates laser** (Class 1 eye-safe)
- **Starts square deterrence pattern** around bird
- Continuously tracks bird movement

**SAFETY OVERRIDE:**
- If a **person** is detected at ANY time during tracking:
  - Laser turns OFF immediately
  - Pattern stops
  - Returns to SEARCH mode

**Lost Target:**
- If bird is lost for 8 frames:
  - Laser turns OFF
  - Pattern stops
  - Returns to SEARCH mode

## Keyboard Controls (During Operation)

| Key | Action |
|-----|--------|
| **Q** | Quit - clean shutdown (laser OFF, stop pattern) |
| **P** | Pause - stop laser and pattern but keep camera running |
| **R** | Resume - return to SEARCH mode |

## Display Window

The live display shows:
- **Mode indicator** (SEARCH/TRACK) in top-left
- **Bounding boxes:**
  - GREEN = bird (safe to track)
  - RED = person (will not track, laser OFF)
- **Distance estimate** (feet) when tracking
- **Laser/Pattern status** indicators

## Configuration Constants

Edit these in [SystemMain.py](SystemMain.py) if needed:

```python
# Moonraker
MOONRAKER_URL = "ws://192.168.8.154:7125/websocket"

# Camera
CAMERA_INDEX = 0
CAMERA_WIDTH = 1080
CAMERA_HEIGHT = 720

# Detection thresholds
CONF_THRESH = {
    "bird": 0.25,    # Lower = more sensitive
    "person": 0.40,  # Higher = fewer false alarms
}

# Distance safety limits
MIN_DISTANCE_FT = 3.0
MAX_DISTANCE_FT = 30.0

# Deterrence pattern
SQUARE_SIZE_FT = 0.5  # Size of square pattern in feet
```

## Architecture

### Main Components (DO NOT MODIFY)
- **Laser Math** - [GroundAim.py](Laser/GroundAim.py) - mirror angle physics
- **Calibration** - [Calibration.py](Laser/Calibration.py) - motor constants
- **Patterns** - [DeterrencePattern.py](Laser/DeterrencePattern.py) - square pattern
- **Klipper Macros** - [square_pattern.cfg](Config/square_pattern.cfg) - motion timing

### Integration Layer (SystemMain.py)
- State machine orchestration
- Safety overrides
- Calibration UI
- Clean exception handling

### Subsystems
- **Motion** - Moonraker WebSocket + MotionController
- **Vision** - YOLOv8 + CameraThread
- **Distance** - Calibration-based Y-pixel → distance model
- **Laser** - ESP32 HTTP control (pin 25)

## Safety Features

1. **Never tracks humans** - detection class filtering
2. **Immediate abort on person detection** - overrides tracking
3. **Distance clamping** - rejects targets outside safe range (3-30ft)
4. **Clean shutdown** - laser OFF on exceptions/Ctrl+C
5. **Explicit OFF state** - laser defaults to OFF on startup

## Troubleshooting

### "Cannot connect to Moonraker"
- Check printer is powered on
- Verify IP address: `MOONRAKER_URL` in SystemMain.py
- Test: `ping 192.168.8.154`

### "Cannot open camera"
- Check camera index: try `CAMERA_INDEX = 0, 1, 2` etc.
- Verify camera permissions: `ls -l /dev/video*`
- Test: `v4l2-ctl --list-devices`

### "Distance estimates are wrong"
- Re-run calibration with more points
- Ensure consistent zoom level (don't change between calibration and operation)
- Click exactly at feet/ground contact point

### "Laser not firing"
- Check ESP32 is powered and connected
- Verify ESP32 IP: `ESP32_IP` in [LaserEnable.py](Laser/LaserEnable.py)
- Test manually: `curl http://192.168.8.186/high`

### "Pattern jitters or drifts"
- Check neutral position: motors should be at X=108.5, Y=71.0 after homing
- Verify rotation_distance calibration in [Calibration.py](Laser/Calibration.py)
- Ensure G90 (absolute mode) is used

## Log Messages

The system logs structured messages:

```
[INIT] - Startup sequence
[CALIBRATION] - Calibration UI actions
[STATE] - Mode transitions (SEARCH ↔ TRACK)
[TRACK] - Distance estimates and motor commands
[SAFETY] - Person detection events
[CLEANUP] - Shutdown sequence
```

## File Structure

```
SystemMain.py          # ← START HERE (run this)
├── Motion/
│   ├── Moonraker_ws_v2.py    # WebSocket client
│   ├── MotionController.py   # Fixed-rate streaming
│   └── Home.py               # Homing sequence
├── Laser/
│   ├── GroundAim.py          # Mirror angle physics
│   ├── Calibration.py        # Motor constants
│   ├── LaserEnable.py        # ESP32 control
│   └── DeterrencePattern.py  # Square pattern
├── YoloModel/
│   ├── Detection.py          # YOLO inference
│   └── CameraThread.py       # Async capture
├── Distance/
│   ├── Model.py              # Y → distance interpolation
│   └── Storage.py            # JSON persistence
└── Behavior/
    ├── Search_v2.py          # Search controller
    └── TrackingController.py # Tracking controller
```

## Development Notes

- **Absolute positioning is mandatory** - prevents drift bugs
- **G90/G91 must be explicit** - never assume mode
- **Neutral position after homing** - ensures deterministic origin
- **Class-based detection** - distinguish bird vs person
- **Staleness checks** - reject old detections
- **Thread-safe state** - atomic updates with locks

## Testing Checklist

- [ ] System starts without errors
- [ ] Homing completes (~30 sec)
- [ ] Calibration UI opens and accepts clicks
- [ ] Can save calibration with 6+ points
- [ ] Camera feed shows in operational window
- [ ] Bird detection shows GREEN bbox
- [ ] Person detection shows RED bbox
- [ ] Laser turns ON when tracking bird
- [ ] Laser turns OFF when person detected
- [ ] Pattern stops when target lost
- [ ] 'Q' key performs clean shutdown
- [ ] Laser is OFF after shutdown

## Support

For issues with:
- **Laser physics/patterns** - These are verified, do not modify
- **Integration/state machine** - Check SystemMain.py logs
- **Calibration** - Ensure 6+ points spread across range
- **Safety overrides** - Verify person detection works (show face to camera)
