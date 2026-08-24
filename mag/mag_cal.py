import serial
import re
import math
import sys

# ============================================
# SERIAL PORT
# ============================================

PORT = "/dev/ttyACM0"
BAUD = 230400

if len(sys.argv) > 1:
    PORT = sys.argv[1]

print("Opening:", PORT)

ser = serial.Serial(PORT, BAUD, timeout=1)

print("Connected")
print()


# ============================================
# REGULAR EXPRESSIONS
# ============================================

acc_pattern = re.compile(
    r"ACC\[m/s2\]\s+X:([-+]?\d*\.?\d+)\s+Y:([-+]?\d*\.?\d+)\s+Z:([-+]?\d*\.?\d+)"
)

gyro_pattern = re.compile(
    r"GYRO\[rad/s\]\s+X:([-+]?\d*\.?\d+)\s+Y:([-+]?\d*\.?\d+)\s+Z:([-+]?\d*\.?\d+)"
)

mag_pattern = re.compile(
    r"MAG\s+X:([-+]?\d*\.?\d+)\s+Y:([-+]?\d*\.?\d+)\s+Z:([-+]?\d*\.?\d+)"
)

gps_pattern = re.compile(
    r"GPS\s+Lat:([-+]?\d*\.?\d+)\s+Lon:([-+]?\d*\.?\d+)\s+Alt:([-+]?\d*\.?\d+)m"
)


# ============================================
# MAIN LOOP
# ============================================

while True:

    try:
        line = ser.readline().decode("utf-8", errors="ignore").strip()

        if not line:
            continue

        # ------------------------------------
        # ACCELEROMETER
        # ------------------------------------

        acc_match = acc_pattern.search(line)

        if acc_match:
            ax = float(acc_match.group(1))
            ay = float(acc_match.group(2))
            az = float(acc_match.group(3))
        else:
            continue


        # ------------------------------------
        # GYROSCOPE
        # ------------------------------------

        gyro_match = gyro_pattern.search(line)

        if gyro_match:
            gx = float(gyro_match.group(1))
            gy = float(gyro_match.group(2))
            gz = float(gyro_match.group(3))
        else:
            continue


        # ------------------------------------
        # MAGNETOMETER
        # ------------------------------------

        mag_match = mag_pattern.search(line)

        if mag_match:
            mx = float(mag_match.group(1))
            my = float(mag_match.group(2))
            mz = float(mag_match.group(3))

            mag_magnitude = math.sqrt(
                mx * mx +
                my * my +
                mz * mz
            )

            # Raw horizontal heading
            heading = math.degrees(
                math.atan2(my, mx)
            )

            if heading < 0:
                heading += 360.0

        else:
            mx = my = mz = 0.0
            mag_magnitude = 0.0
            heading = 0.0


        # ------------------------------------
        # GPS
        # ------------------------------------

        gps_match = gps_pattern.search(line)

        if gps_match:

            latitude = float(gps_match.group(1))
            longitude = float(gps_match.group(2))
            altitude = float(gps_match.group(3))

            gps_text = (
                f"Lat:{latitude:.7f} "
                f"Lon:{longitude:.7f} "
                f"Alt:{altitude:.2f} m"
            )

        else:
            gps_text = "GPS waiting..."


        # ====================================
        # PRINT
        # ====================================

        print(
            f"ACC  "
            f"X:{ax:8.4f} "
            f"Y:{ay:8.4f} "
            f"Z:{az:8.4f}"
        )

        print(
            f"GYRO "
            f"X:{gx:8.5f} "
            f"Y:{gy:8.5f} "
            f"Z:{gz:8.5f}"
        )

        print(
            f"MAG  "
            f"X:{mx:8.2f} "
            f"Y:{my:8.2f} "
            f"Z:{mz:8.2f} "
            f"| Magnitude:{mag_magnitude:8.2f} "
            f"| Heading:{heading:7.2f} deg"
        )

        print("GPS ", gps_text)

        print("-" * 100)


    except KeyboardInterrupt:
        print("\nStopping...")
        ser.close()
        break

    except Exception as e:
        print("Error:", e)
