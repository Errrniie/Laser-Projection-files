# Pre-Flight Checklist

## Hardware Setup

### Printer/Motion System
- [ ] Printer powered ON
- [ ] Network cable connected or WiFi active
- [ ] Printer accessible at 192.168.8.154
- [ ] Moonraker running (test: `http://192.168.8.154:7125`)
- [ ] All axes can move freely (no obstructions)
- [ ] Homing switches functional

### Laser System
- [ ] ESP32 powered ON
- [ ] ESP32 accessible at 192.168.8.186
- [ ] Test laser control: `curl http://192.168.8.186/high` (should see "HIGH")
- [ ] Test laser disable: `curl http://192.168.8.186/low` (should see "LOW")
- [ ] Laser module connected to ESP32 pin 25
- [ ] Laser pointing at safe target area (ground, not walls/windows)

### Camera
- [ ] Camera connected via USB
- [ ] Camera permissions: `ls -l /dev/video*` (should be readable)
- [ ] Test capture: `v4l2-ctl --list-devices`
- [ ] Clear field of view (no obstructions)
- [ ] Adequate lighting (outdoor daylight or bright indoor)

### Software
- [ ] Python 3.8+ installed
- [ ] Required packages installed:
  - [ ] ultralytics (YOLO)
  - [ ] opencv-python
  - [ ] websocket-client
  - [ ] numpy
  - [ ] requests
- [ ] CUDA available (check: `python -c "import torch; print(torch.cuda.is_available())"`)
- [ ] YOLOv8n model downloaded (yolov8n.pt in project root)

## Calibration Preparation

### Tools Needed
- [ ] Measuring tape (25-50 feet)
- [ ] Target object (stuffed animal, cardboard cutout, etc.)
- [ ] Helper to position target at marked distances (optional but recommended)

### Measurement Plan
Mark these distances from camera position:
- [ ] 5 feet
- [ ] 10 feet
- [ ] 15 feet
- [ ] 20 feet
- [ ] 25 feet
- [ ] 30 feet

**Tip:** Use chalk, tape, or markers on ground

## Safety Setup

### Laser Safety
- [ ] Laser pointing at GROUND (not at eye level)
- [ ] No reflective surfaces in laser path
- [ ] Clear area around target zone (no people/pets)
- [ ] Emergency stop accessible (keyboard with 'Q' key ready)

### Physical Safety
- [ ] Printer secured (won't tip or slide)
- [ ] Cables secured (no trip hazards)
- [ ] Adequate ventilation
- [ ] Clear egress paths

## Pre-Launch Verification

### Network Tests
```bash
# Printer reachable
ping -c 3 192.168.8.154

# Moonraker API responding
curl http://192.168.8.154:7125/printer/info

# ESP32 reachable
ping -c 3 192.168.8.186

# Laser control responding
curl http://192.168.8.186/status
```

### Camera Test
```bash
# List video devices
v4l2-ctl --list-devices

# Test capture (will show one frame)
python -c "import cv2; cap = cv2.VideoCapture(0); ret, frame = cap.read(); print('OK' if ret else 'FAIL'); cap.release()"
```

### File Permissions
```bash
cd /home/LxSparda/Desktop/GooseProject

# Check files exist
ls -l SystemMain.py
ls -l YoloModel/Detection.py
ls -l Laser/GroundAim.py

# Verify executability
test -x SystemMain.py && echo "Executable" || echo "Run: chmod +x SystemMain.py"
```

## Launch Sequence

### Step 1: Start System
```bash
cd /home/LxSparda/Desktop/GooseProject
python SystemMain.py
```

**Expected output:**
```
======================================================================
GOOSE DETERRENCE SYSTEM - STARTING
======================================================================

[INIT] Connecting to Moonraker...
[INIT] Moonraker connected
[INIT] Initializing motion controller...
[INIT] Motion controller ready
[INIT] Homing printer (this will take ~30 seconds)...
```

**Wait:** Homing takes ~30 seconds (don't interrupt)

### Step 2: Calibration

**Window opens:** "CALIBRATE DISTANCE - Click Target Feet"

**Process:**
1. Place target at first distance (e.g., 5ft)
2. Click on target's feet (bottom/ground contact point)
3. Enter distance when prompted: `5`
4. Move target to next distance (e.g., 10ft)
5. Repeat clicks for all distances
6. After 6+ points, press 'S' to save

**If mistake:** Press 'U' to undo last point

**To abort:** Press 'Q' (system will exit cleanly)

### Step 3: Operation

**System enters operational mode**

**Display window shows:**
- Live camera feed
- Mode indicator (SEARCH/TRACK)
- Bounding boxes (GREEN=bird, RED=person)
- Distance estimates
- Laser/pattern status

**Test sequence:**
1. Show bird/target to camera
2. Wait for GREEN box → mode switches to TRACK
3. Laser should turn ON
4. Square pattern should start
5. Show person to camera
6. Laser should turn OFF immediately
7. Mode should return to SEARCH

### Step 4: Shutdown

**Normal shutdown:** Press 'Q'

**Expected output:**
```
[CLEANUP] Shutting down system...
[CLEANUP] Stopping deterrence pattern...
[CLEANUP] Turning off laser...
[CLEANUP] Stopping camera...
[CLEANUP] Disconnecting from Moonraker...
[CLEANUP] Shutdown complete
```

**Emergency shutdown:** Ctrl+C (same cleanup will run)

## Post-Operation Checklist

- [ ] Laser is OFF (verify manually if needed)
- [ ] Printer is idle (check web interface)
- [ ] No error messages in terminal
- [ ] Camera released (can test with other apps)
- [ ] Calibration saved (check for JSON file)

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "Cannot connect to Moonraker" | Printer offline | Check power, network, IP address |
| "Cannot open camera" | Camera in use | Close other apps, check permissions |
| "Calibration aborted" | User pressed Q | Restart system, redo calibration |
| Laser stays ON after exit | Cleanup failed | Run: `curl http://192.168.8.186/low` |
| No detections | Low confidence | Lower CONF_THRESH in SystemMain.py |
| False positives | High sensitivity | Raise CONF_THRESH in SystemMain.py |
| Distance wrong | Bad calibration | Redo calibration with more points |
| Laser misaligned | Neutral position off | Check Calibration.py constants |
| Pattern jitters | Absolute mode issue | Verify G90 commands in logs |

## Support Resources

- **Operation Guide:** README_SYSTEM.md
- **Integration Details:** INTEGRATION_SUMMARY.md
- **Laser Physics:** Laser/GroundAim.py (comments)
- **Calibration Constants:** Laser/Calibration.py
- **Klipper Macros:** Config/square_pattern.cfg

## Emergency Procedures

### If Laser Won't Turn Off
```bash
# Direct ESP32 command
curl http://192.168.8.186/low

# If that fails, power cycle ESP32
```

### If Printer Won't Stop
```bash
# Emergency stop via Moonraker
curl -X POST http://192.168.8.154:7125/printer/emergency_stop

# Or use physical emergency stop button
```

### If System Hangs
```bash
# Terminal 1: Ctrl+C (triggers cleanup)
# If frozen: Ctrl+Z then `kill %1`
# Last resort: `pkill -9 python`
```

## Ready to Launch? ✓

Ensure ALL hardware checklist items are complete before running SystemMain.py.

**The system will:**
1. Home the printer (loud noises are normal)
2. Open calibration window (requires user interaction)
3. Enter operational mode (autonomous from here)

**Safety reminders:**
- Never look directly at laser
- Keep people/pets out of target zone during testing
- Emergency stop ready at all times
- Monitor system during entire operation

Good luck! 🦆➡️⚡
