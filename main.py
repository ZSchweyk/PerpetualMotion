# ////////////////////////////////////////////////////////////////
# //                     IMPORT STATEMENTS                      //
# ////////////////////////////////////////////////////////////////

import math
import sys
import time
from threading import Thread

from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ObjectProperty
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import *
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.slider import Slider
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.animation import Animation
from functools import partial
from kivy.config import Config
from kivy.core.window import Window
from pidev.kivy import DPEAButton
from pidev.kivy import PauseScreen
from time import sleep
import RPi.GPIO as GPIO
from pidev.stepper import stepper
from pidev.Cyprus_Commands import Cyprus_Commands_RPi as cyprus

# ////////////////////////////////////////////////////////////////
# //                      GLOBAL VARIABLES                      //
# //                         CONSTANTS                          //
# ////////////////////////////////////////////////////////////////
ON = False
OFF = True
HOME = True
TOP = False
OPEN = False
CLOSE = True
YELLOW = .180, 0.188, 0.980, 1
BLUE = 0.917, 0.796, 0.380, 1
DEBOUNCE = 0.1
INIT_RAMP_SPEED = 150
RAMP_LENGTH = 725


# ////////////////////////////////////////////////////////////////
# //            DECLARE APP CLASS AND SCREENMANAGER             //
# //                     LOAD KIVY FILE                         //
# ////////////////////////////////////////////////////////////////
class MyApp(App):
    def build(self):
        self.title = "Perpetual Motion"
        return sm


Builder.load_file('main.kv')
Window.clearcolor = (.1, .1, .1, 1)  # (WHITE)

cyprus.open_spi()

# ////////////////////////////////////////////////////////////////
# //                    SLUSH/HARDWARE SETUP                    //
# ////////////////////////////////////////////////////////////////
sm = ScreenManager()
ramp = stepper(port=0, speed=INIT_RAMP_SPEED)


# ////////////////////////////////////////////////////////////////
# //                       MAIN FUNCTIONS                       //
# //             SHOULD INTERACT DIRECTLY WITH HARDWARE         //
# ////////////////////////////////////////////////////////////////

# ////////////////////////////////////////////////////////////////
# //        DEFINE MAINSCREEN CLASS THAT KIVY RECOGNIZES        //
# //                                                            //
# //   KIVY UI CAN INTERACT DIRECTLY W/ THE FUNCTIONS DEFINED   //
# //     CORRESPONDS TO BUTTON/SLIDER/WIDGET "on_release"       //
# //                                                            //
# //   SHOULD REFERENCE MAIN FUNCTIONS WITHIN THESE FUNCTIONS   //
# //      SHOULD NOT INTERACT DIRECTLY WITH THE HARDWARE        //
# ////////////////////////////////////////////////////////////////
class MainScreen(Screen):
    version = cyprus.read_firmware_version()
    staircaseSpeedText = '0'
    rampSpeed = INIT_RAMP_SPEED
    staircaseSpeed = 40

    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.initialize()

        # Cyprus Stairs
        self.cyprus_stairs = cyprus
        self.cyprus_stairs.initialize()
        self.cyprus_stairs.setup_servo(1)

        self.staircase_status = False
        staircase = ObjectProperty(None)
        staircaseSpeed = ObjectProperty(None)

        # Stepper Ramp
        self.m0 = stepper(port=0, micro_steps=32, hold_current=20, run_current=20, accel_current=20, deaccel_current=20,
                          steps_per_unit=200, speed=2)
        self.m0_speed = lambda speed: (speed / 100) * (self.m0.speed / self.m0.steps_per_unit)
        self.initial_stepper_position = 0
        self.last_stepper_closed_position = self.initial_stepper_position

        ramp = ObjectProperty(None)
        rampSpeed = ObjectProperty(None)

        # Servo Gate
        gate = ObjectProperty(None)
        self.servo_gate = cyprus
        self.servo_gate.initialize()
        self.servo_gate.setup_servo(2)
        self.initial_servo_position = 0
        self.servo_gate.set_servo_position(2, self.initial_servo_position)
        self.last_servo_closed_position = self.initial_servo_position

        self.servo_gate.set_servo_position(2, self.initial_servo_position)

    @staticmethod
    def is_port_on(port):
        check_bin = None
        if port == 6:
            check_bin = 0b0001
        elif port == 7:
            check_bin = 0b0010
        elif port == 8:
            check_bin = 0b0100
        elif port == 9:
            check_bin = 0b1000

        if not cyprus.read_gpio() & check_bin:
            return True
        else:
            return False

    def toggleGate(self):
        if self.gate.text == "Open Gate":
            self.servo_gate.set_servo_position(2, .475)
            self.gate.text = "Close Gate"
        else:
            if self.last_servo_closed_position == 0:
                self.last_servo_closed_position = 1
            else:
                self.last_servo_closed_position = 0
            self.servo_gate.set_servo_position(2, self.last_servo_closed_position)
            self.gate.text = "Open Gate"

    def toggleStaircase(self):
        if self.staircase_status:
            self.staircase_status = False
            self.staircase.text = "Staircase On"
            self.staircaseSpeed.disabled = True
        else:
            self.staircase_status = True
            self.staircase.text = "Staircase Off"
            self.staircaseSpeed.disabled = False
        self.setStaircaseSpeed()

    def toggleRamp(self):
        self.ramp.disabled = True
        thread = None
        if self.last_stepper_closed_position == 0:
            thread = Thread(target=lambda: self.move_stepper_motor("up"))
            self.ramp.text = "Ramp to Bottom"
            self.last_stepper_closed_position = 29
        elif self.last_stepper_closed_position == 29:
            thread = Thread(target=lambda: self.move_stepper_motor("down"))
            self.ramp.text = "Ramp to Top"
            self.last_stepper_closed_position = 0
        self.ramp.disabled = False
        thread.start()

    def move_stepper_motor(self, direction):
        port = None
        if direction == "up":
            self.m0.start_relative_move(29)
            port = 6
            # while not self.is_port_on(6):
            #     self.m0.start_relative_move(.1)
        elif direction == "down":
            self.m0.start_relative_move(-29)
            port = 8

        while True:
            if self.is_port_on(port):
                self.m0.hardStop()
                break
            sleep(.05)

    def auto(self):
        pass

    def setRampSpeed(self):
        self.m0.hard_stop()
        self.m0.set_speed(self.m0_speed(self.rampSpeed.value))
        return self.m0_speed(self.rampSpeed.value)

    def setStaircaseSpeed(self):
        if self.staircase_status:

            self.cyprus_stairs.set_pwm_values(1, period_value=100000,
                                              compare_value=float(self.staircaseSpeed.value) * 1000,
                                              compare_mode=self.cyprus_stairs.LESS_THAN_OR_EQUAL)
            self.staircaseSpeed.text = str(self.staircaseSpeed.value)
        else:
            self.cyprus_stairs.set_pwm_values(1, period_value=100000, compare_value=0,
                                              compare_mode=self.cyprus_stairs.LESS_THAN_OR_EQUAL)

    def initialize(self):
        pass

    def resetColors(self):
        self.ids.gate.color = YELLOW
        self.ids.staircase.color = YELLOW
        self.ids.ramp.color = YELLOW
        self.ids.auto.color = BLUE

    def quit(self):
        self.servo_gate.set_servo_position(2, self.initial_servo_position)
        self.move_stepper_motor("down")
        MyApp().stop()


sm.add_widget(MainScreen(name='main'))

# ////////////////////////////////////////////////////////////////
# //                          RUN APP                           //
# ////////////////////////////////////////////////////////////////

MyApp().run()
cyprus.close_spi()
