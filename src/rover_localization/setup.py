from glob import glob

from setuptools import find_packages, setup


package_name = "rover_localization"


setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        (
            "share/" + package_name,
            ["package.xml"],
        ),
        (
            "share/" + package_name + "/launch",
            glob("launch/*.launch.py"),
        ),
        (
            "share/" + package_name + "/config",
            glob("config/*.yaml") + glob("config/*.rviz"),
        ),
        (
            "share/" + package_name + "/urdf",
            glob("urdf/*.urdf") + glob("urdf/*.xacro"),
        ),
        (
            "share/" + package_name + "/meshes",
            glob("meshes/*"),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="nilesh",
    maintainer_email="nilesh@bhairavrobotics.in",
    description="EKF localization and debugging tools for the rover",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "odom_to_path = rover_localization.odom_to_path:main",
            "print_filtered = rover_localization.print_filtered:main",
            "print_position = rover_localization.print_position:main",
            "print_imu = rover_localization.print_imu:main",
            "livox_imu = rover_localization.livox_imu_print:main",
            'livox_imu_converter = rover_localization.livox_imu_converter:main',
        ],
    },
)
