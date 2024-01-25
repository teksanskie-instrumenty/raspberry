import time
import RPi.GPIO as GPIO
from config import *  # pylint: disable=unused-wildcard-import
from mfrc522 import MFRC522
import neopixel
import board
import paho.mqtt.client as mqtt
import sender
import raspberry.receiver as receiver
import json
import busio
import adafruit_bme280.advanced as adafruit_bme280
from PIL import Image, ImageDraw, ImageFont
import lib.oled.SSD1331 as SSD1331

# App logic
# put card -> sprawdzenie, czy ćwiczenie jest zaczęte, jeśli tak przerywa poprzednie, jeśli nie to zaczyna nowe
# 1. starting activity ->
# get/task card id -> show task info -> start buzzing -> start timer -> timer ends -> show success message -> stop buzzing -> stop timer -> stop showing task info
# interruption -> new task

current_card_id = -1
current_task_id = -1
task_start_time = -1
task_end_time = -1
task_start = False
task_length = 60
task_finished = True
cur_exercise = None
confirmed = False
confirmedAt = 0
pace = 0.5
reps = 0
parsed = None

application_state = 0
last_changed_at = 0
ui_updated = True
IDLE = 0
NEW_CARD = 1
EXERCISE = 2
EXERCISE_FINISHED = 3
WAITING_FOR_CONFIRMATION = 4
DIRECT_TO_NEXT_EXERCISE = 5

BUZZER_PIN = buzzerPin

display = SSD1331.SSD1331()
image1 = Image.new("RGB", (display.width, display.height), "BLACK")
draw = ImageDraw.Draw(image1)
fontSmall = ImageFont.truetype("./lib/oled/Font.ttf", 10)


def initDisplay(display):
    display.Init()
    display.clear()
    global image1, draw, fontSmall
    draw.text((30, 10), "Put card to a reader", font=fontSmall, fill="WHITE")
    display.ShowImage(image1, 0, 0)


def resetDisplay():
    global image1, draw, fontSmall, display
    display.clear()
    draw.rectangle([(0, 0), (96, 56)], fill="BLACK")
    draw.text((0, 10), "Put card to a reader", font=fontSmall, fill="WHITE")
    display.ShowImage(image1, 0, 0)


def showSuccess():
    global image1, draw, fontSmall, display, success_reseted

    display.clear()
    draw.rectangle([(0, 0), (96, 56)], fill="BLACK")
    draw.text((30, 10), "Good job!", font=fontSmall, fill="WHITE")
    display.ShowImage(image1, 0, 0)


def start_task():
    global image1, draw, fontSmall, display, cur_exercise, reps, task_finished
    display.clear()
    draw.rectangle([(0, 0), (96, 56)], fill="BLACK")
    draw.text(
        (10, 10),
        f"Current exercise:",
        font=fontSmall,
        fill="WHITE",
    )
    draw.text(
        (10, 20),
        f"{cur_exercise['exercise']['name']}",
        font=fontSmall,
        fill="WHITE",
    )
    draw.text(
        (10, 30),
        f"Repetitions: {cur_exercise['repetitions']}",
        font=fontSmall,
        fill="WHITE",
    )
    draw.text(
        (10, 40),
        f"Repetitions made: {reps}",
        font=fontSmall,
        fill="WHITE",
    )
    display.ShowImage(image1, 0, 0)


def direct_to_next_exercise():
    print("directing to next exercise wow")
    global image1, draw, fontSmall, display, cur_exercise, reps, task_finished, parsed

    display.clear()
    draw.rectangle([(0, 0), (96, 56)], fill="BLACK")

    exercises = parsed["dailyPlanExercises"]
    exercises.sort(key=lambda x: x["order"])
    unfinished = [exercise for exercise in exercises if not exercise["is_finished"]]
    if len(unfinished) <= 1:
        draw.text(
            (10, 10),
            f"Your daily plan",
            font=fontSmall,
            fill="WHITE",
        )
        draw.text(
            (10, 20),
            f"is finished",
            font=fontSmall,
            fill="WHITE",
        )
    else:
        draw.text(
            (10, 10),
            f"Next exercise:",
            font=fontSmall,
            fill="WHITE",
        )
        draw.text(
            (10, 20),
            f"{unfinished[1]['exercise']['name']}",
            font=fontSmall,
            fill="WHITE",
        )
        draw.text(
            (10, 30),
            f"Repetitions: {unfinished[1]['repetitions']}",
            font=fontSmall,
            fill="WHITE",
        )
    display.ShowImage(image1, 0, 0)


