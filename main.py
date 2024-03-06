import asyncio
from contextlib import suppress
from typing import Type
from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic
from bleak.backends.client import BaseBleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.winrt.client import WinRTClientArgs
import matplotlib.pyplot as plt
import numpy as np
from threading import Thread
from flask import Flask
import base64
from io import BytesIO
import math
from matplotlib.figure import Figure


app = Flask(__name__)
hub_data = []


# class PUPBleakClient(BleakClient):
#     def __init__(self, address_or_ble_device: BLEDevice | str, disconnected_callback: Callable[[BleakClient], None] | None = None, services: Iterable[str] | None = None, *, timeout: float = 10, winrt: WinRTClientArgs = ..., backend: type[BaseBleakClient] | None = None, **kwargs):
#         super().__init__(address_or_ble_device, disconnected_callback, services, timeout=timeout, winrt=winrt, backend=backend, **kwargs)

class ComThread(Thread):

    HUB_NAME = "Pybricks Hub"
    PYBRICKS_COMMAND_EVENT_CHAR_UUID = "c5f50002-8280-46da-89f4-6d8051e4aeef"
    WRITE_STDOUT_EVENT = 0x01
    ODOMETRY_DATA = ord('o')

    def __init__(self) -> None:
        super().__init__(target=self._thread_func, daemon=True)

    def _thread_func(self):
        with suppress(asyncio.CancelledError):
            asyncio.run(self.comunication_corutine())

    async def comunication_corutine(self):
        main_task = asyncio.current_task()

        def handle_disconnect(_):
            print("Hub was disconnected.")

            if not main_task.done():
                main_task.cancel()

        def handle_rx(sender: BleakGATTCharacteristic, data: bytearray):
            if data[0] == self.WRITE_STDOUT_EVENT:
                payload = data[1:]
                if payload[0] == self.ODOMETRY_DATA:
                    dx, dy = payload[1:]
                    hub_data.append((dx,dy))
                    print(f"Received odometry data: dx={dx}, dy={dy}", flush=True)

            
        dev = await BleakScanner.find_device_by_name(self.HUB_NAME)
        if dev is None:
            print(f"Could not find hub with name {self.HUB_NAME}")
            if not main_task.done():
                main_task.cancel()
                return
        else:
            print(f"Device {self.HUB_NAME} found. Press green button on the device to start the program.")

        async with BleakClient(dev, handle_disconnect) as client:
            await client.start_notify(self.PYBRICKS_COMMAND_EVENT_CHAR_UUID, handle_rx)
            while client.is_connected:
                await asyncio.sleep(1)


@app.route("/")
def hello_world():
    fig = Figure()
    ax= fig.subplots()
    X = [data_item[0] for data_item in hub_data]
    Y = [data_item[1] for data_item in hub_data]
    ax.plot(X,Y)
    buf = BytesIO()
    fig.savefig(buf, format="png")
    data = base64.b64encode(buf.getbuffer()).decode('ascii')
    return f"<meta http-equiv='refresh' content='1'><img src='data:image/png;base64,{data}'/>" 


if __name__ == "__main__":

    print("Starting comunication thread...")
    comThread = ComThread()
    comThread.start()
    print("Starting Flask server...")
    app.run(debug=False, use_reloader=False)
     

# https://matplotlib.org/stable/gallery/user_interfaces/web_application_server_sgskip.html#sphx-glr-gallery-user-interfaces-web-application-server-sgskip-py 
# https://flask.palletsprojects.com/en/3.0.x/async-await/
# https://flask.palletsprojects.com/en/3.0.x/quickstart/#a-minimal-application
# http://127.0.0.1:5000/