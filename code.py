print("Hello  World!")
# a small portion of this code comes from an Adafruit example, I leave there copyright here
# For my code, please do not use for comercial purposes.
# SPDX-FileCopyrightText: 2022 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
import os
import time
import board
import busio
from adafruit_neotrellis.neotrellis import NeoTrellis
import ssl
import wifi
import socketpool
import microcontroller
import adafruit_requests

# setup: CIRCUITPY_WIFI_SSID and CIRCUITPY_WIFI_PASSWORD in settings.toml for
# automatic connection to WIFI.   Also the following env vars are set up in settings.toml
REST_URL = os.getenv("REST_URL")
RIGHT_LAMP = os.getenv("RIGHT_LAMP")
LEFT_LAMP = os.getenv("LEFT_LAMP")
BOTH_LAMPS = os.getenv("BOTH_LAMPS")
TREE = os.getenv("TREE")
DINING_ROOM_LIGHTS = os.getenv("DINING_ROOM_LIGHTS")
DINING_ROOM_DIMMER = os.getenv("DINING_ROOM_DIMMER")

#used in rest api calls for authentication
myHeaders = {'Authorization': 'Basic '+os.getenv('HOME_AUTOMATION_TOKEN'), 'Content-Type': 'text/plain'}

# where o where is the queue class?
class queue:
    def __init__(self):
        self.storage = []
    
    def push(self, val):
        self.storage.append(val)
    
    def pop(self):
        results = self.storage[0]
        self.storage = self.storage[1:]
        return results

    def front(self):
        return self.storage[0]
    
    def back(self):
        return self.storage[-1]
    
    def valAt(self, idx):
        return self.storage[idx]


#initialization for "snake" dazzling mode
def initSnake():
    global board, snakeColors, snake, dr,dc, snakeActive
    colorWipe(OFF)
    #initialize the 4x4 board to empty
    board = [[False for x in range(4)] for x in range(4)]
    snakeColors = [RED, GREEN, BLUE]
    
    # place the snake in
    snake = queue()
    
    for i in range(3):
        board[0][i] = True
        #trellis.pixels[i] = snakeColors[2-i]
        snake.push(2-i)
    
    dr = 1
    dc = 0
    snakeActive = False
    
#step the snake across the keypad
def stepSnake():
    global board, snakeColors, snake, dr,dc, snakeActive
    if snakeActive:
        #move snake
        snakeHead = snake.back()
        row, col = divmod(snakeHead, 4)
        #print(f'{snakeHead}, {row}, {col}')
        newRow = row+dr
        newCol = col+dc
        if newRow >= 0 and newRow < 4 and newCol >= 0 and newCol < 4 and not board[newRow][newCol]:
            nr = newRow
            nc = newCol
        else:
            possibleDirections = []
            for drdc in [(-1,-1), (-1, 0), (-1, 1), (0,-1), (0, 1), (1,-1), (1, 0), (1,1)]:
                nr = row + drdc[0]
                nc = col + drdc[1]
                if nr >= 0 and nr < 4 and nc >= 0 and nc <4 and not board[nr][nc]:
                    possibleDirections.append(drdc)
            newDir = possibleDirections[ord(os.urandom(1)) % len(possibleDirections)]
            nr = row + newDir[0]
            nc = col + newDir[1]
            dr = newDir[0]
            dc = newDir[1]
        board[nr][nc] = True
        newSnake = nr*4+nc
        snakeTail = snake.pop()
        stR, stC = divmod(snakeTail, 4)
        board[stR][stC] = False
        trellis.pixels[snakeTail] = OFF
        snake.push(newSnake)
        for i in range(3):
            snakeSeg = snake.valAt(i)
            trellis.pixels[snakeSeg] = snakeColors[i]        
    



# for Raspberry Pi Pico W, this gets the i2c bus easilly
i2c_bus = board.STEMMA_I2C()

# create the trellis
trellis = NeoTrellis(i2c_bus)

# Set the brightness value (0 to 1.0)
trellis.brightness = 0.5

# some color definitions
OFF = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
CYAN = (0, 255, 255)
MAGENTA = (255,0,255)
YELLOW = (255, 150, 0)
PURPLE = (180, 0, 255)
RANDOM = (1,2,3) # a special color to tell colorWipe to use random colors

colorSet = [RED, GREEN, BLUE, CYAN, MAGENTA, YELLOW, PURPLE]

#sweep a color or colors across keypad and then clear to off
def colorWipe(color):
    if color == RANDOM:
        for i in range(16):
            trellis.pixels[i] = colorSet[ord(os.urandom(1))%len(colorSet)]
    else:
        for i in range(16):
            trellis.pixels[i] = color
    for i in range(16):
        trellis.pixels[i] = OFF
    
#memoryGame globals
sequence = []
stepInSequence = 0
seqLength = 1
ignoreGameButtons = True

#track user keypresses during the game
def memoryGameButtonEvent(event):
    global sequence, stepInSequence, seqLength, ignoreGameButtons
    if ignoreGameButtons :
        return
    
    if event.edge == NeoTrellis.EDGE_RISING:
        #a button was pressed down
        print(f'event.number: {event.number}, sequence: {sequence[stepInSequence][0]}')
        if event.number == sequence[stepInSequence][0]:
            #it was the correct one for the current step in the sequence
            #flash it's sequence color
            trellis.pixels[event.number] = sequence[stepInSequence][1]
            time.sleep(1)
            trellis.pixels[event.number] = OFF
            
            #advance to next step
            stepInSequence += 1
            if stepInSequence == len(sequence):
                # they won the sequence, make the game harder and play new seq out
                colorWipe(GREEN)
                seqLength += 1
                stepInSequence = 0
                ignoreGameButtons = True
                memoryGame()
        else:
            # they hit the wrong button, reset to begining of game
            # and restore normal button function
            colorWipe(RED)
            seqLength = 1
            for i in range(16):
                trellis.callbacks[i] = blink

