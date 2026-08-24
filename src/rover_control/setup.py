from glob import glob

from setuptools import find_packages, setup


package_name = "rover_control"


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
            glob("config/*.yaml"),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="nilesh",
    maintainer_email="nilesh@bhairavrobotics.in",
    description="Control nodes for the physical rover",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "udp_bridge = rover_control.udp_bridge:main",
            "keyboard_teleop = rover_control.keyboard_teleop:main",
            "move_x = rover_control.move_x:main",
            "rotate = rover_control.rotate:main",
            "spin = rover_control.spin:main",
            "joy_control = rover_control.joy_control:main",
        ],
    },
)
