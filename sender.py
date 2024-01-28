#!/usr/bin/env python3

import paho.mqtt.client as mqtt

# The terminal ID - can be any string.
terminal_id = "T0"
# The broker name or IP address.
broker = "iot-proj.swisz.cz"
# broker = "localhost"


# The MQTT client.
client = mqtt.Client()
client.username_pw_set("iot", "G516cD8#rSb£")


def call_worker(topic, message):
    client.publish(topic, message)


def connect_to_broker(topic="get/task", message="AN3W4324N43TSA"):
    # Connect to the broker.
    client.connect(broker)
    # Send message about conenction.
    call_worker(topic, message)


def disconnect_from_broker():
    # Send message about disconenction.
    # call_worker("Client disconnected")
    # Disconnet the client.
    client.disconnect()


def run_sender():
    connect_to_broker(message="330923611457")
    disconnect_from_broker()


if __name__ == "__main__":
    run_sender()
