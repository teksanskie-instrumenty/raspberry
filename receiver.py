#!/usr/bin/env python3

import time
import json
import paho.mqtt.client as mqtt


client = mqtt.Client()
client.username_pw_set("iot", "G516cD8#rSb£")
topic = "get/task"
broker = "iot-proj.swisz.cz"
# broker="localhost"


def connect_to_broker(topic, process_message):
    # Connect to the broker.
    client.connect(broker)
    # Send message about conenction.
    client.on_message = process_message
    # Starts client and subscribe.
    client.loop_start()
    client.subscribe(topic)


def disconnect_from_broker():
    # Disconnet the client.
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    # GPIO.setmode(GPIO.BCM)
    connect_to_broker(
        "get/task/resp",
        lambda client, userdata, message: print(message.payload.decode("utf-8")),
    )
    input("")

    disconnect_from_broker()