#set up next level in memory game and enable user keypresses
def memoryGame():
    global sequence, stepInSequence, seqLength, ignoreGameButtons

    ignoreGameButtons = True
    
    #flash the lights
    colorWipe(BLUE)
    time.sleep(1)
    
    #generate random sequence 0..15 of buttons and colors
    sequence = []
    for i in range(seqLength):
        buttonNum = ord(os.urandom(1))%16
        buttonColor = colorSet[ord(os.urandom(1))%len(colorSet)]
        sequence.append((buttonNum, buttonColor))
        
    #play it out
    for i in sequence:
        trellis.pixels[i[0]] = i[1]
        time.sleep(1)
        trellis.pixels[i[0]] = OFF
        time.sleep(1)
        
    # switch button handlers to game input
    for i in range(16):
        trellis.callbacks[i] = memoryGameButtonEvent
    
    #indicate ready for input
    colorWipe(YELLOW)
    
    #enable buttons
    ignoreGameButtons = False
    
        
# example home automation rest api to toggle a switch
def toggleLamp(which):
    #get, among other things, the current on/off state
    response = requests.get(f'{REST_URL}/{which}')
    print(response.json()['state'])
    response.close()
    
    #send a command to flip the on/off state
    switchTo = 'OFF' if response.json()['state'] == 'ON' else 'ON'
    response = requests.post(f'{REST_URL}/{which}', headers=myHeaders, data=switchTo)
    print(response.status_code)
    print(response.text)
    response.close()

# helpful for debuggin use of rest api
def getStatus(which):
    response = requests.get(f'{REST_URL}/{which}')
    #print(response.status_code)
    print(response.json())
    response.close()

# example home automation rest api to up or down a dimmer
def dimmerChange(which, direction):
    # first get the current value of the dimmer
    response = requests.get(f'{REST_URL}/{which}')
    print(response.json()['state'])
    val = int(response.json()['state'])
    response.close()
    
    # now increment it or decrement it by the amount in 'direction'
    val += direction
    # keep it in the 0 to 100 range
    if val < 0:
        val = 0
    elif val > 100:
        val = 100
    
    # post the new value to the api
    changeTo = str(val)
    response = requests.post(f'{REST_URL}/{which}', headers=myHeaders, data=changeTo)
    print(response.status_code)
    print(response.text)
    response.close()

#example home automation rest api to turn a dimmer all the way up
def dimmerFull(which):
    #first turn the lamp on
    switchTo = 'ON'
    response = requests.post(f'{REST_URL}/{which}', headers=myHeaders, data=switchTo)
    print(response.status_code)
    print(response.text)
    response.close()

    #then set the dimmer val all the way up
    changeTo = '100'
    response = requests.post(f'{REST_URL}/{which}', headers=myHeaders, data=changeTo)
    print(response.status_code)
    print(response.text)
    response.close()

# this will be called when button events are received (when not in game mode)
def blink(event):
    global snakeActive
    # turn the LED on when a rising edge is detected
    if event.edge == NeoTrellis.EDGE_RISING:
        trellis.pixels[event.number] = CYAN
        print(f'Event number = {event.number}')
        #dispatch to button specific handlers
        if event.number == 0:
            toggleLamp(RIGHT_LAMP)
        if event.number == 1:
            toggleLamp(LEFT_LAMP)
        if event.number == 2:
            toggleLamp(BOTH_LAMPS)
        if event.number == 3:
            toggleLamp(TREE)
        if event.number == 4:
            toggleLamp(DINING_ROOM_LIGHTS)
        if event.number == 5:
            dimmerChange(DINING_ROOM_DIMMER, -5)
        if event.number == 6:
            dimmerChange(DINING_ROOM_DIMMER, 5)
        if event.number == 7:
            dimmerFull(DINING_ROOM_DIMMER)
        if event.number == 14:
            snakeActive = not snakeActive
            if not snakeActive:
                colorWipe(OFF)
        if event.number == 15:
            memoryGame()
            
    # turn the LED off when a falling edge is detected
    elif event.edge == NeoTrellis.EDGE_FALLING:
        trellis.pixels[event.number] = OFF


#setup the trellis
for i in range(16):
    # activate rising edge events on all keys
    trellis.activate_key(i, NeoTrellis.EDGE_RISING)
    # activate falling edge events on all keys
    trellis.activate_key(i, NeoTrellis.EDGE_FALLING)
    # set all keys to trigger the blink callback
    trellis.callbacks[i] = blink

#need to set up to do rest api calls
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

#flash a lot of colors to indicate all set up
colorWipe(RANDOM)

initSnake()

#loop infinitely waiting for button events
while True:
    # call the sync function call any triggered callbacks
    trellis.sync()
    # the trellis can only be read every 17 millisecons or so
    time.sleep(0.02)
    stepSnake() #actually only steps the snake when it is active





response = requests.post('http://192.168.1.53:8080/rest/items/LivingroomCouchRightOutlet_Switch', headers=myHeaders, data='OFF')
print(response.status_code)
print(response.text)
response.close()
time.sleep(3)
response = requests.post('http://192.168.1.53:8080/rest/items/LivingroomCouchRightOutlet_Switch', headers=myHeaders, data='ON')
print(response.status_code)
print(response.text)
response.close()
