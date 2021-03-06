#! /usr/bin/python
#-*-coding: utf-8 -*-

"""
 Imports: serial is needed for serial port communication with all RFID readers on all platforms.
 Install serial with pip if it is missing. RPi.GPIO is used only on the Raspberry Pi, and only
 when a callback function is installed on the Tag in-Range Pin that is only on the ID tag readers
 Otherwise, you can delete the import of RPi.GPIO
"""
import serial
import RPi.GPIO as GPIO

"""
global variables and call back function for use on Raspberry Pi with
ID Tag Readers with Tag-In-Range pin
Updates RFIDtag global variable whenever Tag-In-Range pin toggles
Setting tag to 0 means no tag is presently in range of the reader
"""
globalTag = 0
globalReader = None


def tagReaderCallback(channel):
    global globalTag # the global indicates that it is the same variable declared above
    if GPIO.input(channel) == GPIO.HIGH: # tag just entered
        try:
            globalTag = globalReader.readTag()
        except Exception as e:
            globalTag = 0
    else:  # tag just left
        globalTag = 0
        globalReader.clearBuffer()


class TagReader:
    """
    Class to read values from an ID-Innovations RFID tag reader, such as ID-20LA
    or an RDM tag reader, like the 630. Only differece for the two tag reader types is
    that the ID readers return 2 more termination characters than the RDM reader.
    ID - RFID Tag is 16 characters: STX(02h) DATA (10 ASCII) CHECK SUM (2 ASCII) CR LF ETX(03h)
    RDM - RFID Tag is 14 characters: STX(02h) DATA (10 ASCII) CHECK SUM (2 ASCII) ETX(03h)
    Other important differences : 
    1) the ID readers have a Tag-In-Range pin that goes from low to high when a tag
    comes into range, and stays high till the tag leaves. This allows
    use of an interrput function on a GPIO event to read the tag. The RDM readers do
    not have a Tag-In-Range pin, although they do a tag-read pin, which gives a brief
    pulse when a tag is read, so an interrupt can still be used to read a tag, but not to
    tell when a tag has left the tag reader range. 
    2) The ID readers report the tag only once, when the tag first enters the reading range.
    The RDM readers report the tag value repeatedly as long as the tag is in range, with a
    frequency somewhere between 1 and 2 Hz.
    
    """
    def __init__(self):
        """
        Makes a new RFIDTagReader object
        :param serialPort:serial port tag reader is attached to, /dev/ttyUSB0 or /dev/ttyAMA0 for instance
        :param doCheckSum: set to calculate the checksum on each tag read
        :param timeOutSecs:sets time out value. Use None for no time out, won't return until a tag has ben read
        """
        self.TIRpin = 23
        self.dataSize = 16
    # initialize serial port
        serial_port = '/dev/ttyS0'
        try:
            self.serialPort = serial.Serial(serial_port, baudrate=9600)
        except Exception as anError:
            print("Error initializing TagReader serial port.." + str(anError))
            raise anError
        if not self.serialPort.isOpen():
            self.serialPort.open()
        self.serialPort.flushInput()

    def clearBuffer(self):
        """
        Clears the serial inout buffer for the serialport used by the tagReader
        """
        self.serialPort.flushInput()

    def readTag(self):
        """
        Reads a hexidecimal RFID tag from the serial port and returns the decimal equivalent

        :returns: decimal value of RFID tag, or 0 if no tag and non-blocking reading was specified
        :raises:IOError:if serialPort not read
        raises:ValueError:if either checksum or conversion from hex to decimal fails
        
        Clears buffer if there is an error. This will delete data in the serial buffer if
        more than one tag has been read before calling readTag. Use with code that is interested in
        what is near the tagReader right now, not what may have passed by in the past.
        """
        # try to read a single byte with requested timeout, which may be no timeout
        self.serialPort.timeout = None
        tag = self.serialPort.read(size=1)
        # if there is a timeout with no data, return 0
        if tag == b'':
            return 0
        # if we read code for start of tag, read rest of tag with short timeout
        elif tag == b'\x02':
            self.serialPort.timeout = 0.025
            tag=self.serialPort.read(size=self.dataSize -1)
        # bad data. flush input buffer
        else:
            self.serialPort.flushInput()
            raise ValueError ('First character in tag was not \'\\x02\'')
        # the read timed out with not enough data for a tag, so return 0
        if tag.__len__() < self.dataSize - 1:
            self.serialPort.flushInput()
            raise ValueError('Not enough data in the buffer for a complete tag')
        try:
            decVal = int(tag[0:10], 16)
        except ValueError:
            self.serialPort.flushInput()
            raise ValueError("TagReader Error converting tag to integer: ", tag)
        else:
            if self.checkSum(tag[0:10], tag[10:12]):
                print("woot")
                return decVal
            else:
                self.serialPort.flushInput()
                raise ValueError("TagReader checksum error: ", tag, ' : ', tag[10:12])

    def checkSum(self, tag, checkSum):
        """
    Sequentially XOR-ing 2 byte chunks of the 10 byte tag value will give the 2-byte check sum

    :param tag: the 10 bytes of tag value
    :param checksum: the two bytes of checksum value
    :returns: True if check sum calculated correctly, else False
        """
        checkedVal = 0
        try:
            for i in range (0,5):
                checkedVal = checkedVal ^ int(tag[(2 * i): (2 * (i + 1))], 16)
            if checkedVal == int(checkSum, 16):
                return True
            else:
                return False
        except Exception as e:
            raise e("checksum error")

    def installCallback(self, tag_in_range_pin, callBackFunc=tagReaderCallback):
        """
        Installs a threaded call back for the tag reader, the default callback function
        being tagReaderCallback.  tagReaderCallback uses the global references globalReader for
        the RFIDTagReader object, and globalTag for the variable updated with the RFID Tag number.
        the call back sets global variable globalTag when tag-in-range pin toggles, either
        to the new tag value, if a tag just entered, or to 0 if a tag left.
        You can install your own callback, as long as it uses RFIDTagReader.globalReader 
        and only references RFIDTagReader.globalTag  and other global variables and objects.
        """
        global globalReader
        globalReader = self
        GPIO.setmode(GPIO.BCM)
        GPIO.add_event_detect(tag_in_range_pin, GPIO.BOTH)
        GPIO.add_event_callback(tag_in_range_pin, callBackFunc)

    def removeCallback(self):
        GPIO.remove_event_detect(self.TIRpin)
        GPIO.cleanup(self.TIRpin)
    
    def __del__(self):
        """
        close the serial port when we are done with it
        """
        if self.serialPort is not None:
            self.serialPort.close()
        if self.TIRpin != 0:
            GPIO.remove_event_detect(self.TIRpin)
            GPIO.cleanup(self.TIRpin)