def setup_buzzer():
    GPIO.setup(BUZZER_PIN, GPIO.OUT)


def buzzer(state):
    GPIO.output(buzzerPin, not state)


def beep(pace1, pace2, pace3, pace4):
    cycle = pace1 + pace2 + pace3 + pace4
    global task_start_time
    duration = time.time() - task_start_time
    phase = duration % cycle
    buzzer_phase = duration % 0.2
    if phase < pace1:
        buzzer(buzzer_phase < 0.1)
    elif phase < pace1 + pace2:
        buzzer(False)
    elif phase < pace1 + pace2 + pace3:
        buzzer(buzzer_phase < 0.1)
    elif phase < pace1 + pace2 + pace3 + pace4:
        buzzer(False)


def get_task_info():
    global current_card_id
    print("getting task")
    sender.connect_to_broker("get/task", current_card_id)
    sender.disconnect_from_broker()
    print("request sent")


def act_on_task_info(client, userdata, message):
    # """
    # {
    #     "dailyPlan": {
    #         "id": 2,
    #         "name": "Zdrowe plecy",
    #         "description": "Ulecz ból pleców",
    #         "image": "./plecy.png",
    #     },
    #     "dailyPlanExercises": [
    #         {
    #             "id": 3,
    #             "order": 1,
    #             "sets": 3,
    #             "repetitions": 10,
    #             "interval": 60,
    #             "exercise": {
    #                 "id": 1,
    #                 "station_id": 1,
    #                 "name": "plecy 1",
    #                 "pace": "3040",
    #             },
    #             "when_finished": "2022-03-01T11:00:00.000Z",
    #             "is_finished": true,
    #         },
    #         {
    #             "id": 2,
    #             "order": 1,
    #             "sets": 3,
    #             "repetitions": 10,
    #             "interval": 60,
    #             "exercise": {
    #                 "id": 1,
    #                 "station_id": 1,
    #                 "name": "plecy 1",
    #                 "pace": "3040",
    #             },
    #             "when_finished": "2022-03-01T11:00:00.000Z",
    #             "is_finished": true,
    #         },
    #         {
    #             "id": 1,
    #             "order": 1,
    #             "sets": 20,
    #             "repetitions": 10,
    #             "interval": 5,
    #             "exercise": {
    #                 "id": 1,
    #                 "station_id": 1,
    #                 "name": "plecy 1",
    #                 "pace": "3040",
    #             },
    #             "when_finished": "2022-03-01T11:00:00.000Z",
    #             "is_finished": true,
    #         },
    #     ],
    # }
    # """
    global current_task_id, cur_exercise, parsed

    # sender.disconnect_from_broker()
    message_decoded = str(message.payload.decode("utf-8"))
    print(message_decoded)
    parsed = json.loads(message_decoded)
    exercises = parsed["dailyPlanExercises"]
    exercises.sort(key=lambda x: x["order"])
    current_exercise = exercises[0]
    for exercise in exercises:
        if not exercise["is_finished"]:
            current_exercise = exercise
            break
    cur_exercise = current_exercise
    current_task_id = str(current_exercise["id"])
    change_app_state(EXERCISE)


def finish_task():
    global image1, draw, fontSmall, display, task_start, task_start_time, cur_exercise, reps, task_finished, confirmed, display, confirmedAt
    display.clear()
    task_finished = True
    draw.rectangle([(0, 0), (96, 56)], fill="BLACK")
    draw.text((10, 10), "Confirm finishing", font=fontSmall, fill="WHITE")
    draw.text((10, 20), "exercise. Put card", font=fontSmall, fill="WHITE")
    draw.text((10, 30), "to reader", font=fontSmall, fill="WHITE")
    display.ShowImage(image1, 0, 0)


