# SystemMain.py - Integration Summary

## What Was Created

### New Files
1. **SystemMain.py** - Complete system orchestration (729 lines)
   - Single runnable entry point
   - Live camera calibration UI
   - SEARCH/TRACK state machine
   - Safety overrides
   - Clean exception handling

2. **README_SYSTEM.md** - Complete operation guide
   - Quick start instructions
   - Calibration walkthrough
   - Keyboard controls
   - Troubleshooting guide

3. **quick_start.sh** - Launch script with checklist

### Modified Files
1. **YoloModel/Detection.py**
   - Returns 5 values instead of 4: `(has_target, bbox_center, bbox, confidence, class_id)`
   - Distinguishes between person (class 0) and bird (class 14)
   - Required for safety override logic

2. **YoloModel/YoloInterface.py**
   - Updated to handle 5-value return from detect_human()
   - Unpack includes class_id

## Key Features Implemented

### 1. Live Camera Calibration UI
**Location:** `SystemMain.py` lines 133-288

- Opens at startup before operational mode
- Interactive OpenCV window with mouse callbacks
- Click target feet → enter distance → repeat
- Minimum 6 points required
- Undo support (U key)
- Save to JSON via Storage.py
- Immediate load into distance model

**Workflow:**
```
startup → camera opens → show instructions
       → user clicks + enters distances
       → validates monotonicity
       → saves to Storage
       → loads into Model
       → continues to operational mode
```

### 2. Safety Override System
**Location:** `SystemMain.py` lines 524-543, 557-575

**Rules:**
- SEARCH mode: Never confirms person as target
- TRACK mode: Aborts immediately if person detected
- Always: Laser OFF when person present
- Always: Pattern stops when person present

**Implementation:**
```python
if detected_class == "person":
    # In SEARCH: skip, don't confirm
    # In TRACK: immediate abort to SEARCH
    stop_pattern()
    laser_off()
```

### 3. State Machine
**Modes:** SEARCH ↔ TRACK

**SEARCH Mode:**
- Laser OFF
- Pattern OFF
- Scanning for valid targets
- Requires 3 consecutive bird detections to enter TRACK
- Ignores person detections (safety)

**TRACK Mode:**
- Estimates distance from Y-pixel
- Computes ground hit point
- Aims laser (absolute positioning)
- Activates laser
- Starts deterrence pattern
- Exits on:
  - Person detected (safety override)
  - Bird lost for 8 frames
  - Distance out of range (3-30ft)

### 4. Robust Cleanup
**Location:** `SystemMain.py` lines 631-690

**Always executed (try/finally):**
1. Stop deterrence pattern
2. Turn OFF laser
3. Stop camera thread
4. Close display windows
5. Disconnect Moonraker

**Triggered by:**
- Normal 'Q' quit
- Ctrl+C interrupt
- Any unhandled exception
- Calibration abort

### 5. Absolute Positioning Strategy
**Location:** Multiple locations in SystemMain.py

**Why:** Prevents "delta-from-delta" drift bugs

**Implementation:**
```python
# After homing - explicit neutral move
G90  # Absolute mode
G1 X{X_NEUTRAL_MM} Y{Y_NEUTRAL_MM}

# During tracking - absolute target position
target_x = X_NEUTRAL_MM + dx_from_GroundAim
target_y = Y_NEUTRAL_MM + dy_from_GroundAim
G90
G1 X{target_x} Y{target_y}
```

### 6. Distance Estimation Pipeline
**Flow:**
```
Detection → bbox (x1,y1,x2,y2)
         → feet_y = y2 (bottom of bbox)
         → distance_ft = get_distance(feet_y)  # Model interpolation
         → clamp to [3ft, 30ft]
         → convert to meters
         → GroundAim.get_motor_deltas(x_m, z_m)
         → absolute motor positions
         → G-code command
```

### 7. Logging Structure
**Prefixes:**
- `[INIT]` - Startup sequence
- `[CALIBRATION]` - Calibration UI
- `[STATE]` - Mode transitions
- `[TRACK]` - Distance/aiming info
- `[SAFETY]` - Person detection events
- `[CLEANUP]` - Shutdown

**Example output:**
```
[INIT] Connecting to Moonraker...
[INIT] Homing printer...
[CALIBRATION] Added point #1: y=450, dist=10.0ft
[STATE] SEARCH -> TRACK (confirmed 3 frames)
[TRACK] dist=12.3ft, y=385px, X=110.2, Y=73.5, conf=0.87
[SAFETY] PERSON DETECTED - TRACK -> SEARCH (laser OFF)
[CLEANUP] Shutting down system...
```

## Architecture Decisions

### What Was NOT Modified
Per requirements, these verified subsystems were left untouched:
- Laser/GroundAim.py - mirror angle physics
- Laser/Calibration.py - motor constants
- Laser/DeterrencePattern.py - pattern geometry
- Config/square_pattern.cfg - Klipper macros
- Behavior/Search_v2.py - search pattern
- Behavior/TrackingController.py - tracking logic

### What Was Modified (Minimally)
1. **Detection.py** - Added class_id return value
2. **YoloInterface.py** - Updated unpacking for 5-value return

### Integration Points

