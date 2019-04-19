#! /usr/bin/python
#-*-coding: utf-8 -*-

"""
Simple test script for TagReader
Reads a few tags and prints them
Last Modified:
2018/03/07 by Jamie Boyd - added some comments, cleaned up a bit
"""

from RFIDTagReader import TagReader
import RPi.GPIO as GPIO


"""
Setting to timeout to None means we don't return till we have a tag.
If a timeout is set and no tag is found, 0 is returned.
"""
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN)
reader = TagReader()


def read_tag():
    try:
        tag = reader.readTag()
        print(tag)
        wait_for_tag_exit()
    except ValueError as e:
        print(str(e))
        reader.clearBuffer()
    except KeyboardInterrupt:
        GPIO.cleanup()

def wait_for_tag_exit():
    try:
        while True:
            if not GPIO.input(23):
                print('Tag has left')
    except KeyboardInterrupt:
        GPIO.cleanup()

if __name__ ==  "__main__":
    read_tag()


