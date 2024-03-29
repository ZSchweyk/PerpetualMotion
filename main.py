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
# ramp = stepper(port=0, speed=INIT_RAMP_SPEED)


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
    # rampSpeed = INIT_RAMP_SPEED
    # staircaseSpeed = 40
    staircaseSpeed = ObjectProperty(None)
    staircase = ObjectProperty(None)
    ramp = ObjectProperty(None)
    rampSpeed = ObjectProperty(None)
    gate = ObjectProperty(None)
    auto = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)

        cyprus.initialize()

        # Cyprus Stairs
        self.cyprus_stairs = cyprus

        # Stepper Ramp
        self.m0 = stepper(port=0, micro_steps=32, hold_current=20, run_current=20, accel_current=20, deaccel_current=20,
                          steps_per_unit=200, speed=2)

        # Servo Gate
        self.servo_gate = cyprus
        self.servo_gate.setup_servo(2)

        # Set everything to default positions.
        self.initialize(True)


    def switch_m0_direction(self):
        self.m0_direction = 1 - self.m0_direction

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

    def toggleRampThread(self):
        Thread(target=self.toggleRamp).start()

    def toggleRamp(self):
        self.ramp.disabled = True
        if self.m0_direction == 1:
            self.m0.relative_move(1)
        # print("Ramp Speed: ", 6400 * self.rampSpeed.value)
        self.m0.go_until_press(self.m0_direction, 6400 * self.rampSpeed.value)

        if self.m0_direction == 1:
            self.ramp.text = "Ramp to Bottom"
            while True:
                if self.is_port_on(6):
                    self.m0.hardStop()
                    break
                sleep(.05)
        else:
            self.ramp.text = "Ramp to Top"

        self.switch_m0_direction()
        # print("Switched m0 direction to ", self.m0_direction)
        self.ramp.disabled = False
        return

    def automatic_loop(self):
        print("self.initialize()")
        self.initialize(False)
        self.toggleRamp()
        print("self.toggleRamp()")
        self.toggleRampThread()
        print("self.toggleRampThread()")
        self.staircaseSpeed.value = 50
        self.toggleStaircase()
        print("self.toggleStaircase()")
        sleep(15)
        print("sleep(15)")
        self.toggleStaircase()
        print("self.toggleStaircase()")
        self.toggleGate()
        print("self.toggleGate()")
        sleep(2)
        print("sleep(2)")
        self.toggleGate()
        self.toggleGate()
        self.toggleGate()
        print("self.toggleGate()")



        all_btns_and_sliders = [self.auto, self.gate, self.ramp, self.rampSpeed, self.staircase, self.staircaseSpeed]
        for elem in all_btns_and_sliders:
            elem.disabled = False

        return


    def setRampSpeed(self):
        self.m0.hard_stop()
        self.m0.set_speed(self.m0_speed(self.rampSpeed.value))

        # return self.m0_speed(self.rampSpeed.value)

    def setStaircaseSpeed(self):
        if self.staircase_status:
            self.cyprus_stairs.set_pwm_values(1, period_value=100000,
                                              compare_value=float(self.staircaseSpeed.value) * 1000,
                                              compare_mode=self.cyprus_stairs.LESS_THAN_OR_EQUAL)
            self.staircaseSpeed.text = str(self.staircaseSpeed.value)
        else:
            self.cyprus_stairs.set_pwm_values(1, period_value=100000, compare_value=0,
                                              compare_mode=self.cyprus_stairs.LESS_THAN_OR_EQUAL)

    def initialize(self, on_thread):
        self.initial_servo_position = 0
        self.servo_gate.set_servo_position(2, self.initial_servo_position)
        self.last_servo_closed_position = self.initial_servo_position
        print("\tInitialized Gate")

        self.m0_speed = lambda speed: (speed / 100) * (self.m0.speed / self.m0.steps_per_unit)
        self.m0_direction = 0
        if on_thread:
            self.toggleRampThread()
        else:
            self.toggleRamp()
        print("\tInitialized Ramp")

        self.staircase_status = False
        # self.toggleStaircase()
        # self.setStaircaseSpeed()
        print("\tInitialized Stairs")

    def resetColors(self):
        self.ids.gate.color = YELLOW
        self.ids.staircase.color = YELLOW
        self.ids.ramp.color = YELLOW
        self.ids.auto.color = BLUE

    @staticmethod
    def quit():
        # self.m0.hardStop()
        # self.cyprus_stairs.close()
        MyApp().stop()


sm.add_widget(MainScreen(name='main'))

# ////////////////////////////////////////////////////////////////
# //                          RUN APP                           //
# ////////////////////////////////////////////////////////////////

MyApp().run()
cyprus.close_spi()
