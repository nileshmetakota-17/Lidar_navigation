import serial
import re
import sys
import math

# ============================================
# SERIAL
# ============================================

PORT = "/dev/ttyACM0"
BAUD = 230400

if len(sys.argv) > 1:
    PORT = sys.argv[1]

print()
print("============================================")
print(" MAGNETOMETER OFFSET CALIBRATION")
print("============================================")
print()
print("Opening:", PORT)

ser = serial.Serial(
    PORT,
    BAUD,
    timeout=1
)

print("Connected")
print()

print("INSTRUCTIONS:")
print()
print("1. Keep IMU mounted in its normal position.")
print("2. Keep rover electronics powered normally.")
print("3. Rotate sensor/rover slowly through many orientations.")
print("4. Try to expose X, Y and Z to all directions.")
print("5. Continue for around 30-60 seconds.")
print("6. Press Ctrl+C when finished.")
print()

print("Collecting magnetometer data...")
print()


# ============================================
# MAG PATTERN
# ============================================

mag_pattern = re.compile(
    r"MAG\s+X:([-+]?\d*\.?\d+)\s+Y:([-+]?\d*\.?\d+)\s+Z:([-+]?\d*\.?\d+)"
)


# ============================================
# INITIAL MIN/MAX
# ============================================

min_x = float("inf")
max_x = float("-inf")

min_y = float("inf")
max_y = float("-inf")

min_z = float("inf")
max_z = float("-inf")

sample_count = 0


# ============================================
# MAIN LOOP
# ============================================

while True:

    try:

        line = ser.readline().decode(
            "utf-8",
            errors="ignore"
        ).strip()

        if not line:
            continue


        mag_match = mag_pattern.search(line)

        if not mag_match:
            continue


        # ====================================
        # MAG DATA
        # ====================================

        mx = float(mag_match.group(1))
        my = float(mag_match.group(2))
        mz = float(mag_match.group(3))

        sample_count += 1


        # ====================================
        # UPDATE MIN/MAX
        # ====================================

        min_x = min(min_x, mx)
        max_x = max(max_x, mx)

        min_y = min(min_y, my)
        max_y = max(max_y, my)

        min_z = min(min_z, mz)
        max_z = max(max_z, mz)


        # ====================================
        # CURRENT OFFSET ESTIMATE
        # ====================================

        offset_x = (
            max_x + min_x
        ) / 2.0

        offset_y = (
            max_y + min_y
        ) / 2.0

        offset_z = (
            max_z + min_z
        ) / 2.0


        # ====================================
        # DISPLAY
        # ====================================

        if sample_count % 20 == 0:

            print(
                f"Samples:{sample_count:6d} | "
                f"X [{min_x:8.2f}, {max_x:8.2f}] | "
                f"Y [{min_y:8.2f}, {max_y:8.2f}] | "
                f"Z [{min_z:8.2f}, {max_z:8.2f}]"
            )


    except KeyboardInterrupt:

        print()
        print()
        print("============================================")
        print(" CALIBRATION FINISHED")
        print("============================================")
        print()

        ser.close()


        if sample_count == 0:

            print("No magnetometer samples received.")

            break


        # ====================================
        # CALCULATE OFFSETS
        # ====================================

        offset_x = (
            max_x + min_x
        ) / 2.0

        offset_y = (
            max_y + min_y
        ) / 2.0

        offset_z = (
            max_z + min_z
        ) / 2.0


        # ====================================
        # AXIS RANGES
        # ====================================

        range_x = (
            max_x - min_x
        ) / 2.0

        range_y = (
            max_y - min_y
        ) / 2.0

        range_z = (
            max_z - min_z
        ) / 2.0


        print(
            f"Samples collected : {sample_count}"
        )

        print()

        print("RAW MIN/MAX")
        print("--------------------------------------------")

        print(
            f"X min: {min_x:10.2f}   "
            f"X max: {max_x:10.2f}"
        )

        print(
            f"Y min: {min_y:10.2f}   "
            f"Y max: {max_y:10.2f}"
        )

        print(
            f"Z min: {min_z:10.2f}   "
            f"Z max: {max_z:10.2f}"
        )

        print()

        print("HARD-IRON OFFSETS")
        print("--------------------------------------------")

        print(
            f"MAG_OFFSET_X = {offset_x:.2f}"
        )

        print(
            f"MAG_OFFSET_Y = {offset_y:.2f}"
        )

        print(
            f"MAG_OFFSET_Z = {offset_z:.2f}"
        )

        print()

        print("HALF RANGES")
        print("--------------------------------------------")

        print(
            f"X radius = {range_x:.2f}"
        )

        print(
            f"Y radius = {range_y:.2f}"
        )

        print(
            f"Z radius = {range_z:.2f}"
        )

        print()

        print("COPY THESE INTO YOUR MAIN CODE:")
        print("--------------------------------------------")
        print()

        print(
            f"MAG_OFFSET_X = {offset_x:.2f}"
        )

        print(
            f"MAG_OFFSET_Y = {offset_y:.2f}"
        )

        print(
            f"MAG_OFFSET_Z = {offset_z:.2f}"
        )

        print()

        break


    except Exception as e:

        print(
            "Error:",
            e
        )
