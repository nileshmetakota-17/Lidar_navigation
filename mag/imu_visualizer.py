import re
import time
import math
import serial
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


# ============================================================
# CONFIGURATION
# ============================================================

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 230400

# Complementary filter
ALPHA = 0.98


# ============================================================
# SERIAL
# ============================================================

ser = serial.Serial(
    SERIAL_PORT,
    BAUD_RATE,
    timeout=0.01
)

time.sleep(2)

# Remove old buffered data
ser.reset_input_buffer()


# ============================================================
# ORIENTATION STATE
# ============================================================

roll = 0.0
pitch = 0.0
yaw = 0.0

last_time = time.time()

initialized = False


# ============================================================
# REGEX FOR YOUR EXISTING ARDUINO OUTPUT
# ============================================================

pattern = re.compile(
    r"ACC\[m/s2\]\s+"
    r"X:([-+]?\d*\.?\d+)\s+"
    r"Y:([-+]?\d*\.?\d+)\s+"
    r"Z:([-+]?\d*\.?\d+)"
    r".*?"
    r"GYRO\[rad/s\]\s+"
    r"X:([-+]?\d*\.?\d+)\s+"
    r"Y:([-+]?\d*\.?\d+)\s+"
    r"Z:([-+]?\d*\.?\d+)"
)


# ============================================================
# ROTATION MATRIX
#
# Rotation order:
# R = Rz(yaw) * Ry(pitch) * Rx(roll)
# ============================================================

def rotation_matrix(roll, pitch, yaw):

    cr = math.cos(roll)
    sr = math.sin(roll)

    cp = math.cos(pitch)
    sp = math.sin(pitch)

    cy = math.cos(yaw)
    sy = math.sin(yaw)

    Rx = np.array([
        [1, 0, 0],
        [0, cr, -sr],
        [0, sr, cr]
    ])

    Ry = np.array([
        [cp, 0, sp],
        [0, 1, 0],
        [-sp, 0, cp]
    ])

    Rz = np.array([
        [cy, -sy, 0],
        [sy, cy, 0],
        [0, 0, 1]
    ])

    return Rz @ Ry @ Rx


# ============================================================
# MATPLOTLIB WINDOW
# ============================================================

fig = plt.figure(
    figsize=(8, 8)
)

ax = fig.add_subplot(
    111,
    projection="3d"
)


# ============================================================
# UPDATE
# ============================================================

def update(frame):

    global roll
    global pitch
    global yaw
    global last_time
    global initialized

    # --------------------------------------------------------
    # READ NEW SERIAL DATA
    # --------------------------------------------------------

    latest_values = None

    while ser.in_waiting:

        try:

            line = ser.readline().decode(
                "utf-8",
                errors="ignore"
            )

        except Exception:
            continue

        match = pattern.search(line)

        if match:

            latest_values = [
                float(match.group(i))
                for i in range(1, 7)
            ]

    if latest_values is None:
        return

    ax_m, ay_m, az_m, gx, gy, gz = latest_values


    # --------------------------------------------------------
    # TIME STEP
    # --------------------------------------------------------

    now = time.time()

    dt = now - last_time
    last_time = now

    # Prevent bad integration if program pauses
    if dt <= 0 or dt > 0.5:
        dt = 0.1


    # --------------------------------------------------------
    # ACCELEROMETER ORIENTATION
    # --------------------------------------------------------

    roll_acc = math.atan2(
        ay_m,
        az_m
    )

    pitch_acc = math.atan2(
        -ax_m,
        math.sqrt(
            ay_m * ay_m +
            az_m * az_m
        )
    )


    # --------------------------------------------------------
    # INITIAL ORIENTATION
    # --------------------------------------------------------

    if not initialized:

        roll = roll_acc
        pitch = pitch_acc

        yaw = 0.0

        initialized = True


    # --------------------------------------------------------
    # COMPLEMENTARY FILTER
    #
    # Gyro:
    #   good during fast movement
    #
    # Accelerometer:
    #   corrects long-term roll/pitch drift
    # --------------------------------------------------------

    roll_gyro = roll + gx * dt
    pitch_gyro = pitch + gy * dt

    roll = (
        ALPHA * roll_gyro
        +
        (1.0 - ALPHA) * roll_acc
    )

    pitch = (
        ALPHA * pitch_gyro
        +
        (1.0 - ALPHA) * pitch_acc
    )


    # --------------------------------------------------------
    # YAW
    #
    # Currently gyro-only because magnetometer calibration
    # is not yet trustworthy.
    #
    # Therefore yaw WILL slowly drift.
    # --------------------------------------------------------

    yaw += gz * dt


    # --------------------------------------------------------
    # CREATE ROTATION MATRIX
    # --------------------------------------------------------

    R = rotation_matrix(
        roll,
        pitch,
        yaw
    )


    # Sensor/body axes
    x_axis = R @ np.array([1.0, 0.0, 0.0])
    y_axis = R @ np.array([0.0, 1.0, 0.0])
    z_axis = R @ np.array([0.0, 0.0, 1.0])


    # --------------------------------------------------------
    # DRAW
    # --------------------------------------------------------

    ax.clear()

    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_zlim(-1.2, 1.2)

    ax.set_xlabel("World X")
    ax.set_ylabel("World Y")
    ax.set_zlabel("World Z")

    ax.set_title(
        "Live IMU Orientation\n"
        f"Roll: {math.degrees(roll):6.1f}°   "
        f"Pitch: {math.degrees(pitch):6.1f}°   "
        f"Yaw: {math.degrees(yaw):6.1f}°"
    )


    # --------------------------------------------------------
    # SENSOR X AXIS
    # --------------------------------------------------------

    ax.quiver(
        0, 0, 0,
        x_axis[0],
        x_axis[1],
        x_axis[2],
        color="red",
        linewidth=4
    )

    ax.text(
        x_axis[0],
        x_axis[1],
        x_axis[2],
        "  X",
        color="red",
        fontsize=14
    )


    # --------------------------------------------------------
    # SENSOR Y AXIS
    # --------------------------------------------------------

    ax.quiver(
        0, 0, 0,
        y_axis[0],
        y_axis[1],
        y_axis[2],
        color="green",
        linewidth=4
    )

    ax.text(
        y_axis[0],
        y_axis[1],
        y_axis[2],
        "  Y",
        color="green",
        fontsize=14
    )


    # --------------------------------------------------------
    # SENSOR Z AXIS
    # --------------------------------------------------------

    ax.quiver(
        0, 0, 0,
        z_axis[0],
        z_axis[1],
        z_axis[2],
        color="blue",
        linewidth=4
    )

    ax.text(
        z_axis[0],
        z_axis[1],
        z_axis[2],
        "  Z",
        color="blue",
        fontsize=14
    )


    # --------------------------------------------------------
    # FIX VIEW ASPECT
    # --------------------------------------------------------

    ax.set_box_aspect(
        [1, 1, 1]
    )

    ax.view_init(
        elev=25,
        azim=45
    )


# ============================================================
# RUN
# ============================================================

ani = FuncAnimation(
    fig,
    update,
    interval=50,
    cache_frame_data=False
)

try:

    plt.show()

finally:

    ser.close()
