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


def act(client, userdata, message):
    message_decoded = str(message.payload.decode("utf-8"))
    if message_decoded == "Card not assigned to user":
        print("card not assigned to the user")
        return
    print(message_decoded)
    try:
        parsed = json.loads(message_decoded)
    except:
        print("parse error")
        return

    exercises = parsed["dailyPlanExercises"]
    if len(exercises) == 0:
        print("no exercises")
        return

    exercises.sort(key=lambda x: x["order"])
    current_exercise = exercises[0]
    for exercise in exercises:
        if not exercise["is_finished"]:
            current_exercise = exercise
            break
    cur_exercise = current_exercise
    current_task_id = str(current_exercise["id"])
    print("current task id: " + current_task_id)
    print("current exercise: " + current_exercise["exercise"]["name"])
    time.sleep(10)

    current_card_id = "330923611457"

    print(f'{current_card_id} {current_task_id} {time.strftime("%Y-%m-%dT%H:%M:%SZ")}')
    import sender
    sender.connect_to_broker(
        "confirm/task",
        f'{current_card_id} {current_task_id} {time.strftime("%Y-%m-%dT%H:%M:%SZ")}',
    )
    sender.disconnect_from_broker()


if __name__ == "__main__":
    # GPIO.setmode(GPIO.BCM)

    connect_to_broker("get/task/resp", act)
    input("")

    disconnect_from_broker()
