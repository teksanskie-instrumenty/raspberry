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
reseted_after_finish = False
success_reseted = False

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
    if not success_reseted:
        display.clear()
        draw.rectangle([(0, 0), (96, 56)], fill="BLACK")
        draw.text((30, 10), "Good job!", font=fontSmall, fill="WHITE")
        display.ShowImage(image1, 0, 0)
        success_reseted = True


def start_task():
    global image1, draw, fontSmall, display, task_start, task_start_time, cur_exercise, reps, task_finished, reseted_after_finish, success_reseted
    success_reseted = True
    reseted_after_finish = False
    task_start = True
    task_finished = False
    reps = 0
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
    display.ShowImage(image1, 0, 0)
    task_start_time = time.time()


def setup_buzzer():
    GPIO.setup(BUZZER_PIN, GPIO.OUT)


def buzzer(state):
    GPIO.output(buzzerPin, not state)


def beep(pace1, pace2, pace3, pace4):
    cycle = pace1 + pace2 + pace3 + pace4
    global task_start_time
    duration = time.time() - task_start_time
    phase = duration % cycle
    if phase < pace1:
        buzzer(True)
    elif phase < pace1 + pace2:
        buzzer(False)
    elif phase < pace1 + pace2 + pace3:
        buzzer(True)
    elif phase < pace1 + pace2 + pace3 + pace4:
        buzzer(False)


def get_task_info():
    global current_task_id
    global task_start_time
    global task_end_time
    global task_start

    # subscribe to get/task/response
    # send get/task request
    print('getting task')
    send_get_task_request()
    print('request sent')


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
    global current_task_id, cur_exercise
    
    
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
    start_task()

    # show visual on a screen


def finish_task():
    global reseted_after_finish
    if not reseted_after_finish:
        global image1, draw, fontSmall, display, task_start, task_start_time, cur_exercise, reps, task_finished, confirmed, display, confirmedAt
        display.clear()
        task_finished = True
        draw.rectangle([(0, 0), (96, 56)], fill="BLACK")
        draw.text((30, 10), "Confirm finishing exercise", font=fontSmall, fill="WHITE")
        display.ShowImage(image1, 0, 0)
        confirmed = False
        confirmedAt = time.time()
        reseted_after_finish = True


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
        current_card_id
        + " "
        + current_task_id
        + " "
        + time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def update_exercise():
    print("updating exercise")
    global cur_exercise, reps, task_finished, task_start_time, confirmed, confirmedAt

    phases = (int(phase) for phase in cur_exercise["exercise"]["pace"])
    cycle = sum(phases)
    reps = int((time.time() - task_start_time) / cycle)

    if reps >= cur_exercise["repetitions"]:
        task_finished = True
        print(confirmed, confirmedAt)
        if confirmed and time.time() - confirmedAt < 5:
            print('success')
            showSuccess()
        elif confirmed and time.time() - confirmedAt < 6 and time.time() - confirmedAt > 5:
            resetDisplay()
        else:
            print('finish task')
            finish_task()
        return
    else:
        # beep(*(int(phase) for phase in cur_exercise["exercise"]["pace"]))
        pass


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
                if num == current_card_id and task_finished:
                    send_confirm_task_request()
                    print('confirming')
                    confirmed = True
                    confirmedAt = time.time()
                    # show success message
                elif num != current_card_id:
                    current_card_id = num
                    print(current_card_id)
                    task_finished = False
                    get_task_info()
        elif cur_exercise != None:
            update_exercise()
        elif confirmed and time.time() - confirmedAt > 5:
            confirmed = False
            resetDisplay()
            cur_exercise = None


# if card_read:
#     if card_read == current_card_id and exercise_finished:
#         send confirm/task request

#     else:
#         get_task_info() -> exercise = true, update screen
#         current_card_id = card_read
# elseif exercise:
#     interface update
# else:
#      continue
#
#

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
