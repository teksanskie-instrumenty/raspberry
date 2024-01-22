#!/usr/bin/env python3

import time
import os
import board
import busio
import RPi.GPIO as GPIO
from config import *
import w1thermsensor
import adafruit_bme280.advanced as adafruit_bme280
from PIL import Image, ImageDraw, ImageFont
import lib.oled.SSD1331 as SSD1331

last_change = 0

def bme280Init():
    i2c = busio.I2C(board.SCL, board.SDA)
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, 0x76)

    bme280.sea_level_pressure = 1013.25
    bme280.standby_period = adafruit_bme280.STANDBY_TC_500
    bme280.iir_filter = adafruit_bme280.IIR_FILTER_X16
    bme280.overscan_pressure = adafruit_bme280.OVERSCAN_X16
    bme280.overscan_humidity = adafruit_bme280.OVERSCAN_X1
    bme280.overscan_temperature = adafruit_bme280.OVERSCAN_X2
    
    return bme280

def bme280Read():
    bme280 = bme280Init()

    temperature = bme280.temperature
    humidity = bme280.humidity
    pressure = bme280.pressure
    altitude = bme280.altitude

    print('\nBME280:')
    print(f'Temperature: {temperature:0.1f}{chr(176)}C')
    print(f'Humidity: {humidity:0.1f} %')
    print(f'Pressure: {pressure:0.1f} hPa')
    print(f'Altitude: {altitude:0.2f} meters')

    return temperature, humidity, pressure, altitude

def ds18b20Read():
    sensor = w1thermsensor.W1ThermSensor()

    temperature = sensor.get_temperature()
    
    print(f'Temperature: {temperature:0.1f}{chr(176)}C')
    
    return temperature


display = SSD1331.SSD1331()

def initDisplay(display):
    display.Init()
    display.clear()


image1 = Image.new("RGB", (display.width, display.height), "BLACK")
draw = ImageDraw.Draw(image1)
fontSmall = ImageFont.truetype('./lib/oled/Font.ttf', 10)

def initGUI():
    global image1, draw, fontSmall

    draw.rectangle([(0, 0), (5, 10)], fill="GREEN")
    draw.text((10, 0), 'temp.:', font=fontSmall, fill="GREEN")

    draw.rectangle([(0, 15), (5, 25)], fill="BLUE")
    draw.text((10, 15), 'hum.:', font=fontSmall, fill="BLUE")
    
    draw.rectangle([(0, 30), (5, 40)], fill="YELLOW")
    draw.text((10, 30), 'press.:', font=fontSmall, fill="YELLOW")
    
    draw.rectangle([(0, 45), (5, 55)], fill="WHITE")
    draw.text((10, 45), 'alt.:', font=fontSmall, fill="WHITE")

    display.ShowImage(image1, 0, 0)

def readMeasurements(temperature, humidity, pressure, altitude):
    global draw, fontSmall
    draw.rectangle([(50, 0), (96, 56)], fill="BLACK")  

    draw.text((50, 0), f'{temperature:.1f}{chr(176)}C', font=fontSmall, fill="GREEN")
    draw.text((50, 15), f'{humidity:.1f}%', font=fontSmall, fill="BLUE")
    draw.text((50, 30), f'{pressure:.1f} hPa', font=fontSmall, fill="YELLOW")
    draw.text((50, 45), f'{altitude:.2f} m', font=fontSmall, fill="WHITE")      

    display.ShowImage(image1, 0, 0)

def main():
    GPIO.setmode(GPIO.BCM)
    print("\nProgram started")
    initDisplay(display)
    initGUI()

    try:
        while True:
            t, h, p, a = bme280Read()
            readMeasurements(t, h, p, a)
    except KeyboardInterrupt:
        print("\nProgram terminated")
    
    print("\nProgram finished")


if __name__ == "__main__":
    main()



'''
Image.frombuffer()
Image.frombytes()

https://hhsprings.bitbucket.io/docs/programming/examples/python/PIL/Image__Functions.html
https://stackoverflow.com/questions/32908639/open-pil-image-from-byte-file
https://stackoverflow.com/questions/43078729/pils-image-frombuffer-creates-wrong-image
https://www.geeksforgeeks.org/python-pil-image-frombuffer-method/

https://gist.github.com/sleepless-se/3674830cbb53b9e04b03b18f2b47815e
https://github.com/novaspirit/img2bytearray

Image.paste()
ImageDraw.bitmap()

https://stackoverflow.com/questions/64363171/why-does-pillow-invert-the-colors-when-drawing-via-imagedraw
'''