"""
Xbox (or any SDL "game controller") input for the control panel.

Uses SDL's GameController API through pygame, so buttons and sticks have the same
names on Windows, macOS and Linux (A/B/X/Y, LEFTX, ...), whatever the raw indices are.
poll() must be called from the Tk main thread (root.after), never from a worker thread.
"""

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# The Tk window has focus, not pygame - keep receiving controller input anyway.
os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")

try:
    import pygame
    from pygame._sdl2 import controller
except ImportError:  # GUI still works without a controller
    pygame = None

DEADZONE = 0.15

if pygame:
    BUTTONS = {
        "A": pygame.CONTROLLER_BUTTON_A,
        "B": pygame.CONTROLLER_BUTTON_B,
        "X": pygame.CONTROLLER_BUTTON_X,
        "Y": pygame.CONTROLLER_BUTTON_Y,
        "LB": pygame.CONTROLLER_BUTTON_LEFTSHOULDER,
        "RB": pygame.CONTROLLER_BUTTON_RIGHTSHOULDER,
        "VIEW": pygame.CONTROLLER_BUTTON_BACK,
        "MENU": pygame.CONTROLLER_BUTTON_START,
        "LEFT": pygame.CONTROLLER_BUTTON_DPAD_LEFT,
        "RIGHT": pygame.CONTROLLER_BUTTON_DPAD_RIGHT,
        "UP": pygame.CONTROLLER_BUTTON_DPAD_UP,
        "DOWN": pygame.CONTROLLER_BUTTON_DPAD_DOWN,
    }
    AXES = {
        "LX": pygame.CONTROLLER_AXIS_LEFTX,
        "LY": pygame.CONTROLLER_AXIS_LEFTY,
        "RX": pygame.CONTROLLER_AXIS_RIGHTX,
        "RY": pygame.CONTROLLER_AXIS_RIGHTY,
        "LT": pygame.CONTROLLER_AXIS_TRIGGERLEFT,
        "RT": pygame.CONTROLLER_AXIS_TRIGGERRIGHT,
    }


def available():
    return pygame is not None


class Gamepad:
    def __init__(self):
        pygame.init()
        controller.init()
        self.pad = None
        self._held = set()

    @property
    def name(self):
        return self.pad.name if self.pad else None

    def poll(self):
        """Returns (axes, pressed): axes in -1..1 with deadzone applied (triggers 0..1),
        pressed = buttons that went down since the last poll."""
        pygame.event.pump()
        self._attach()
        if not self.pad:
            self._held.clear()
            return {}, set()

        try:
            axes = {}
            for name, idx in AXES.items():
                v = self.pad.get_axis(idx) / 32767.0
                axes[name] = 0.0 if abs(v) < DEADZONE else max(-1.0, min(1.0, v))
            held = {name for name, idx in BUTTONS.items() if self.pad.get_button(idx)}
        except pygame.error:  # unplugged
            self.pad = None
            return {}, set()

        pressed = held - self._held
        self._held = held
        return axes, pressed

    def _attach(self):
        if self.pad and self.pad.attached():
            return
        self.pad = None
        for i in range(controller.get_count()):
            if controller.is_controller(i):
                self.pad = controller.Controller(i)
                return