**Moonraker:**
```python
ws = MoonrakerWSClient(url)
ws.connect()
ws.call("printer.gcode.script", {"script": "G28"})  # blocking
ws.send_gcode("G1 X100 Y50")  # non-blocking
```

**Motion:**
```python
motion = MotionController(ws, config)
# Not used in current implementation
# (direct G-code preferred for galvo precision)
```

**Laser:**
```python
from Laser import LaserEnable
controller = LaserEnable.LaserController()
controller.turn_on()
controller.turn_off()
```

**Pattern:**
```python
from Laser.DeterrencePattern import start_square_pattern, stop_pattern
start_square_pattern(ws, target_dist_in=120, square_size_ft=0.5)
stop_pattern(ws)
```

**Distance Model:**
```python
from Distance.Model import load_model, get_distance
load_model(calibration_points)  # [(y_pixel, distance_ft), ...]
dist_ft = get_distance(y_pixel)  # Interpolates
```

## Testing Procedure

### Phase 1: Startup & Calibration
1. Run `python SystemMain.py`
2. Verify Moonraker connection
3. Wait for homing (~30 sec)
4. Observe calibration window opens
5. Click 6+ points at known distances
6. Press 'S' to save
7. Verify system enters operational mode

### Phase 2: Detection Testing
1. Show bird (or bird-like object) to camera
2. Verify GREEN bounding box appears
3. Wait for 3 frames → mode should switch to TRACK
4. Verify laser turns ON
5. Show person to camera
6. Verify RED bounding box appears
7. Verify laser turns OFF immediately
8. Verify mode returns to SEARCH

### Phase 3: Tracking & Pattern
1. In TRACK mode with bird target
2. Observe laser moves to aim at estimated ground position
3. Verify square pattern starts
4. Move target closer/farther
5. Observe laser repositions
6. Remove target
7. After 8 frames, verify laser OFF and mode → SEARCH

### Phase 4: Shutdown
1. Press 'Q'
2. Verify clean shutdown messages
3. Verify laser is OFF
4. Verify camera stopped
5. Verify Moonraker disconnected

## Known Limitations

1. **Single target tracking** - Picks highest confidence detection
2. **No lateral (X) tracking** - Assumes target is straight ahead (x_m = 0)
3. **Y-only distance model** - Doesn't account for X position in frame
4. **No search motion** - Search mode is passive (camera only)
5. **Fixed pattern size** - Square size is constant (could be distance-adaptive)

## Future Enhancements (Out of Scope)

- [ ] Lateral tracking using bbox X-position
- [ ] Distance-adaptive pattern scaling
- [ ] Multi-target priority queue
- [ ] Search scan motion (pan camera view)
- [ ] BNO055 roll compensation integration
- [ ] Web UI for remote control
- [ ] Detection history/heatmap
- [ ] Calibration point visualization

## Configuration Reference

**Edit these constants in SystemMain.py as needed:**

```python
# Lines 43-47: Connection
MOONRAKER_URL = "ws://192.168.8.154:7125/websocket"
CAMERA_INDEX = 0

# Lines 56-61: Detection thresholds
CONF_THRESH = {
    "bird": 0.25,    # Increase to reduce false positives
    "person": 0.40,  # Decrease to be more cautious
}

# Lines 63-69: Safety and behavior
TRACK_CONFIRM_FRAMES = 3   # Higher = less jittery, slower to engage
LOST_FRAMES_TO_EXIT = 8    # Higher = more persistent tracking
MIN_DISTANCE_FT = 3.0      # Safety: too close
MAX_DISTANCE_FT = 30.0     # Limit: too far (model unreliable)

# Lines 71-74: Pattern
SQUARE_SIZE_FT = 0.5       # Larger = more visible, less precise
PATTERN_SPEED = 12000      # mm/min feedrate
PATTERN_DWELL_MS = 100     # Pause at corners
```

## File Checklist

**New:**
- ✅ SystemMain.py
- ✅ README_SYSTEM.md
- ✅ quick_start.sh

**Modified:**
- ✅ YoloModel/Detection.py (returns class_id)
- ✅ YoloModel/YoloInterface.py (unpacks class_id)

**Unchanged (verified subsystems):**
- ✅ Laser/GroundAim.py
- ✅ Laser/Calibration.py
- ✅ Laser/DeterrencePattern.py
- ✅ Laser/LaserEnable.py
- ✅ Config/square_pattern.cfg
- ✅ Behavior/Search_v2.py
- ✅ Behavior/TrackingController.py
- ✅ Motion/Moonraker_ws_v2.py
- ✅ Motion/MotionController.py
- ✅ Motion/Home.py
- ✅ Distance/Model.py
- ✅ Distance/Storage.py

## Success Criteria

✅ Single runnable entry point (SystemMain.py)
✅ Moonraker connection and homing
✅ Live camera calibration UI at startup
✅ Calibration persistence (Storage.py integration)
✅ Distance model loading
✅ SEARCH/TRACK state machine
✅ Simultaneous bird + human detection
✅ Safety override (person → laser OFF)
✅ Laser aiming via GroundAim
✅ Deterrence pattern start/stop
✅ Keyboard controls (Q/P/R)
✅ Clean shutdown on exceptions
✅ Absolute positioning (no drift)
✅ Structured logging
✅ Comprehensive documentation

## System Ready for Testing ✓