def send_get_task_request():
    # send get/task request
    global current_card_id
    sender.connect_to_broker("get/task", current_card_id)
    sender.disconnect_from_broker()


def send_confirm_task_request():
    # send confirm/task request
    global current_card_id
    global current_task_id
    # current timestamp in format 2022-03-01T10:00:00Z
    sender.connect_to_broker(
        "confirm/task",
        f'{current_card_id} {current_task_id} {time.strftime("%Y-%m-%dT%H:%M:%SZ")}',
    )
    sender.disconnect_from_broker()


def update_state():
    global ui_updated, application_state, last_changed_at, cur_exercise
    if application_state == IDLE:
        if not ui_updated:
            resetDisplay()
            ui_updated = True
    elif application_state == NEW_CARD:
        if not ui_updated:
            get_task_info()
            ui_updated = True
    elif application_state == EXERCISE:
        if not ui_updated:
            start_task()
            ui_updated = True
        global cur_exercise, reps, task_finished, task_start_time, confirmed, confirmedAt

        beep(*(int(phase) for phase in cur_exercise["exercise"]["pace"]))

        phases = (int(phase) for phase in cur_exercise["exercise"]["pace"])
        cycle = sum(phases)
        reps = int((time.time() - task_start_time) / cycle)
        if reps >= cur_exercise["repetitions"]:
            change_app_state(EXERCISE_FINISHED)
    elif application_state == EXERCISE_FINISHED:
        if not ui_updated:
            showSuccess()
            ui_updated = True
        if time.time() - last_changed_at > 5:
            showSuccess()
            change_app_state(WAITING_FOR_CONFIRMATION)
    elif application_state == WAITING_FOR_CONFIRMATION:
        if not ui_updated:
            finish_task()
            ui_updated = True
        # 3 minutes passed
        if time.time() - last_changed_at > 180:
            resetDisplay()
            change_app_state(IDLE)
    elif application_state == DIRECT_TO_NEXT_EXERCISE:
        if not ui_updated:
            send_confirm_task_request()
            direct_to_next_exercise()
            ui_updated = True
        # 15 SECOND PASSED
        if time.time() - last_changed_at > 15:
            change_app_state(IDLE)
            cur_exercise = None


def main_loop():
    global task_length
    global cur_exercise
    global confirmed, confirmedAt
    global current_card_id
    MIFAREReader = MFRC522()
    while True:
        (status, TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)
        if status == MIFAREReader.MI_OK:
            (status, uid) = MIFAREReader.MFRC522_Anticoll()
            if status == MIFAREReader.MI_OK:
                num = 0
                for i in range(0, len(uid)):
                    num += uid[i] << (i * 8)
                print(current_card_id)
                if num == current_card_id:
                    same_card(num)
                    print("same card")
                elif num != current_card_id:
                    handle_new_card(num)

        update_state()


def same_card(num):
    global application_state, last_changed_at
    if application_state == IDLE:
        print("idle")
    elif application_state == NEW_CARD:
        print("new card")
    elif application_state == EXERCISE:
        print("exercise")
    elif application_state == EXERCISE_FINISHED:
        change_app_state(DIRECT_TO_NEXT_EXERCISE)
    elif application_state == WAITING_FOR_CONFIRMATION:
        change_app_state(EXERCISE_FINISHED)
    elif application_state == DIRECT_TO_NEXT_EXERCISE:
        print("direct to next exercise")


def handle_new_card(num):
    global application_state, last_changed_at, current_card_id
    current_card_id = num
    change_app_state(NEW_CARD)


def change_app_state(state):
    global application_state, last_changed_at, ui_updated
    print(f'change{application_state}->{state}')
    application_state = state
    last_changed_at = time.time()
    ui_updated = False


if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    print("\nProgram started")
    initDisplay(display)
    setup_buzzer()
    receiver.connect_to_broker("get/task/resp", process_message=act_on_task_info)
    try:
        resetDisplay()
        main_loop()
    except KeyboardInterrupt:
        print("\nProgram terminated")

    receiver.disconnect_from_broker()
    print("\nProgram finished")
