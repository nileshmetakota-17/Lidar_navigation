#!/usr/bin/env python3

import re
import sys
import math
import csv


if len(sys.argv) != 2:
    print(f"Usage: python3 {sys.argv[0]} <log_file.txt>")
    sys.exit(1)

filename = sys.argv[1]

# Example expected:
# MAG_RAW X:612 Y:-268 Z:-429
pattern = re.compile(
    r"MAG_RAW\s+X:\s*(-?\d+(?:\.\d+)?)\s+"
    r"Y:\s*(-?\d+(?:\.\d+)?)\s+"
    r"Z:\s*(-?\d+(?:\.\d+)?)"
)

samples = []

with open(filename, "r", errors="ignore") as f:
    for line in f:
        match = pattern.search(line)

        if match:
            mx = float(match.group(1))
            my = float(match.group(2))
            mz = float(match.group(3))

            samples.append((mx, my, mz))


if len(samples) < 10:
    print("ERROR: Not enough MAG_RAW samples found.")
    print(f"Found only {len(samples)} samples.")
    sys.exit(1)


print("\n========================================")
print("      MAGNETOMETER CALIBRATION")
print("========================================")
print(f"Samples collected: {len(samples)}")


xs = [s[0] for s in samples]
ys = [s[1] for s in samples]
zs = [s[2] for s in samples]


# ------------------------------------------------
# Min / Max
# ------------------------------------------------

xmin = min(xs)
xmax = max(xs)

ymin = min(ys)
ymax = max(ys)

zmin = min(zs)
zmax = max(zs)


print("\nRAW MIN / MAX")
print("----------------------------------------")
print(f"X min = {xmin:10.3f}   X max = {xmax:10.3f}")
print(f"Y min = {ymin:10.3f}   Y max = {ymax:10.3f}")
print(f"Z min = {zmin:10.3f}   Z max = {zmax:10.3f}")


# ------------------------------------------------
# Hard Iron Offset
# ------------------------------------------------

offset_x = (xmax + xmin) / 2.0
offset_y = (ymax + ymin) / 2.0
offset_z = (zmax + zmin) / 2.0


print("\nHARD IRON OFFSETS")
print("----------------------------------------")
print(f"offset_x = {offset_x:.6f}")
print(f"offset_y = {offset_y:.6f}")
print(f"offset_z = {offset_z:.6f}")


# ------------------------------------------------
# Radius on each axis
# ------------------------------------------------

radius_x = (xmax - xmin) / 2.0
radius_y = (ymax - ymin) / 2.0
radius_z = (zmax - zmin) / 2.0


print("\nAXIS RADII")
print("----------------------------------------")
print(f"radius_x = {radius_x:.6f}")
print(f"radius_y = {radius_y:.6f}")
print(f"radius_z = {radius_z:.6f}")


if radius_x == 0 or radius_y == 0 or radius_z == 0:
    print("\nERROR: One axis has zero range.")
    print("Rotate the sensor through all 3 axes.")
    sys.exit(1)


# ------------------------------------------------
# Soft Iron Scale
# ------------------------------------------------

average_radius = (radius_x + radius_y + radius_z) / 3.0

scale_x = average_radius / radius_x
scale_y = average_radius / radius_y
scale_z = average_radius / radius_z


print("\nSOFT IRON SCALE")
print("----------------------------------------")
print(f"scale_x = {scale_x:.6f}")
print(f"scale_y = {scale_y:.6f}")
print(f"scale_z = {scale_z:.6f}")


# ------------------------------------------------
# Apply calibration
# ------------------------------------------------

calibrated = []

for mx, my, mz in samples:

    mx_cal = (mx - offset_x) * scale_x
    my_cal = (my - offset_y) * scale_y
    mz_cal = (mz - offset_z) * scale_z

    magnitude = math.sqrt(
        mx_cal * mx_cal +
        my_cal * my_cal +
        mz_cal * mz_cal
    )

    calibrated.append(
        (mx, my, mz,
         mx_cal, my_cal, mz_cal,
         magnitude)
    )


magnitudes = [s[6] for s in calibrated]

mag_min = min(magnitudes)
mag_max = max(magnitudes)
mag_avg = sum(magnitudes) / len(magnitudes)


print("\nCALIBRATED MAGNITUDE")
print("----------------------------------------")
print(f"Minimum |M| = {mag_min:.3f}")
print(f"Average |M| = {mag_avg:.3f}")
print(f"Maximum |M| = {mag_max:.3f}")

variation = ((mag_max - mag_min) / mag_avg) * 100.0

print(f"Total variation = {variation:.2f} %")


# ------------------------------------------------
# C/C++ constants
# ------------------------------------------------

print("\n========================================")
print("COPY THESE VALUES INTO YOUR CODE")
print("========================================")

print(f"""
float MAG_OFFSET_X = {offset_x:.6f};
float MAG_OFFSET_Y = {offset_y:.6f};
float MAG_OFFSET_Z = {offset_z:.6f};

float MAG_SCALE_X = {scale_x:.6f};
float MAG_SCALE_Y = {scale_y:.6f};
float MAG_SCALE_Z = {scale_z:.6f};
""")


print("Calibration formula:")
print("""
mx_cal = (mx_raw - MAG_OFFSET_X) * MAG_SCALE_X;
my_cal = (my_raw - MAG_OFFSET_Y) * MAG_SCALE_Y;
mz_cal = (mz_raw - MAG_OFFSET_Z) * MAG_SCALE_Z;
""")


# ------------------------------------------------
# Save CSV
# ------------------------------------------------

output_file = "mag_calibrated.csv"

with open(output_file, "w", newline="") as f:

    writer = csv.writer(f)

    writer.writerow([
        "mx_raw",
        "my_raw",
        "mz_raw",
        "mx_cal",
        "my_cal",
        "mz_cal",
        "magnitude"
    ])

    writer.writerows(calibrated)


print(f"Calibration data saved to: {output_file}")
print("========================================\n")
