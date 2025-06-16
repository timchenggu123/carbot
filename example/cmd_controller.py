#!/usr/bin/env python3

from robot_hat.utils import reset_mcu
from driver.picarx import Picarx
from robot_hat import Music,TTS
from vilib import Vilib
from time import sleep, time, strftime, localtime
import termios, tty, fcntl, os, sys, select
from inputs import get_key

import os
user = os.getlogin()
user_home = os.path.expanduser(f'~{user}')

reset_mcu()
sleep(0.2)

px = Picarx()
music = Music()
music.music_set_volume(20)
tts = TTS()

# Setup: non-blocking stdin
fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)
tty.setcbreak(fd)  # raw-like mode
fcntl_old = fcntl.fcntl(fd, fcntl.F_GETFL)
fcntl.fcntl(fd, fcntl.F_SETFL, fcntl_old | os.O_NONBLOCK)

def flush_stdin():
    while True:
        r, _, _ = select.select([sys.stdin], [], [], 0)
        if r:
            try:
                os.read(sys.stdin.fileno(), 4096)  # discard buffered input
            except OSError:
                break
        else:
            break

KEY_MAP = {
    'w': 'forward',
    's': 'backward',
    'a': 'left',
    'd': 'right',
    'f': 'stop',
    'k': 'look_up',
    'j': 'look_down',
    'l': 'look_right',
    'h': 'look_left',
    'o': 'center',
    "t": 'hi'
}

manual = 'Press key to call the function (non-case sensitive)'
for k, v in KEY_MAP.items():
    manual += f"\n{k}:{v}"

def main(px):

    Vilib.camera_start(vflip=False,hflip=False)
    Vilib.display(local=True,web=True)
    sleep(2)  # wait for startup
    print(manual)
    
    tts.lang("en-US")

    run = True
    while run:
        flush_stdin()
        sleep(0.10)
        c = sys.stdin.read(1).lower()
        if c in KEY_MAP:
            cmd = KEY_MAP[c]
            if cmd == "forward":
                px.accelerate(10)
                # print("forward")
            if cmd == "backward":
                px.accelerate(-30)
                # print("backward")
            if cmd == "right":
                px.turn(5)
                px.accelerate(10)
                # print("right")
            if cmd == "left":
                px.turn(-5)
                px.accelerate(10)
                # print("left")
            if cmd == "stop":
                print("stop")
                px.stop()
                continue
            if cmd == "look_up":
                px.tilt_up()
            if cmd == "look_down":
                px.tilt_down()
            if cmd == "look_right":
                px.pan_right()
            if cmd == "look_left":
                px.pan_left()
            if cmd == 'center':
                px.pan_angle = 0
                px.tilt_angle = 0
            if cmd == "hi":
                tts.say("Hello!")
        else:
            px.stop()
            if px.dir_current_angle > 0:
                px.turn(max(-10, 0 - px.dir_current_angle))
            elif px.dir_current_angle < 0:
                px.turn(min(10, 0 - px.dir_current_angle)) 
        px.update_motor()
        px.update_pan()
        px.update_tilt()


if __name__ == "__main__":

    try:
        main(px)
    except Exception as e:    
        print("error:%s"%e)
    finally:
        px.stop()
        Vilib.camera_close()


        