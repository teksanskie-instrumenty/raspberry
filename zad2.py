#!/usr/bin/env python3

import time
import RPi.GPIO as GPIO
from config import *  # pylint: disable=unused-wildcard-import
from mfrc522 import MFRC522
import neopixel
import board

BUZZER_PIN = buzzerPin

def setup_buzzer():
    GPIO.setup(BUZZER_PIN, GPIO.OUT)

def buzzer(state):
    GPIO.output(buzzerPin, not state)

def beep():
    buzzer(True)
    time.sleep(0.1)
    buzzer(False)

def init_led():
    strip = neopixel.NeoPixel(board.D18, 8, brightness=1.0/32, auto_write=False)
    return strip

def turn_on_led(strip, color):
    strip.fill(color)
    strip.show()

def turn_off_led(strip):
    turn_on_led(strip, (0, 0, 0))

def rfid_read(strip):
    MIFAREReader = MFRC522()
    counter = 0
    # uid -> status
    card_dict_start = {}
    card_dict_end = {}
    prev_state = False
    debounce = 200000000
    last_true_read_timestamp = 0
    cur_uid = -1
    while True:
        (status, TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)
        if status == MIFAREReader.MI_OK:
            (status, uid) = MIFAREReader.MFRC522_Anticoll()
            if status == MIFAREReader.MI_OK:
                prev_state = True
                last_true_read_timestamp = time.time_ns()
                num = 0
                for i in range(0, len(uid)):
                    num += uid[i] << (i * 8)
                if (num in card_dict_start.keys() and num in card_dict_end.keys()):
                    continue
                elif (num not in card_dict_start.keys()):
                    card_dict_start[num] = time.time_ns()
                    cur_uid = num
                    buzzer(True)
                    turn_on_led(strip, (0, 255, 0))
                    print(f"Card read UID: {uid} > {num}")
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"Timestamp: {timestamp}")
                    prev_state = True
                elif (time.time_ns() - card_dict_start[num] > 100000):
                    buzzer(False)
                    turn_off_led(strip)
                counter += 1
        elif prev_state:
            if(time.time_ns()-last_true_read_timestamp > debounce and cur_uid in card_dict_start.keys() and cur_uid not in card_dict_end.keys()):
                buzzer(False)
                card_dict_end[cur_uid] = time.time_ns()
                hold_time = (float)(card_dict_end[cur_uid] - card_dict_start[cur_uid])/1000000000.0
                print(f'Card was held for {hold_time} seconds')
                prev_state = False
                turn_off_led(strip)
                card_dict_start.pop(cur_uid)
                card_dict_end.pop(cur_uid)

if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    try:
        led_strip = init_led()
        setup_buzzer()
        print('\nThe RFID reader test.')
        print('Place the card close to the reader (on the right side of the set).')
        rfid_read(led_strip)
        print("The RFID reader tested successfully.")
    finally:
        GPIO.cleanup()
