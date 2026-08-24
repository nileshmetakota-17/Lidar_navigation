import asyncio
import socket
import json
import time


class TeleopSubscriber:

    def __init__(self, port=5006):

        self.linear = 0.0
        self.angular = 0.0
        self.last_rx_time = 0.0

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", port))
        self.sock.setblocking(False)

    async def receiver(self):

        while True:

            try:
                data, addr = self.sock.recvfrom(1024)

                packet = json.loads(data.decode())

                self.linear = packet.get("linear", 0.0)
                self.angular = packet.get("angular", 0.0)

                self.last_rx_time = time.time()

            except BlockingIOError:
                pass

            except Exception as e:
                print(f"Teleop RX Error: {e}")

            await asyncio.sleep(0.001)

    def get_cmd(self):

        return self.linear, self.angular

    def timeout(self, timeout_sec=0.5):

        return (time.time() - self.last_rx_time) > timeout_sec
