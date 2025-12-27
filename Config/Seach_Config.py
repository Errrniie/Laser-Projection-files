# Angular search bounds (degrees)
# Z axis: 8mm/360deg = 0.022222 mm/deg
# Z=0mm -> 0deg, Z=10mm -> 450deg, Z=20mm -> 900deg
min_angle = 0.0
max_angle = 900.0  # 20mm Z limit
start_angle = 450.0  # 10mm Z (matches neutral)

# Angular velocity (degrees per second)
angular_velocity = 3.0  # target tracking speed
max_angular_velocity = 4.5  # hard cap