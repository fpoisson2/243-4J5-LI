#!/usr/bin/env python3
"""
PiWare — Retro arcade microgame collection for ESP32 + Raspberry Pi.

Hardware: 2 buttons, 2 potentiometers, 3 LEDs on ESP32 (Lilygo T-SIM7670E)
Display:  720x1280 portrait touchscreen on Raspberry Pi 5
Touch:    evdev (/dev/input)
Render:   SDL2 kmsdrm (headless, no X11)

Communication modes (selected from in-game menu):
  - Serial USB  (reuses testscreen_serial ESP32 sketch)
  - MQTT WiFi   (reuses testscreen_mqtt_wifi ESP32 sketch)
  - MQTT LTE    (reuses testscreen_mqtt ESP32 sketch)

Usage (from SSH):
  sudo python3 game.py [--port /dev/ttyACM0]
"""

import os
import sys
import abc
import json
import math
import time
import random
import argparse
import threading

# Configure SDL for framebuffer before importing pygame
os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
os.environ.setdefault("SDL_FBDEV", "/dev/fb0")

import pygame
from evdev import InputDevice, ecodes, list_devices

# ═══════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════
SCREEN_W, SCREEN_H = 720, 1280
PIXEL_SCALE = 3
VIRT_W, VIRT_H = SCREEN_W // PIXEL_SCALE, SCREEN_H // PIXEL_SCALE  # 240x426
FPS = 30
HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "highscores.json")

# ── Retro Arcade Palette ─────────────────────────────────
BG          = (5, 5, 15)
WHITE       = (255, 255, 255)
BLACK       = (0, 0, 0)
GREY        = (120, 120, 120)
DARK_GREY   = (35, 35, 50)
RED         = (255, 50, 50)
GREEN       = (50, 255, 100)
BLUE        = (50, 120, 255)
YELLOW      = (255, 255, 50)
ORANGE      = (255, 160, 30)
PURPLE      = (180, 50, 255)
CYAN        = (0, 255, 230)
PINK        = (255, 50, 180)
NEON_GREEN  = (57, 255, 20)
NEON_BLUE   = (77, 77, 255)
MENU_BG     = (5, 5, 20)


# ═══════════════════════════════════════════════════════════
#  HARDWARE STATE
# ═══════════════════════════════════════════════════════════
class HardwareState:
    """Thread-safe container for ESP32 sensor readings."""
    def __init__(self):
        self.btn1 = False
        self.btn2 = False
        self.pot1 = 0
        self.pot2 = 0
        self.led_r = False
        self.led_g = False
        self.led_b = False
        self.connected = False
        # Rising-edge press counters (incremented by comm thread)
        self.btn1_presses = 0
        self.btn2_presses = 0
        self._prev_btn1 = False
        self._prev_btn2 = False
        self.lock = threading.Lock()

    def _detect_edges(self):
        """Call inside lock after updating btn1/btn2 to count state changes."""
        if self.btn1 != self._prev_btn1:
            self.btn1_presses += 1
        if self.btn2 != self._prev_btn2:
            self.btn2_presses += 1
        self._prev_btn1 = self.btn1
        self._prev_btn2 = self.btn2

    def snapshot(self):
        with self.lock:
            return {
                "btn1": self.btn1, "btn2": self.btn2,
                "pot1": self.pot1, "pot2": self.pot2,
                "led_r": self.led_r, "led_g": self.led_g, "led_b": self.led_b,
                "connected": self.connected,
                "btn1_presses": self.btn1_presses,
                "btn2_presses": self.btn2_presses,
            }

    def reset_press_count(self, btn):
        """Reset a button's press counter (call when starting a mash game)."""
        with self.lock:
            if btn == 1:
                self.btn1_presses = 0
            else:
                self.btn2_presses = 0


# ═══════════════════════════════════════════════════════════
#  COMMUNICATION BACKENDS
# ═══════════════════════════════════════════════════════════
class CommBackend(abc.ABC):
    def __init__(self, state):
        self.state = state

    @abc.abstractmethod
    def start(self): ...

    @abc.abstractmethod
    def set_led(self, color, on): ...

    @abc.abstractmethod
    def stop(self): ...


class SerialBackend(CommBackend):
    """Serial USB communication (toggle-based LED protocol)."""
    def __init__(self, state, port="/dev/ttyACM0"):
        super().__init__(state)
        self.port = port
        self.ser = None

    def start(self):
        import serial as _serial
        self._serial_mod = _serial
        t = threading.Thread(target=self._read_loop, daemon=True)
        t.start()

    def _read_loop(self):
        while True:
            try:
                self.ser = self._serial_mod.Serial(self.port, 115200, timeout=1)
                while True:
                    line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                    if line.startswith("S,"):
                        parts = line[2:].split(",")
                        if len(parts) == 7:
                            with self.state.lock:
                                self.state.btn1  = parts[0] == "1"
                                self.state.btn2  = parts[1] == "1"
                                self.state.pot1  = int(parts[2])
                                self.state.pot2  = int(parts[3])
                                self.state.led_r = parts[4] == "1"
                                self.state.led_g = parts[5] == "1"
                                self.state.led_b = parts[6] == "1"
                                self.state.connected = True
                                self.state._detect_edges()
            except Exception:
                with self.state.lock:
                    self.state.connected = False
                self.ser = None
                time.sleep(2)

    def set_led(self, color, on):
        """Toggle LED only if current state differs from desired state."""
        if not self.ser:
            return
        key = {"r": "led_r", "g": "led_g", "b": "led_b"}[color]
        current = getattr(self.state, key)
        if current != on:
            cmd = color.upper()
            try:
                self.ser.write(cmd.encode())
            except Exception:
                pass

    def stop(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass


class MQTTBackend(CommBackend):
    """MQTT communication (WSS, works for both WiFi and LTE ESP32 modes)."""
    def __init__(self, state):
        super().__init__(state)
        self.mqtt = None

    def _load_mqtt_config(self):
        """Import MQTT_CONFIG from adjacent project folders."""
        import importlib.util
        script_dir = os.path.dirname(os.path.abspath(__file__))
        for subdir in [".", "..", "../testscreen_mqtt", "../testscreen_mqtt_wifi"]:
            cfg_path = os.path.join(script_dir, subdir, "mqtt_config.py")
            if os.path.exists(cfg_path):
                spec = importlib.util.spec_from_file_location("mqtt_config", cfg_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod.MQTT_CONFIG
        raise FileNotFoundError(
            "mqtt_config.py not found.  Copy it from testscreen_mqtt/."
        )

    def start(self):
        import paho.mqtt.client as paho_mqtt
        import ssl

        cfg = self._load_mqtt_config()
        self.device_id = cfg["device_id"]
        self.status_topic = f"{self.device_id}/testscreen/status"
        self.led_topics = {
            "r": f"{self.device_id}/testscreen/led/red",
            "g": f"{self.device_id}/testscreen/led/green",
            "b": f"{self.device_id}/testscreen/led/blue",
        }

        client_id = f"pi-piware-{int(time.time())}"
        self.mqtt = paho_mqtt.Client(client_id=client_id, transport="websockets")
        self.mqtt.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
        self.mqtt.username_pw_set(cfg["username"], cfg["password"])

        def on_connect(client, _ud, _flags, rc):
            if rc == 0:
                client.subscribe(self.status_topic)
                print(f"[MQTT] Subscribed to {self.status_topic}")

        def on_message(_client, _ud, msg):
            try:
                data = json.loads(msg.payload.decode())
                with self.state.lock:
                    self.state.btn1  = bool(data.get("btn1", 0))
                    self.state.btn2  = bool(data.get("btn2", 0))
                    self.state.pot1  = int(data.get("pot1", 0))
                    self.state.pot2  = int(data.get("pot2", 0))
                    self.state.led_r = bool(data.get("ledR", 0))
                    self.state.led_g = bool(data.get("ledG", 0))
                    self.state.led_b = bool(data.get("ledB", 0))
                    self.state.connected = True
                    self.state._detect_edges()
            except Exception:
                pass

        self.mqtt.on_connect = on_connect
        self.mqtt.on_message = on_message
        self.mqtt.connect(cfg["broker"], cfg["port"], 60)
        self.mqtt.loop_start()

    def set_led(self, color, on):
        if self.mqtt:
            topic = self.led_topics.get(color)
            if topic:
                self.mqtt.publish(topic, "ON" if on else "OFF")

    def stop(self):
        if self.mqtt:
            self.mqtt.loop_stop()
            self.mqtt.disconnect()


# ═══════════════════════════════════════════════════════════
#  TOUCH INPUT
# ═══════════════════════════════════════════════════════════
def find_touch_device():
    for path in list_devices():
        dev = InputDevice(path)
        if "touch" in dev.name.lower() or "ft5406" in dev.name.lower():
            return dev
    return None


def touch_reader(dev, queue):
    x, y = 0, 0
    for ev in dev.read_loop():
        if ev.type == ecodes.EV_ABS:
            if ev.code in (ecodes.ABS_MT_POSITION_X, ecodes.ABS_X):
                x = ev.value
            elif ev.code in (ecodes.ABS_MT_POSITION_Y, ecodes.ABS_Y):
                y = ev.value
        elif (ev.type == ecodes.EV_KEY
              and ev.code == ecodes.BTN_TOUCH
              and ev.value == 1):
            queue.append((x, y))


# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════
def draw_rounded_rect(surface, colour, rect, radius=4):
    pygame.draw.rect(surface, colour, rect, border_radius=radius)


def draw_pixel_border(surface, rect, color, thickness=1):
    """Draw a retro pixel-style border."""
    pygame.draw.rect(surface, color, rect, width=thickness)


def draw_glow_text(surface, text, font, color, pos, glow_color=None, glow_radius=1):
    """Render text with a subtle pixel glow (1px offset)."""
    if glow_color is None:
        glow_color = tuple(min(255, c // 2 + 30) for c in color)
    if glow_radius >= 1:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                glow = font.render(text, False, glow_color)
                glow.set_alpha(80)
                surface.blit(glow, (pos[0] + dx, pos[1] + dy))
    txt = font.render(text, False, color)
    surface.blit(txt, pos)


# ── High scores ──────────────────────────────────────────
def load_highscores():
    """Load top 5 high scores from disk."""
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            data = json.load(f)
            return data.get("scores", [])[:5]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_highscores(scores):
    """Save top 5 high scores to disk."""
    scores = sorted(scores, reverse=True)[:5]
    with open(HIGHSCORE_FILE, "w") as f:
        json.dump({"scores": scores}, f)


def is_highscore(score):
    """Check if score qualifies as a new high score."""
    scores = load_highscores()
    return len(scores) < 5 or score > min(scores)


# ═══════════════════════════════════════════════════════════
#  MICROGAMES
# ═══════════════════════════════════════════════════════════
class MicroGame(abc.ABC):
    """Base class for all microgames."""
    name = ""
    hint = ""         # shown below name on instruction screen (e.g. "B1 + B2")
    base_duration = 4.0
    game_type = "action"    # "action" = win early, "survive" = don't fail
    wave_based = False      # True = no timer, game ends when update() returns
    bg_color = BG
    RESULT_DURATION = 0.7   # seconds for result animation

    def reset(self, snap=None, speed_mult=1.0):
        """Called when microgame starts.  Override for randomisation."""
        pass

    @abc.abstractmethod
    def update(self, snap, dt):
        """Return True=win, False=lose, None=ongoing."""
        ...

    @abc.abstractmethod
    def draw(self, screen, snap, time_left, time_total, fonts):
        """Render the microgame (timer/HUD drawn by engine)."""
        ...

    def animate_result(self, screen, won, t, fonts):
        """Per-game win/lose animation.  t = seconds since result (0..~0.7).
        Override for custom animations.  Default: simple text."""
        cx, cy = VIRT_W // 2, VIRT_H // 2
        if won:
            draw_glow_text(screen, "OK!", fonts["giant"], GREEN,
                           (cx - fonts["giant"].size("OK!")[0] // 2, cy - 16),
                           (0, 100, 0))
        else:
            draw_glow_text(screen, "NO!", fonts["giant"], RED,
                           (cx - fonts["giant"].size("NO!")[0] // 2, cy - 16),
                           (100, 0, 0))


# ── 1. Press a specific button ────────────────────────────
class PressButtonGame(MicroGame):
    name = "PRESS!"
    base_duration = 3.5
    game_type = "action"

    def reset(self, snap=None, speed_mult=1.0):
        self.target = random.choice([1, 2])
        self.bg_color = (20, 30, 50) if self.target == 1 else (50, 20, 30)
        self.arrow_phase = 0.0
        self.hint = f"B{self.target}"

    def update(self, snap, dt):
        if snap[f"btn{self.target}"]:
            return True
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2 - 20
        self.arrow_phase += 0.2

        # Bouncing arrow pointing at button
        bounce = int(math.sin(self.arrow_phase * 3) * 5)
        arrow_y = cy - 20 + bounce
        pygame.draw.polygon(screen, YELLOW, [
            (cx, arrow_y + 15), (cx - 12, arrow_y), (cx - 5, arrow_y),
            (cx - 5, arrow_y - 12), (cx + 5, arrow_y - 12),
            (cx + 5, arrow_y), (cx + 12, arrow_y),
        ])

        pressed = snap[f"btn{self.target}"]
        btn_y = cy + 30
        # Pulsing glow ring
        glow_r = 33 + int(abs(math.sin(time.time() * 5)) * 5)
        pygame.draw.circle(screen, (YELLOW[0] // 4, YELLOW[1] // 4, YELLOW[2] // 4),
                           (cx, btn_y), glow_r)
        btn_color = NEON_GREEN if pressed else YELLOW
        pygame.draw.circle(screen, btn_color, (cx, btn_y), 30)
        pygame.draw.circle(screen, WHITE, (cx, btn_y), 30, 1)
        num = fonts["giant"].render(str(self.target), False, BLACK)
        screen.blit(num, (cx - num.get_width() // 2,
                          btn_y - num.get_height() // 2))
        lbl = fonts["big"].render(f"BTN {self.target}", False, WHITE)
        screen.blit(lbl, (cx - lbl.get_width() // 2, 22))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2 + 10
        if won:
            # Button launches up like a spring
            fly_y = cy - int(t * 300)
            r = max(5, 30 - int(t * 20))
            pygame.draw.circle(screen, NEON_GREEN, (cx, fly_y), r)
            # Trail of sparkles
            for i in range(6):
                sy = fly_y + 10 + i * 12
                if sy < VIRT_H:
                    sc = random.choice([YELLOW, GREEN, CYAN])
                    pygame.draw.rect(screen, sc,
                                     (cx + random.randint(-8, 8), sy, 2, 2))
            txt = fonts["huge"].render("NICE!", False, NEON_GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, VIRT_H // 2 + 30))
        else:
            # Button crumbles
            for i in range(15):
                bx = cx + random.randint(-25, 25)
                by = cy + int(t * 80) + random.randint(-10, 20)
                sz = random.randint(1, 4)
                pygame.draw.rect(screen, GREY, (bx, by, sz, sz))
            txt = fonts["huge"].render("MISS!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 40))


# ── 2. Press both buttons ────────────────────────────────
class PressBothGame(MicroGame):
    name = "SMASH!"
    hint = "B1 + B2"
    base_duration = 3.5
    game_type = "action"
    bg_color = (15, 10, 30)

    def reset(self, snap=None, speed_mult=1.0):
        self.sparks = []
        self.flash_timer = 0
        self.l_pos = 30.0
        self.r_pos = float(VIRT_W - 30)
        self.collided_timer = 0.0  # time both buttons held

    def update(self, snap, dt):
        if snap["btn1"] and snap["btn2"]:
            self.collided_timer += dt
            # Let fists visually slam together before winning
            if self.collided_timer >= 0.25:
                return True
        else:
            self.collided_timer = 0.0
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2

        b1 = snap["btn1"]
        b2 = snap["btn2"]
        # Smooth lerp towards target positions
        l_target = float(cx - 22) if b1 else 30.0
        r_target = float(cx + 22) if b2 else float(VIRT_W - 30)
        lerp_speed = 0.25
        self.l_pos += (l_target - self.l_pos) * lerp_speed
        self.r_pos += (r_target - self.r_pos) * lerp_speed
        l_x = int(self.l_pos)
        r_x = int(self.r_pos)

        # Left fist (square pixel fist)
        lc = NEON_GREEN if b1 else ORANGE
        pygame.draw.rect(screen, lc, (l_x - 14, cy - 10, 14, 22))
        pygame.draw.rect(screen, lc, (l_x - 18, cy - 6, 6, 14))
        pygame.draw.rect(screen, WHITE, (l_x - 14, cy - 10, 14, 22), 1)
        lbl1 = fonts["big"].render("1", False, BLACK)
        screen.blit(lbl1, (l_x - 12, cy - 6))

        # Right fist
        rc = NEON_GREEN if b2 else ORANGE
        pygame.draw.rect(screen, rc, (r_x, cy - 10, 14, 22))
        pygame.draw.rect(screen, rc, (r_x + 12, cy - 6, 6, 14))
        pygame.draw.rect(screen, WHITE, (r_x, cy - 10, 14, 22), 1)
        lbl2 = fonts["big"].render("2", False, BLACK)
        screen.blit(lbl2, (r_x + 2, cy - 6))

        # Impact sparks when both pressed
        if b1 and b2:
            for _ in range(4):
                self.sparks.append([cx + random.randint(-8, 8),
                                    cy + random.randint(-12, 12),
                                    random.randint(3, 7),
                                    random.choice([YELLOW, WHITE, ORANGE])])
        new_s = []
        for s in self.sparks:
            s[0] += random.uniform(-2, 2)
            s[1] += random.uniform(-2, 2)
            s[2] -= 1
            if s[2] > 0:
                pygame.draw.rect(screen, s[3], (int(s[0]), int(s[1]), 2, 2))
                new_s.append(s)
        self.sparks = new_s[-30:]

        # "VS" in the middle
        vs = fonts["big"].render("VS", False, YELLOW)
        screen.blit(vs, (cx - vs.get_width() // 2, cy + 30))

        # Button labels at top
        t1c = NEON_GREEN if b1 else GREY
        t2c = NEON_GREEN if b2 else GREY
        l1 = fonts["big"].render("BTN 1", False, t1c)
        l2 = fonts["big"].render("BTN 2", False, t2c)
        screen.blit(l1, (25, 22))
        screen.blit(l2, (VIRT_W - 25 - l2.get_width(), 22))
        plus = fonts["huge"].render("+", False, YELLOW)
        screen.blit(plus, (cx - plus.get_width() // 2, 20))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        if won:
            # Fists collide — shockwave expanding outward
            wave_r = int(t * 200)
            for ring in range(3):
                r = wave_r - ring * 15
                if r > 0:
                    alpha_pct = max(0, 1.0 - r / 120)
                    c = (int(255 * alpha_pct), int(200 * alpha_pct), 0)
                    pygame.draw.circle(screen, c, (cx, cy), r, 2)
            # Impact sparks
            for _ in range(8):
                angle = random.uniform(0, math.pi * 2)
                dist = t * random.uniform(40, 120)
                px = cx + int(math.cos(angle) * dist)
                py = cy + int(math.sin(angle) * dist)
                pygame.draw.rect(screen, random.choice([YELLOW, WHITE, ORANGE]),
                                 (px, py, 2, 2))
            txt = fonts["huge"].render("BOOM!", False, YELLOW)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 15))
        else:
            # Fists slide away to opposite sides
            l_x = int(30 - t * 100)
            r_x = int(VIRT_W - 30 + t * 100)
            pygame.draw.rect(screen, ORANGE, (l_x - 14, cy - 10, 14, 22))
            pygame.draw.rect(screen, ORANGE, (r_x, cy - 10, 14, 22))
            txt = fonts["huge"].render("WEAK!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 15))


# ── 3. Don't touch anything ──────────────────────────────
class DontTouchGame(MicroGame):
    name = "FREEZE!"
    hint = "NOTHING!"
    base_duration = 3.0
    game_type = "survive"
    bg_color = (8, 8, 25)

    def reset(self, snap=None, speed_mult=1.0):
        self.grace = 0.35
        self.initial_pot1 = snap["pot1"] if snap else None
        self.initial_pot2 = snap["pot2"] if snap else None
        self.pot_margin = 25
        self.ice = [(random.randint(0, VIRT_W), random.randint(0, VIRT_H),
                     random.uniform(0.2, 1.0)) for _ in range(30)]
        self.frost_phase = 0

    def update(self, snap, dt):
        if self.grace > 0:
            self.grace -= dt
            return None
        if snap["btn1"] or snap["btn2"]:
            return False
        if self.initial_pot1 is not None:
            if abs(snap["pot1"] - self.initial_pot1) > self.pot_margin:
                return False
            if abs(snap["pot2"] - self.initial_pot2) > self.pot_margin:
                return False
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        self.frost_phase += 0.05

        # Falling ice crystals
        for i, (ix, iy, spd) in enumerate(self.ice):
            iy += spd
            ix += math.sin(self.frost_phase + i) * 0.3
            if iy > VIRT_H:
                iy = -5
                ix = random.randint(0, VIRT_W)
            self.ice[i] = (ix, iy, spd)
            # Tiny snowflake shape
            px, py = int(ix), int(iy)
            c = (150, 200, 255)
            pygame.draw.rect(screen, c, (px, py, 1, 1))
            pygame.draw.rect(screen, c, (px - 1, py, 1, 1))
            pygame.draw.rect(screen, c, (px + 1, py, 1, 1))

        # Frozen character in center
        pulse = abs(math.sin(time.time() * 3))
        # Ice block
        ice_c = (100, 180, 255)
        block_w, block_h = 38, 50
        bx = cx - block_w // 2
        by = cy - block_h // 2
        pygame.draw.rect(screen, (40, 80, 140), (bx, by, block_w, block_h))
        pygame.draw.rect(screen, ice_c, (bx, by, block_w, block_h), 1)
        # Frost highlights
        for fy in range(by + 3, by + block_h - 3, 6):
            fw = random.randint(4, 12)
            fx = bx + random.randint(2, block_w - fw - 2)
            pygame.draw.rect(screen, (80, 150, 230), (fx, fy, fw, 1))
        # Stick figure inside ice
        pygame.draw.circle(screen, (180, 180, 200), (cx, cy - 10), 5, 1)
        pygame.draw.line(screen, (180, 180, 200), (cx, cy - 5), (cx, cy + 8), 1)
        pygame.draw.line(screen, (180, 180, 200), (cx, cy), (cx - 5, cy + 5), 1)
        pygame.draw.line(screen, (180, 180, 200), (cx, cy), (cx + 5, cy + 5), 1)

        # Danger border pulse
        bp = int(pulse * 80)
        border_c = (bp, 0, 0)
        pygame.draw.rect(screen, border_c, (0, 20, VIRT_W, VIRT_H - 20), 2)

        # Warning text
        warn = fonts["huge"].render("FREEZE!", False,
                                     (int(200 + pulse * 55), 100, 100))
        screen.blit(warn, (cx - warn.get_width() // 2, cy + 40))
        sub = fonts["med"].render("DON'T MOVE!", False, CYAN)
        screen.blit(sub, (cx - sub.get_width() // 2, cy + 65))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        if won:
            # Ice melts, character breaks free — rising sparkles
            melt = min(t / 0.5, 1.0)
            block_h = int(50 * (1 - melt))
            if block_h > 2:
                by = cy - block_h // 2
                pygame.draw.rect(screen, (40, 80, 140),
                                 (cx - 19, by, 38, block_h))
            # Freed character jumps
            jump_y = cy - int(melt * 40)
            pygame.draw.circle(screen, WHITE, (cx, jump_y - 10), 5, 1)
            pygame.draw.line(screen, WHITE, (cx, jump_y - 5), (cx, jump_y + 8), 1)
            pygame.draw.line(screen, WHITE, (cx - 5, jump_y - 2),
                             (cx + 5, jump_y - 2), 1)
            # Water puddle
            pw = int(melt * 30)
            pygame.draw.ellipse(screen, (60, 140, 200),
                                (cx - pw, cy + 30, pw * 2, 6))
            txt = fonts["huge"].render("FREE!", False, CYAN)
            screen.blit(txt, (cx - txt.get_width() // 2, cy + 45))
        else:
            # Ice shatters into shards
            for i in range(20):
                angle = i * math.pi * 2 / 20
                dist = t * random.uniform(30, 100)
                sx = cx + int(math.cos(angle) * dist)
                sy = cy + int(math.sin(angle) * dist)
                sz = random.randint(2, 5)
                pygame.draw.rect(screen, (100, 180, 255), (sx, sy, sz, sz))
            txt = fonts["huge"].render("SHATTER!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 15))


# ── 4. Turn potentiometer to MAX ─────────────────────────
class PotMaxGame(MicroGame):
    name = "LAUNCH!"
    base_duration = 4.0
    game_type = "action"

    def reset(self, snap=None, speed_mult=1.0):
        candidates = [1, 2]
        random.shuffle(candidates)
        self.pot = candidates[0]
        if snap:
            for c in candidates:
                if snap[f"pot{c}"] <= 3400:
                    self.pot = c
                    break
            else:
                self.pot = min(candidates,
                               key=lambda c: snap[f"pot{c}"])
        self.bg_color = (2, 2, 15)
        self.grace = 0.4
        self.particles = []
        self.smooth_pct = (snap[f"pot{self.pot}"] / 4095.0) if snap else 0.0
        self.stars = [(random.randint(0, VIRT_W - 1),
                       random.randint(0, VIRT_H - 1),
                       random.random() * 2 + 0.5) for _ in range(25)]
        self.hint = f"POT {self.pot}"

    def update(self, snap, dt):
        if self.grace > 0:
            self.grace -= dt
            return None
        target_pct = snap[f"pot{self.pot}"] / 4095.0
        self.smooth_pct += (target_pct - self.smooth_pct) * 0.15
        if self.smooth_pct * 4095 > 3800:
            return True
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        pct = self.smooth_pct

        # Scrolling stars (faster as pct increases)
        for i, (sx, sy, spd) in enumerate(self.stars):
            sy += spd * (0.5 + pct * 4)
            if sy > VIRT_H:
                sy = 0
                sx = random.randint(0, VIRT_W - 1)
            self.stars[i] = (sx, sy, spd)
            bright = int(80 + pct * 175)
            pygame.draw.rect(screen, (bright, bright, bright),
                             (int(sx), int(sy), 1, 1))

        # Rocket position rises with pot
        ground_y = cy + 70
        sky_y = cy - 80
        rocket_y = int(ground_y - pct * (ground_y - sky_y))
        rx = cx

        # Exhaust flame particles
        if pct > 0.02:
            for _ in range(int(1 + pct * 5)):
                px = rx + random.randint(-3, 3)
                py = rocket_y + 14 + random.randint(0, int(5 + pct * 12))
                self.particles.append([px, py, random.choice([RED, ORANGE, YELLOW]),
                                       random.randint(4, 10)])
        new_p = []
        for p in self.particles:
            p[1] += random.uniform(0.5, 2.0)
            p[0] += random.uniform(-0.5, 0.5)
            p[3] -= 1
            if p[3] > 0 and p[1] < VIRT_H:
                sz = 2 if p[3] > 3 else 1
                pygame.draw.rect(screen, p[2], (int(p[0]), int(p[1]), sz, sz))
                new_p.append(p)
        self.particles = new_p[-80:]

        # Rocket pixel art
        pygame.draw.polygon(screen, RED, [
            (rx, rocket_y - 6), (rx - 4, rocket_y + 2), (rx + 4, rocket_y + 2)])
        pygame.draw.rect(screen, WHITE, (rx - 4, rocket_y + 2, 8, 12))
        pygame.draw.rect(screen, CYAN, (rx - 2, rocket_y + 4, 4, 3))
        pygame.draw.polygon(screen, ORANGE, [
            (rx - 4, rocket_y + 10), (rx - 7, rocket_y + 15), (rx - 4, rocket_y + 14)])
        pygame.draw.polygon(screen, ORANGE, [
            (rx + 4, rocket_y + 10), (rx + 7, rocket_y + 15), (rx + 4, rocket_y + 14)])

        # Launch pad
        if pct < 0.3:
            pygame.draw.rect(screen, GREY, (cx - 15, ground_y + 16, 30, 3))

        # Orbit threshold line
        thresh_y = int(ground_y - (3800 / 4095) * (ground_y - sky_y))
        pygame.draw.line(screen, NEON_GREEN, (cx - 25, thresh_y), (cx + 25, thresh_y), 1)
        orbit = fonts["small"].render("ORBIT", False, NEON_GREEN)
        screen.blit(orbit, (cx + 28, thresh_y - 4))

        lbl = fonts["big"].render(f"POT {self.pot}", False, WHITE)
        screen.blit(lbl, (cx - lbl.get_width() // 2, 22))
        color = GREEN if pct > 0.9 else YELLOW if pct > 0.5 else ORANGE
        pct_txt = fonts["med"].render(f"{int(pct * 100)}%", False, color)
        screen.blit(pct_txt, (cx - pct_txt.get_width() // 2, ground_y + 24))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        if won:
            # Rocket blasts off screen with massive flame trail
            rocket_y = int(cy - 60 - t * 400)
            rx = cx
            # Huge flame trail
            for i in range(25):
                py = rocket_y + 14 + random.randint(0, int(20 + t * 80))
                px = rx + random.randint(-5, 5)
                if py < VIRT_H:
                    c = random.choice([RED, ORANGE, YELLOW, WHITE])
                    sz = random.randint(1, 3)
                    pygame.draw.rect(screen, c, (px, py, sz, sz))
            # Rocket (flies up)
            if rocket_y > -20:
                pygame.draw.polygon(screen, RED, [
                    (rx, rocket_y - 6), (rx - 4, rocket_y + 2),
                    (rx + 4, rocket_y + 2)])
                pygame.draw.rect(screen, WHITE, (rx - 4, rocket_y + 2, 8, 12))
            # Stars streak past
            for i in range(8):
                sy = (i * 50 + int(t * 600)) % VIRT_H
                sx = random.randint(0, VIRT_W)
                pygame.draw.line(screen, WHITE, (sx, sy), (sx, sy + 3))
            txt = fonts["huge"].render("ORBIT!", False, NEON_GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, VIRT_H // 2 + 30))
        else:
            # Rocket falls and crashes with explosion
            ground = cy + 70
            fall_y = min(ground, int(cy - 60 + t * 300))
            rx = cx + int(math.sin(t * 15) * 5)
            # Smoke
            for i in range(8):
                sx = rx + random.randint(-10, 10)
                sy = fall_y - random.randint(0, int(t * 40))
                pygame.draw.circle(screen, GREY, (sx, sy), random.randint(2, 5))
            if fall_y >= ground:
                # Explosion
                for _ in range(12):
                    angle = random.uniform(0, math.pi * 2)
                    d = random.uniform(5, 25)
                    ex = rx + int(math.cos(angle) * d)
                    ey = ground + int(math.sin(angle) * d)
                    pygame.draw.rect(screen, random.choice([RED, ORANGE, YELLOW]),
                                     (ex, ey, 3, 3))
            else:
                # Tumbling rocket
                pygame.draw.polygon(screen, RED, [
                    (rx, fall_y - 6), (rx - 4, fall_y + 2),
                    (rx + 4, fall_y + 2)])
                pygame.draw.rect(screen, WHITE, (rx - 4, fall_y + 2, 8, 12))
            txt = fonts["huge"].render("CRASH!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 30))


# ── 5. Turn potentiometer to MIN ─────────────────────────
class PotMinGame(MicroGame):
    name = "DIVE!"
    base_duration = 4.0
    game_type = "action"

    def reset(self, snap=None, speed_mult=1.0):
        candidates = [1, 2]
        random.shuffle(candidates)
        self.pot = candidates[0]
        if snap:
            for c in candidates:
                if snap[f"pot{c}"] >= 700:
                    self.pot = c
                    break
            else:
                self.pot = max(candidates,
                               key=lambda c: snap[f"pot{c}"])
        self.bg_color = (5, 15, 40)
        self.grace = 0.4
        self.bubbles = []
        self.smooth_pct = (snap[f"pot{self.pot}"] / 4095.0) if snap else 1.0
        self.fish = [(random.randint(0, VIRT_W),
                      random.randint(60, VIRT_H - 40),
                      random.choice([-1, 1]),
                      random.uniform(0.3, 1.0),
                      random.choice([CYAN, NEON_GREEN, PINK, YELLOW]))
                     for _ in range(6)]
        self.hint = f"POT {self.pot}"

    def update(self, snap, dt):
        if self.grace > 0:
            self.grace -= dt
            return None
        target_pct = snap[f"pot{self.pot}"] / 4095.0
        self.smooth_pct += (target_pct - self.smooth_pct) * 0.15
        if self.smooth_pct * 4095 < 300:
            return True
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        pct = self.smooth_pct
        depth = 1.0 - pct

        # Water gradient (darker deeper)
        for stripe_y in range(20, VIRT_H, 8):
            sd = stripe_y / VIRT_H
            r = int(2 + 8 * (1 - sd) * (1 - depth * 0.5))
            g = int(10 + 25 * (1 - sd) * (1 - depth * 0.3))
            b = int(30 + 50 * (1 - sd))
            pygame.draw.rect(screen, (r, g, b), (0, stripe_y, VIRT_W, 8))

        # Fish swimming around
        for i, (fx, fy, d, spd, fc) in enumerate(self.fish):
            fx += d * spd
            if fx > VIRT_W + 10: fx = -10
            elif fx < -10: fx = VIRT_W + 10
            self.fish[i] = (fx, fy, d, spd, fc)
            bx = int(fx)
            pygame.draw.rect(screen, fc, (bx, int(fy), 4, 2))
            pygame.draw.rect(screen, fc, (bx - 2 * d, int(fy) - 1, 2, 4))

        # Submarine position (high pot = near surface, low pot = deep)
        surface_y = 50
        bottom_y = cy + 80
        sub_y = int(surface_y + (1 - pct) * (bottom_y - surface_y))
        sx = cx

        # Bubbles
        if random.random() < 0.4:
            self.bubbles.append([sx + random.randint(-6, 6), sub_y - 2,
                                 random.randint(8, 20)])
        new_b = []
        for b in self.bubbles:
            b[1] -= random.uniform(0.3, 1.0)
            b[2] -= 1
            if b[2] > 0 and b[1] > 20:
                pygame.draw.circle(screen, (100, 200, 255), (int(b[0]), int(b[1])), 1)
                new_b.append(b)
        self.bubbles = new_b[-40:]

        # Submarine pixel art
        pygame.draw.ellipse(screen, YELLOW, (sx - 10, sub_y - 4, 20, 8))
        pygame.draw.rect(screen, YELLOW, (sx - 3, sub_y - 8, 6, 5))
        pygame.draw.rect(screen, GREY, (sx, sub_y - 11, 1, 4))
        pygame.draw.rect(screen, GREY, (sx, sub_y - 11, 3, 1))
        pygame.draw.circle(screen, CYAN, (sx - 3, sub_y), 2)
        prop = int(time.time() * 10) % 2
        pygame.draw.rect(screen, GREY, (sx + 10, sub_y - 3 + prop, 2, 1))
        pygame.draw.rect(screen, GREY, (sx + 10, sub_y + prop, 2, 1))

        # Target depth line
        target_y = int(surface_y + (1 - 300 / 4095) * (bottom_y - surface_y))
        pygame.draw.line(screen, NEON_GREEN, (cx - 25, target_y), (cx + 25, target_y), 1)
        tgt = fonts["small"].render("TARGET", False, NEON_GREEN)
        screen.blit(tgt, (cx + 28, target_y - 4))

        # Surface waves
        for wx in range(0, VIRT_W, 6):
            wy = surface_y - 5 + int(math.sin(time.time() * 3 + wx * 0.3) * 2)
            pygame.draw.rect(screen, (80, 160, 220), (wx, wy, 4, 1))

        lbl = fonts["big"].render(f"POT {self.pot}", False, WHITE)
        screen.blit(lbl, (cx - lbl.get_width() // 2, 22))
        color = GREEN if pct < 0.1 else ORANGE if pct < 0.5 else RED
        depth_m = int((1 - pct) * 200)
        dm = fonts["med"].render(f"{depth_m}m", False, color)
        screen.blit(dm, (cx - dm.get_width() // 2, bottom_y + 15))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        # Dark water bg
        for sy in range(20, VIRT_H, 8):
            sd = sy / VIRT_H
            pygame.draw.rect(screen, (2, int(8 * (1 - sd)), int(30 + 20 * (1 - sd))),
                             (0, sy, VIRT_W, 8))
        if won:
            # Sub finds treasure — chest glows at bottom
            sub_y = cy + int(t * 30)
            pygame.draw.ellipse(screen, YELLOW, (cx - 10, sub_y - 4, 20, 8))
            pygame.draw.rect(screen, YELLOW, (cx - 3, sub_y - 8, 6, 5))
            # Treasure chest
            chest_y = cy + 60
            pygame.draw.rect(screen, (139, 90, 43), (cx - 8, chest_y, 16, 10))
            pygame.draw.rect(screen, YELLOW, (cx - 1, chest_y + 3, 3, 4))
            # Glow
            glow_r = int(10 + t * 30)
            gc = (int(min(255, 80 * t * 3)), int(min(255, 60 * t * 3)), 0)
            pygame.draw.circle(screen, gc, (cx, chest_y + 5), glow_r, 1)
            # Coins floating up
            for i in range(int(t * 12)):
                coin_x = cx + int(math.sin(i * 2.1 + t * 3) * 15)
                coin_y = chest_y - int(i * 4 + t * 20)
                if coin_y > 20:
                    pygame.draw.rect(screen, YELLOW, (coin_x, coin_y, 3, 3))
            txt = fonts["huge"].render("FOUND!", False, YELLOW)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 40))
        else:
            # Sub implodes — hull cracks, bubbles everywhere
            sub_y = cy
            shake = int(t * 8) % 3 - 1
            sx = cx + shake
            # Cracking sub
            pygame.draw.ellipse(screen, (180, 150, 0), (sx - 10, sub_y - 4, 20, 8))
            # Crack lines
            for i in range(int(t * 8)):
                cl = random.randint(3, 8)
                ca = random.uniform(0, math.pi * 2)
                pygame.draw.line(screen, RED,
                                 (sx, sub_y),
                                 (sx + int(math.cos(ca) * cl),
                                  sub_y + int(math.sin(ca) * cl)), 1)
            # Massive bubbles
            for i in range(int(t * 30)):
                bx = cx + random.randint(-30, 30)
                by = sub_y - random.randint(0, int(t * 80))
                pygame.draw.circle(screen, (100, 200, 255), (bx, by),
                                   random.randint(1, 3))
            txt = fonts["huge"].render("IMPLODE!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy + 30))


# ── 6. Match a target zone with a pot ─────────────────────
class MatchTargetGame(MicroGame):
    name = "TUNE!"
    base_duration = 5.0
    game_type = "action"
    bg_color = (10, 10, 25)

    def reset(self, snap=None, speed_mult=1.0):
        self.pot = random.choice([1, 2])
        self.tolerance = 200
        current = snap[f"pot{self.pot}"] if snap else 2048
        lo, hi = 400, 3700
        far_lo = max(lo, current + 800)
        far_hi = min(hi, current - 800)
        if far_lo <= hi:
            self.target = random.randint(far_lo, hi)
        elif far_hi >= lo:
            self.target = random.randint(lo, far_hi)
        else:
            self.target = lo if current > 2048 else hi
        self.grace = 0.4
        self.notes = []
        self.smooth_val = float(current)
        self.static_px = [(random.randint(0, VIRT_W - 1),
                           random.randint(50, VIRT_H - 30))
                          for _ in range(60)]
        self.hint = f"POT {self.pot}"

    def update(self, snap, dt):
        if self.grace > 0:
            self.grace -= dt
            return None
        raw_val = snap[f"pot{self.pot}"]
        self.smooth_val += (raw_val - self.smooth_val) * 0.15
        if abs(self.smooth_val - self.target) < self.tolerance:
            return True
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2 - 10
        val = self.smooth_val
        dist = abs(val - self.target)
        in_zone = dist < self.tolerance
        closeness = max(0, 1.0 - dist / 2000.0)

        # Static noise (less when closer)
        for i in range(int(60 * (1 - closeness))):
            sx, sy = self.static_px[i % len(self.static_px)]
            sx = (sx + random.randint(-2, 2)) % VIRT_W
            sy = (sy + random.randint(-2, 2)) % VIRT_H
            nv = random.randint(20, 60)
            pygame.draw.rect(screen, (nv, nv, nv + 10), (sx, sy, 1, 1))

        # Radio body
        ant_y = cy - 30
        pygame.draw.rect(screen, GREY, (cx - 8, cy + 10, 16, 6))
        pygame.draw.rect(screen, DARK_GREY, (cx - 6, cy + 6, 12, 6))
        for gy in range(cy + 14, cy + 30, 3):
            pygame.draw.line(screen, GREY, (cx - 6, gy), (cx + 6, gy), 1)
        pygame.draw.rect(screen, GREY, (cx - 8, cy + 10, 16, 22), 1)
        pygame.draw.line(screen, WHITE, (cx, cy + 6), (cx, ant_y), 1)
        pygame.draw.circle(screen, CYAN if in_zone else RED, (cx, ant_y), 2)

        # Signal waves
        if closeness > 0.3:
            for w in range(int(closeness * 4)):
                wave_r = 12 + w * 10 + int(math.sin(time.time() * 4) * 2)
                wc = NEON_GREEN if in_zone else YELLOW
                ac = (wc[0] // (w + 1), wc[1] // (w + 1), wc[2] // (w + 1))
                for angle_deg in range(-60, 61, 15):
                    angle = math.radians(angle_deg - 90)
                    px = cx + int(math.cos(angle) * wave_r)
                    py = ant_y + int(math.sin(angle) * wave_r)
                    if 20 < py < VIRT_H - 20:
                        pygame.draw.rect(screen, ac, (px, py, 1, 1))

        # Music notes when tuned in
        if in_zone and random.random() < 0.3:
            self.notes.append([cx + random.randint(-30, 30),
                               ant_y + random.randint(-20, 10),
                               random.randint(15, 25),
                               random.choice([CYAN, NEON_GREEN, YELLOW])])
        new_notes = []
        for n in self.notes:
            n[1] -= 0.8
            n[2] -= 1
            if n[2] > 0:
                nt = fonts["small"].render("*", False, n[3])
                screen.blit(nt, (int(n[0]), int(n[1])))
                new_notes.append(n)
        self.notes = new_notes[-20:]

        # Dial bar
        dial_y = cy + 50
        bar_w = 160
        bar_x = (VIRT_W - bar_w) // 2
        pygame.draw.rect(screen, DARK_GREY, (bar_x, dial_y, bar_w, 10))
        t_lo = int((self.target - self.tolerance) / 4095 * bar_w)
        t_hi = int((self.target + self.tolerance) / 4095 * bar_w)
        pygame.draw.rect(screen, (20, 60, 20),
                         (bar_x + t_lo, dial_y, t_hi - t_lo, 10))
        pos_x = bar_x + int(val / 4095 * bar_w)
        pygame.draw.rect(screen, NEON_GREEN if in_zone else ORANGE,
                         (pos_x - 1, dial_y - 3, 2, 16))

        # Frequency display
        freq = 88.0 + (val / 4095) * 20
        ft = fonts["med"].render(f"{freq:.1f} FM", False,
                                 NEON_GREEN if in_zone else ORANGE)
        screen.blit(ft, (cx - ft.get_width() // 2, dial_y + 16))
        lbl = fonts["big"].render(f"POT {self.pot}", False, WHITE)
        screen.blit(lbl, (cx - lbl.get_width() // 2, 22))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        if won:
            # Radio plays music — big colorful notes fly out
            pygame.draw.rect(screen, DARK_GREY, (cx - 8, cy + 6, 16, 22))
            pygame.draw.rect(screen, GREY, (cx - 8, cy + 6, 16, 22), 1)
            pygame.draw.circle(screen, NEON_GREEN, (cx, cy - 2), 2)
            note_chars = ["*", "~", ".", "*"]
            for i in range(int(t * 20)):
                angle = (i * 0.8 + t * 4)
                dist = 10 + i * 3 + t * 30
                nx = cx + int(math.cos(angle) * dist)
                ny = cy - 10 + int(math.sin(angle) * dist * 0.6)
                nc = [CYAN, NEON_GREEN, YELLOW, PINK, ORANGE][i % 5]
                nt = fonts["med"].render(note_chars[i % 4], False, nc)
                screen.blit(nt, (nx, ny))
            txt = fonts["huge"].render("TUNED!", False, NEON_GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, cy + 45))
        else:
            # Radio sparks and smokes — static fills screen
            for _ in range(40):
                sx = random.randint(0, VIRT_W)
                sy = random.randint(20, VIRT_H)
                nv = random.randint(20, 60)
                pygame.draw.rect(screen, (nv, nv, nv), (sx, sy, 1, 1))
            # Sparking radio
            pygame.draw.rect(screen, DARK_GREY, (cx - 8, cy + 6, 16, 22))
            for _ in range(5):
                sx = cx + random.randint(-12, 12)
                sy = cy + random.randint(-5, 15)
                pygame.draw.rect(screen, random.choice([YELLOW, ORANGE, RED]),
                                 (sx, sy, 2, 2))
            # Smoke
            for i in range(int(t * 10)):
                sx = cx + random.randint(-6, 6)
                sy = cy - 5 - int(i * 4 + t * 20)
                if sy > 20:
                    pygame.draw.circle(screen, (60, 60, 60), (sx, sy),
                                       random.randint(2, 4))
            txt = fonts["huge"].render("STATIC!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy + 45))
# ── 7. Mash a button N times ─────────────────────────────
class MashGame(MicroGame):
    name = "INFLATE!"
    base_duration = 6.0
    game_type = "action"
    bg_color = (10, 10, 30)

    def reset(self, snap=None, speed_mult=1.0):
        self.target_count = random.randint(8, 16)
        self.count = 0
        self.btn = random.choice([1, 2])
        self._baseline = None
        self.balloon_color = random.choice([RED, PINK, CYAN, NEON_GREEN, YELLOW, PURPLE])
        self.wobble = 0
        self.hint = f"B{self.btn}"

    def update(self, snap, dt):
        presses = snap[f"btn{self.btn}_presses"]
        if self._baseline is None:
            self._baseline = presses
            return None
        old_count = self.count
        self.count = presses - self._baseline
        if self.count != old_count:
            self.wobble = 4
        if self.count >= self.target_count:
            return True
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2 - 15
        pct = min(self.count / self.target_count, 1.0)

        # Balloon grows with each press
        min_r, max_r = 10, 45
        radius = int(min_r + pct * (max_r - min_r))

        # Wobble on press
        if self.wobble > 0:
            self.wobble = max(0, self.wobble - 0.5)
            wx = int(math.sin(time.time() * 40) * self.wobble)
            wy = int(math.cos(time.time() * 40) * self.wobble * 0.5)
        else:
            wx, wy = 0, 0

        bcx = cx + wx
        bcy = cy - radius // 3 + wy

        # Balloon body
        pygame.draw.ellipse(screen, self.balloon_color,
                            (bcx - radius, bcy - int(radius * 1.2),
                             radius * 2, int(radius * 2.4)))
        # Highlight
        hr = max(2, radius // 3)
        hc = (min(255, self.balloon_color[0] + 80),
              min(255, self.balloon_color[1] + 80),
              min(255, self.balloon_color[2] + 80))
        pygame.draw.ellipse(screen, hc,
                            (bcx - radius // 2, bcy - int(radius * 0.9),
                             hr, hr))
        # Knot + string
        knot_y = bcy + int(radius * 1.2)
        pygame.draw.rect(screen, self.balloon_color, (bcx - 1, knot_y, 3, 3))
        for sy in range(knot_y + 3, knot_y + 30):
            ssx = bcx + int(math.sin((sy - knot_y) * 0.3) * 3)
            pygame.draw.rect(screen, GREY, (ssx, sy, 1, 1))

        # Face (gets worried as balloon fills)
        if radius > 15:
            eye_y = bcy - radius // 4
            ed = radius // 3
            pygame.draw.rect(screen, BLACK, (bcx - ed - 1, eye_y, 2, 2))
            pygame.draw.rect(screen, BLACK, (bcx + ed - 1, eye_y, 2, 2))
            mouth_y = bcy + radius // 4
            if pct < 0.5:
                pygame.draw.rect(screen, BLACK, (bcx - 2, mouth_y, 5, 1))
            elif pct < 0.8:
                pygame.draw.circle(screen, BLACK, (bcx, mouth_y), 2, 1)
            else:
                pygame.draw.circle(screen, BLACK, (bcx, mouth_y), 3, 1)
                pygame.draw.rect(screen, CYAN, (bcx + ed + 2, eye_y - 1, 1, 2))

        ct = fonts["big"].render(
            f"{self.count}/{self.target_count}", False,
            GREEN if pct >= 1.0 else WHITE)
        screen.blit(ct, (cx - ct.get_width() // 2, cy + 65))
        btn_lbl = fonts["big"].render(f"BTN {self.btn}", False, YELLOW)
        screen.blit(btn_lbl, (cx - btn_lbl.get_width() // 2, 22))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2 - 15
        if won:
            # Balloon floats up and away with a happy face
            fly_y = cy - int(t * 200)
            sway = int(math.sin(t * 8) * 10)
            bx = cx + sway
            r = 45
            pygame.draw.ellipse(screen, self.balloon_color,
                                (bx - r, fly_y - int(r * 1.2),
                                 r * 2, int(r * 2.4)))
            # Happy face
            ed = r // 3
            eye_y = fly_y - r // 4
            pygame.draw.rect(screen, BLACK, (bx - ed - 1, eye_y, 2, 2))
            pygame.draw.rect(screen, BLACK, (bx + ed - 1, eye_y, 2, 2))
            # Smile arc
            for a in range(-40, 41, 10):
                mx = bx + int(math.cos(math.radians(a)) * 5)
                my = fly_y + r // 4 + int(math.sin(math.radians(a)) * 3)
                pygame.draw.rect(screen, BLACK, (mx, my, 1, 1))
            # String trails behind
            for sy in range(int(fly_y + r * 1.2), int(fly_y + r * 1.2 + 25)):
                ssx = bx + int(math.sin((sy - fly_y) * 0.3) * 3)
                if 0 < sy < VIRT_H:
                    pygame.draw.rect(screen, GREY, (ssx, sy, 1, 1))
            txt = fonts["huge"].render("FLOAT!", False, NEON_GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, VIRT_H // 2 + 50))
        else:
            # Balloon pops — rubber shreds fly outward
            for i in range(20):
                angle = i * math.pi * 2 / 20 + t * 2
                dist = t * random.uniform(20, 100)
                sx = cx + int(math.cos(angle) * dist)
                sy = cy + int(math.sin(angle) * dist)
                # Rubbery shred
                sz = random.randint(2, 5)
                pygame.draw.rect(screen, self.balloon_color, (sx, sy, sz, 2))
            # Pop burst lines
            if t < 0.2:
                for a_deg in range(0, 360, 30):
                    a = math.radians(a_deg)
                    l = int(t * 200)
                    pygame.draw.line(screen, WHITE, (cx, cy),
                                     (cx + int(math.cos(a) * l),
                                      cy + int(math.sin(a) * l)), 1)
            # Dangling string falls
            string_y = cy + int(t * 120)
            for sy in range(string_y, min(string_y + 25, VIRT_H)):
                ssx = cx + int(math.sin((sy - string_y) * 0.3) * 3)
                pygame.draw.rect(screen, GREY, (ssx, sy, 1, 1))
            txt = fonts["huge"].render("POP!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy + 50))


# ── 8. Hold a button for the duration ────────────────────
class HoldGame(MicroGame):
    name = "DEFUSE!"
    base_duration = 4.0
    game_type = "survive"
    bg_color = (15, 10, 10)

    def reset(self, snap=None, speed_mult=1.0):
        self.btn = random.choice([1, 2])
        self.started = False
        self.wait_time = 0.0
        self.sparks = []
        self.hint = f"B{self.btn}"

    def update(self, snap, dt):
        pressed = snap[f"btn{self.btn}"]
        if not self.started:
            if pressed:
                self.started = True
            else:
                # 1.8s to read instruction and press the button
                self.wait_time += dt
                if self.wait_time > 1.8:
                    return False
            return None
        # Once holding, releasing = lose
        if not pressed:
            return False
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2 - 10
        pressed = snap[f"btn{self.btn}"]

        # Bomb body
        pygame.draw.circle(screen, (30, 30, 30), (cx, cy + 10), 22)
        pygame.draw.circle(screen, (50, 50, 50), (cx, cy + 10), 22, 1)
        pygame.draw.circle(screen, (60, 60, 60), (cx - 6, cy + 2), 4)
        # Fuse socket
        pygame.draw.rect(screen, GREY, (cx - 3, cy - 12, 6, 5))
        # Fuse (wiggly)
        fuse_ex, fuse_ey = cx + 15, cy - 30
        for t_val in range(10):
            t = t_val / 10.0
            fx = int(cx + (fuse_ex - cx) * t + math.sin(t * 6) * 3)
            fy = int(cy - 12 + (fuse_ey - cy + 12) * t)
            pygame.draw.rect(screen, (139, 90, 43), (fx, fy, 1, 1))

        # Sparking fuse tip when not safely held
        if not pressed or not self.started:
            for _ in range(3):
                self.sparks.append([fuse_ex + random.randint(-4, 4),
                                    fuse_ey + random.randint(-4, 2),
                                    random.randint(3, 6),
                                    random.choice([YELLOW, ORANGE, RED, WHITE])])
        new_s = []
        for s in self.sparks:
            s[0] += random.uniform(-1, 1)
            s[1] -= random.uniform(0.2, 1)
            s[2] -= 1
            if s[2] > 0:
                pygame.draw.rect(screen, s[3], (int(s[0]), int(s[1]), 1, 1))
                new_s.append(s)
        self.sparks = new_s[-30:]

        if not self.started:
            txt = fonts["big"].render(f"HOLD BTN {self.btn}!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy + 45))
            if int(time.time() * 4) % 2:
                warn = fonts["med"].render("PRESS NOW!", False, YELLOW)
                screen.blit(warn, (cx - warn.get_width() // 2, cy + 65))
        elif pressed:
            txt = fonts["big"].render(f"HOLD BTN {self.btn}!", False, GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, cy + 45))
            safe = fonts["med"].render("DEFUSING...", False, NEON_GREEN)
            screen.blit(safe, (cx - safe.get_width() // 2, cy + 65))
        else:
            txt = fonts["big"].render("BOOM!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy + 45))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        if won:
            # Fuse fizzles out, bomb is safe — checkmark
            pygame.draw.circle(screen, (30, 30, 30), (cx, cy), 22)
            pygame.draw.circle(screen, NEON_GREEN, (cx, cy), 22, 1)
            # Snipped fuse (short stub)
            pygame.draw.rect(screen, (80, 50, 25), (cx - 3, cy - 14, 6, 4))
            # Smoke wisp
            for i in range(int(t * 8)):
                sx = cx + random.randint(-3, 3)
                sy = cy - 18 - int(i * 3 + t * 15)
                if sy > 20:
                    pygame.draw.circle(screen, (80, 80, 80), (sx, sy),
                                       random.randint(1, 3))
            # Checkmark on bomb
            scale = min(t / 0.15, 1.0)
            if scale > 0:
                pts = [(cx - int(8 * scale), cy),
                       (cx - int(2 * scale), cy + int(8 * scale)),
                       (cx + int(10 * scale), cy - int(8 * scale))]
                pygame.draw.lines(screen, NEON_GREEN, False, pts, 2)
            txt = fonts["huge"].render("SAFE!", False, NEON_GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, cy + 35))
        else:
            # Bomb explodes — huge expanding fireball with debris
            shake = int(max(0, 3 - t * 5))
            ox = random.randint(-shake, shake) if shake else 0
            oy = random.randint(-shake, shake) if shake else 0
            ecx, ecy = cx + ox, cy + oy
            # Fireball grows
            fb_r = int(t * 100)
            if fb_r > 0:
                pygame.draw.circle(screen, ORANGE, (ecx, ecy), min(fb_r, 80))
                pygame.draw.circle(screen, YELLOW, (ecx, ecy), min(fb_r // 2, 40))
                pygame.draw.circle(screen, WHITE, (ecx, ecy), min(fb_r // 4, 15))
            # Debris
            for i in range(20):
                angle = i * math.pi * 2 / 20
                dist = t * random.uniform(30, 120)
                dx = ecx + int(math.cos(angle) * dist)
                dy = ecy + int(math.sin(angle) * dist)
                pygame.draw.rect(screen, random.choice([RED, ORANGE, (30, 30, 30)]),
                                 (dx, dy, random.randint(2, 4), random.randint(2, 4)))
            txt = fonts["huge"].render("BOOM!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 60))


# ── 9. Quick Draw — react to a signal ────────────────────
class QuickDrawGame(MicroGame):
    name = "DRAW!"
    hint = "B1 or B2"
    base_duration = 30.0  # safety cap
    game_type = "action"
    wave_based = True
    bg_color = (25, 15, 5)

    def reset(self, snap=None, speed_mult=1.0):
        self.wait_time = random.uniform(3.0, 6.0)
        self.react_window = max(0.4, 1.5 * speed_mult)  # shrinks with difficulty
        self.elapsed = 0.0
        self.signal = False
        self.signal_time = 0.0
        self.too_early = False

    def update(self, snap, dt):
        self.elapsed += dt
        if not self.signal:
            if snap["btn1"] or snap["btn2"]:
                self.too_early = True
                return False
            if self.elapsed >= self.wait_time:
                self.signal = True
                self.signal_time = 0.0
            return None
        # Signal is active — count reaction time
        self.signal_time += dt
        if snap["btn1"] or snap["btn2"]:
            return True
        if self.signal_time > self.react_window:
            return False  # too slow
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2

        # Sky gradient (sunset)
        for sy in range(0, cy + 40, 4):
            t_sky = sy / (cy + 40)
            r = int(25 + 80 * t_sky)
            g = int(15 + 30 * t_sky)
            b = int(5 + 10 * t_sky)
            pygame.draw.rect(screen, (r, g, b), (0, sy, VIRT_W, 4))

        # Sun
        sun_y = 40
        pygame.draw.circle(screen, (255, 200, 50), (cx, sun_y), 14)
        for a_deg in range(0, 360, 30):
            a = math.radians(a_deg + time.time() * 20)
            pygame.draw.line(screen, (255, 180, 30),
                             (cx + int(math.cos(a) * 16), sun_y + int(math.sin(a) * 16)),
                             (cx + int(math.cos(a) * 22), sun_y + int(math.sin(a) * 22)), 1)

        # Desert ground with gradient
        ground_y = cy + 50
        pygame.draw.rect(screen, (80, 55, 25), (0, ground_y, VIRT_W, VIRT_H - ground_y))
        pygame.draw.rect(screen, (90, 65, 30), (0, ground_y, VIRT_W, 3))

        # Cacti (background)
        for ci, cx_off in [(0, 30), (1, VIRT_W - 35)]:
            cg = (40 + ci * 10, 80 + ci * 5, 20)
            pygame.draw.rect(screen, cg, (cx_off, ground_y - 20, 4, 20))
            pygame.draw.rect(screen, cg, (cx_off - 5, ground_y - 15, 4, 10))
            pygame.draw.rect(screen, cg, (cx_off + 5, ground_y - 12, 4, 8))

        # Tumbleweed
        tw_x = int((time.time() * 25) % (VIRT_W + 60)) - 30
        tw_spin = time.time() * 3
        for i in range(6):
            a = tw_spin + i * math.pi / 3
            pygame.draw.line(screen, (90, 70, 40),
                             (tw_x, ground_y - 3),
                             (tw_x + int(math.cos(a) * 5), ground_y - 3 + int(math.sin(a) * 5)), 1)

        # Two cowboys — more detailed
        for side, x_off in [(-1, cx - 50), (1, cx + 50)]:
            # Shadow on ground
            pygame.draw.ellipse(screen, (60, 40, 15), (x_off - 6, ground_y - 1, 12, 3))
            # Boots
            pygame.draw.rect(screen, (50, 25, 10), (x_off - 4, ground_y - 5, 3, 5))
            pygame.draw.rect(screen, (50, 25, 10), (x_off + 1, ground_y - 5, 3, 5))
            # Legs
            pygame.draw.line(screen, (70, 50, 30), (x_off - 2, ground_y - 5),
                             (x_off - 1, ground_y - 15), 1)
            pygame.draw.line(screen, (70, 50, 30), (x_off + 2, ground_y - 5),
                             (x_off + 1, ground_y - 15), 1)
            # Body (poncho)
            pygame.draw.rect(screen, (140, 80, 40), (x_off - 4, ground_y - 25, 8, 12))
            pygame.draw.rect(screen, (120, 65, 30), (x_off - 5, ground_y - 22, 10, 2))
            # Head
            pygame.draw.circle(screen, (210, 170, 130), (x_off, ground_y - 30), 5)
            # Eyes
            eye_dir = side
            pygame.draw.rect(screen, (40, 30, 20), (x_off + eye_dir * 2 - 1, ground_y - 31, 1, 1))
            pygame.draw.rect(screen, (40, 30, 20), (x_off + eye_dir * 2 + 1, ground_y - 31, 1, 1))
            # Hat (wide brim)
            pygame.draw.rect(screen, (60, 35, 15), (x_off - 8, ground_y - 37, 16, 3))
            pygame.draw.rect(screen, (60, 35, 15), (x_off - 4, ground_y - 42, 8, 6))
            # Arms — raise gun when signal
            if not self.signal:
                pygame.draw.line(screen, (210, 170, 130),
                                 (x_off, ground_y - 22),
                                 (x_off + side * 7, ground_y - 18), 1)
            else:
                # Arm pointing gun
                pygame.draw.line(screen, (210, 170, 130),
                                 (x_off, ground_y - 22),
                                 (x_off + side * 10, ground_y - 30), 2)
                # Gun
                pygame.draw.rect(screen, (60, 60, 60),
                                 (x_off + side * 10, ground_y - 32, side * 5, 2))

        if self.too_early:
            txt = fonts["huge"].render("TOO EARLY!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 50))
        elif not self.signal:
            dots = "." * (int(self.elapsed * 3) % 4)
            txt = fonts["huge"].render(f"WAIT{dots}", False, (180, 160, 120))
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 50))
        else:
            pulse = abs(math.sin(time.time() * 10))
            c = (255, int(50 + pulse * 200), 0)
            txt = fonts["giant"].render("FIRE!", False, c)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 55))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        ground_y = cy + 50

        # Sunset sky (same as draw())
        for sy in range(0, cy + 40, 4):
            t_sky = sy / (cy + 40)
            r = int(25 + 80 * t_sky)
            g = int(15 + 30 * t_sky)
            b = int(5 + 10 * t_sky)
            pygame.draw.rect(screen, (r, g, b), (0, sy, VIRT_W, 4))
        # Sun + rays
        sun_y = 40
        pygame.draw.circle(screen, (255, 200, 50), (cx, sun_y), 14)
        for a_deg in range(0, 360, 30):
            a = math.radians(a_deg + time.time() * 20)
            pygame.draw.line(screen, (255, 180, 30),
                             (cx + int(math.cos(a) * 16), sun_y + int(math.sin(a) * 16)),
                             (cx + int(math.cos(a) * 22), sun_y + int(math.sin(a) * 22)), 1)
        # Desert ground
        pygame.draw.rect(screen, (80, 55, 25), (0, ground_y, VIRT_W, VIRT_H - ground_y))
        pygame.draw.rect(screen, (90, 65, 30), (0, ground_y, VIRT_W, 3))
        # Cacti
        for ci, cx_off in [(0, 30), (1, VIRT_W - 35)]:
            cg = (40 + ci * 10, 80 + ci * 5, 20)
            pygame.draw.rect(screen, cg, (cx_off, ground_y - 20, 4, 20))
            pygame.draw.rect(screen, cg, (cx_off - 5, ground_y - 15, 4, 10))
            pygame.draw.rect(screen, cg, (cx_off + 5, ground_y - 12, 4, 8))
        # Tumbleweed
        tw_x = int((time.time() * 25) % (VIRT_W + 60)) - 30
        tw_spin = time.time() * 3
        for i in range(6):
            a = tw_spin + i * math.pi / 3
            pygame.draw.line(screen, (90, 70, 40),
                             (tw_x, ground_y - 3),
                             (tw_x + int(math.cos(a) * 5), ground_y - 3 + int(math.sin(a) * 5)), 1)

        def draw_standing_cowboy(x, facing, blowing_smoke=False):
            """Draw a standing cowboy facing left(-1) or right(+1)."""
            pygame.draw.ellipse(screen, (60, 40, 15), (x - 6, ground_y - 1, 12, 3))
            pygame.draw.rect(screen, (50, 25, 10), (x - 4, ground_y - 5, 3, 5))
            pygame.draw.rect(screen, (50, 25, 10), (x + 1, ground_y - 5, 3, 5))
            pygame.draw.line(screen, (70, 50, 30), (x - 2, ground_y - 5),
                             (x - 1, ground_y - 15), 1)
            pygame.draw.line(screen, (70, 50, 30), (x + 2, ground_y - 5),
                             (x + 1, ground_y - 15), 1)
            pygame.draw.rect(screen, (140, 80, 40), (x - 4, ground_y - 25, 8, 12))
            pygame.draw.rect(screen, (120, 65, 30), (x - 5, ground_y - 22, 10, 2))
            pygame.draw.circle(screen, (210, 170, 130), (x, ground_y - 30), 5)
            pygame.draw.rect(screen, (40, 30, 20),
                             (x + facing * 2 - 1, ground_y - 31, 1, 1))
            pygame.draw.rect(screen, (40, 30, 20),
                             (x + facing * 2 + 1, ground_y - 31, 1, 1))
            pygame.draw.rect(screen, (60, 35, 15), (x - 8, ground_y - 37, 16, 3))
            pygame.draw.rect(screen, (60, 35, 15), (x - 4, ground_y - 42, 8, 6))
            # Arm holding gun up
            pygame.draw.line(screen, (210, 170, 130),
                             (x, ground_y - 22),
                             (x + facing * 10, ground_y - 30), 2)
            gun_x = x + facing * 10
            pygame.draw.rect(screen, (60, 60, 60),
                             (gun_x, ground_y - 32, facing * 5, 2))
            if blowing_smoke:
                for i in range(int(t * 8)):
                    sx = gun_x + facing * 5 + random.Random(i + 7).randint(0, facing * 8)
                    sy = ground_y - 33 - random.Random(i + 3).randint(0, int(t * 20))
                    if 0 < sx < VIRT_W:
                        pygame.draw.circle(screen, (80, 80, 80), (sx, sy),
                                           random.Random(i + 1).randint(1, 2))

        def draw_falling_cowboy(x, facing, fall_pct):
            """Draw a cowboy toppling in the direction they're facing."""
            pivot_y = ground_y - 5
            angle = fall_pct * math.pi / 2
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            def rot(orig_y):
                dy = pivot_y - orig_y
                rx = int(x + facing * dy * sin_a)
                ry = int(pivot_y - dy * cos_a)
                return rx, ry
            # Feet stay planted
            pygame.draw.rect(screen, (50, 25, 10), (x - 4, ground_y - 5, 3, 5))
            pygame.draw.rect(screen, (50, 25, 10), (x + 1, ground_y - 5, 3, 5))
            # Body
            bx_top, by_top = rot(ground_y - 25)
            bx_bot, by_bot = rot(ground_y - 13)
            pygame.draw.line(screen, (140, 80, 40),
                             (bx_bot, by_bot), (bx_top, by_top), 5)
            # Head
            hx, hy = rot(ground_y - 35)
            pygame.draw.circle(screen, (210, 170, 130), (hx, hy), 5)
            # Hat tumbles off
            hat_d = int(fall_pct * 25)
            pygame.draw.rect(screen, (60, 35, 15),
                             (hx + facing * hat_d, hy - 6 + hat_d, 10, 3))
            # Dust on impact
            if fall_pct > 0.7:
                for i in range(int((fall_pct - 0.7) * 12)):
                    dx = x + facing * random.Random(i + 50).randint(5, 18)
                    dy = ground_y - random.Random(i + 80).randint(0, 5)
                    pygame.draw.circle(screen, (120, 90, 50), (dx, dy),
                                       random.Random(i + 30).randint(1, 3))

        if won:
            fall = min(t / 0.4, 1.0)
            # Winner (left, facing right) blows smoke from gun
            draw_standing_cowboy(cx - 50, 1, blowing_smoke=True)
            # Loser (right, facing left) topples backward (away = rightward)
            draw_falling_cowboy(cx + 50, 1, fall)
            txt = fonts["huge"].render("FASTEST!", False, NEON_GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 50))
        else:
            fall = min(t / 0.3, 1.0)
            # Player (left, facing right) topples forward
            draw_falling_cowboy(cx - 50, 1, fall)
            # Opponent (right, facing left) stands
            draw_standing_cowboy(cx + 50, -1)
            txt = fonts["huge"].render("TOO SLOW!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 50))


# ── 10. Catch — move basket with pot to catch falling stars ─
class CatchGame(MicroGame):
    name = "CATCH!"
    base_duration = 30.0  # safety cap; game ends when wave is done
    game_type = "action"
    wave_based = True
    bg_color = (5, 5, 25)

    def reset(self, snap=None, speed_mult=1.0):
        self.pot = random.choice([1, 2])
        self.smooth_x = float(VIRT_W // 2)
        self.total_count = random.randint(8, 12)
        self.target_count = self.total_count // 2 + 1  # need to catch majority
        self.caught = 0
        self.missed = 0
        self.spawned = 0
        self.items = []
        self.spawn_timer = 0.0
        self.spawn_interval = max(0.2, 0.5 * speed_mult)
        self.fall_speed_lo = 70 / speed_mult
        self.fall_speed_hi = 120 / speed_mult
        self.sparkles = []
        self.hint = f"POT {self.pot}"

    def update(self, snap, dt):
        val = snap[f"pot{self.pot}"]
        target_x = 15 + (val / 4095) * (VIRT_W - 30)
        self.smooth_x += (target_x - self.smooth_x) * 0.2
        basket_x = self.smooth_x
        basket_y = VIRT_H - 55

        # Spawn falling items one at a time with delay
        if self.spawned < self.total_count:
            self.spawn_timer += dt
            if self.spawn_timer >= self.spawn_interval:
                self.spawn_timer = 0
                sx = random.randint(20, VIRT_W - 20)
                self.items.append([sx, -8.0,
                                   random.uniform(self.fall_speed_lo, self.fall_speed_hi)])
                self.spawned += 1

        # Move items and check catches
        new_items = []
        for item in self.items:
            item[1] += item[2] * dt
            if abs(item[0] - basket_x) < 14 and abs(item[1] - basket_y) < 10:
                self.caught += 1
                for _ in range(4):
                    self.sparkles.append([item[0], basket_y,
                                          random.uniform(-30, 30),
                                          random.uniform(-50, -20), 0.4])
                continue
            if item[1] >= VIRT_H + 10:
                self.missed += 1
                continue
            new_items.append(item)
        self.items = new_items

        # Update sparkles
        new_sp = []
        for sp in self.sparkles:
            sp[0] += sp[2] * dt
            sp[1] += sp[3] * dt
            sp[4] -= dt
            if sp[4] > 0:
                new_sp.append(sp)
        self.sparkles = new_sp

        # Win early if caught enough
        if self.caught >= self.target_count:
            return True
        # All items done — did we catch enough?
        if self.spawned >= self.total_count and len(self.items) == 0:
            return self.caught >= self.target_count
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        bx = int(self.smooth_x)
        by = VIRT_H - 55

        # Starry sky background
        for i in range(15):
            sx = random.Random(i + 7).randint(5, VIRT_W - 5)
            sy = random.Random(i + 77).randint(30, cy)
            twinkle = 150 + int(math.sin(time.time() * 3 + i) * 80)
            pygame.draw.rect(screen, (twinkle, twinkle, twinkle), (sx, sy, 1, 1))

        # Moon
        pygame.draw.circle(screen, (220, 220, 180), (VIRT_W - 30, 45), 10)
        pygame.draw.circle(screen, self.bg_color, (VIRT_W - 26, 42), 8)

        # Falling stars (5-point star shape)
        for item in self.items:
            ix, iy = int(item[0]), int(item[1])
            spin = time.time() * 4 + ix
            for a_i in range(5):
                a = spin + a_i * math.pi * 2 / 5
                px = ix + int(math.cos(a) * 5)
                py = iy + int(math.sin(a) * 5)
                pygame.draw.line(screen, YELLOW, (ix, iy), (px, py), 1)
            pygame.draw.circle(screen, WHITE, (ix, iy), 2)

        # Sparkles
        for sp in self.sparkles:
            alpha = int(255 * (sp[4] / 0.4))
            c = (alpha, alpha, min(255, alpha + 50))
            pygame.draw.rect(screen, c, (int(sp[0]), int(sp[1]), 2, 2))

        # Basket
        pygame.draw.polygon(screen, (139, 90, 43), [
            (bx - 12, by - 5), (bx - 10, by + 8),
            (bx + 10, by + 8), (bx + 12, by - 5)])
        pygame.draw.polygon(screen, (100, 65, 25), [
            (bx - 12, by - 5), (bx - 10, by + 8),
            (bx + 10, by + 8), (bx + 12, by - 5)], 1)
        # Basket weave lines
        for wy in range(by - 3, by + 7, 3):
            pygame.draw.line(screen, (100, 65, 25), (bx - 11, wy), (bx + 11, wy), 1)

        # Ground
        pygame.draw.line(screen, (30, 50, 30), (0, VIRT_H - 38), (VIRT_W, VIRT_H - 38), 1)
        # Grass tufts
        for i in range(0, VIRT_W, 8):
            gh = random.Random(i + 3).randint(2, 5)
            pygame.draw.line(screen, (30, 70, 30), (i, VIRT_H - 38), (i + 2, VIRT_H - 38 - gh), 1)

        # Counter
        ct = fonts["big"].render(f"{self.caught}/{self.target_count}", False,
                                 NEON_GREEN if self.caught >= self.target_count else YELLOW)
        screen.blit(ct, (cx - ct.get_width() // 2, VIRT_H - 30))
        # Remaining stars indicator
        left = self.total_count - self.spawned
        if left > 0:
            rem = fonts["small"].render(f"{left} left", False, GREY)
            screen.blit(rem, (cx - rem.get_width() // 2, VIRT_H - 20))

        lbl = fonts["big"].render(f"POT {self.pot}", False, WHITE)
        screen.blit(lbl, (cx - lbl.get_width() // 2, 22))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        if won:
            # Stars burst outward in celebration
            for i in range(12):
                a = t * 3 + i * math.pi * 2 / 12
                dist = t * 80
                sx = cx + int(math.cos(a) * dist)
                sy = cy + int(math.sin(a) * dist)
                if 0 < sx < VIRT_W and 0 < sy < VIRT_H:
                    pygame.draw.circle(screen, YELLOW, (sx, sy), 2)
            txt = fonts["huge"].render("STELLAR!", False, NEON_GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 30))
        else:
            # Stars fall and shatter on ground
            for i in range(5):
                fx = random.Random(i + 10).randint(30, VIRT_W - 30)
                fy = VIRT_H - 50 + int(t * 20)
                pygame.draw.line(screen, (80, 80, 40), (fx, fy), (fx + 3, fy + 3), 1)
                pygame.draw.line(screen, (80, 80, 40), (fx, fy), (fx - 3, fy + 2), 1)
            txt = fonts["huge"].render("MISSED!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 30))


# ── 11. Saw — alternate B1 and B2 rapidly ─────────────────
class SawGame(MicroGame):
    name = "SAW!"
    hint = "B1 & B2"
    base_duration = 5.0
    game_type = "action"
    bg_color = (25, 15, 5)

    def reset(self, snap=None, speed_mult=1.0):
        self.target_count = random.randint(6, 10)
        self.count = 0
        self.last_btn = 0
        self._b1_base = None
        self._b2_base = None
        self._prev_b1 = 0
        self._prev_b2 = 0
        self.saw_x = 0.0

    def update(self, snap, dt):
        b1 = snap["btn1_presses"]
        b2 = snap["btn2_presses"]
        if self._b1_base is None:
            self._b1_base = b1
            self._b2_base = b2
            self._prev_b1 = b1
            self._prev_b2 = b2
            return None
        # Detect new presses and check alternation
        if b1 != self._prev_b1 and self.last_btn != 1:
            self.count += 1
            self.last_btn = 1
        elif b2 != self._prev_b2 and self.last_btn != 2:
            self.count += 1
            self.last_btn = 2
        self._prev_b1 = b1
        self._prev_b2 = b2
        if self.count >= self.target_count:
            return True
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        pct = min(self.count / self.target_count, 1.0)

        # Workshop background
        # Floor
        pygame.draw.rect(screen, (50, 35, 18), (0, cy + 55, VIRT_W, VIRT_H - cy - 55))
        # Workbench
        bench_y = cy + 5
        pygame.draw.rect(screen, (90, 60, 25), (20, bench_y, VIRT_W - 40, 8))
        pygame.draw.rect(screen, (70, 45, 18), (20, bench_y, VIRT_W - 40, 8), 1)
        # Bench legs
        pygame.draw.rect(screen, (80, 55, 22), (30, bench_y + 8, 6, 45))
        pygame.draw.rect(screen, (80, 55, 22), (VIRT_W - 36, bench_y + 8, 6, 45))

        # Wall details
        for wx in range(0, VIRT_W, 30):
            pygame.draw.line(screen, (30, 20, 10), (wx, 0), (wx, bench_y), 1)

        # Log on bench — cylindrical with bark and rings
        log_x = cx - 40
        log_y = bench_y - 16
        log_w, log_h = 80, 16
        # Bark (outer)
        pygame.draw.rect(screen, (90, 55, 20), (log_x, log_y, log_w, log_h))
        pygame.draw.rect(screen, (70, 40, 15), (log_x, log_y, log_w, log_h), 1)
        # Bark texture lines
        for bx in range(log_x + 4, log_x + log_w - 4, 6):
            pygame.draw.line(screen, (70, 40, 15), (bx, log_y + 2),
                             (bx + 2, log_y + log_h - 2), 1)
        # End grain circles (left end)
        pygame.draw.ellipse(screen, (120, 80, 40), (log_x - 2, log_y + 1, 6, log_h - 2))
        for r in range(2, 7, 2):
            pygame.draw.ellipse(screen, (100, 65, 30),
                                (log_x - r // 2, log_y + log_h // 2 - r, r, r * 2), 1)

        # Cut progress — gap in the log
        cut_depth = int(pct * (log_h - 2))
        if cut_depth > 0:
            pygame.draw.rect(screen, self.bg_color,
                             (log_x, log_y, log_w, cut_depth))
            # Cut line
            pygame.draw.line(screen, (180, 150, 80), (log_x, log_y + cut_depth),
                             (log_x + log_w, log_y + cut_depth), 1)

        # Saw — moves left/right with alternation
        target_saw = -20.0 if self.last_btn == 1 else 20.0
        self.saw_x += (target_saw - self.saw_x) * 0.3
        saw_cx = cx + int(self.saw_x)
        saw_y = log_y + cut_depth - 2

        # Saw blade (zigzag teeth)
        pts = []
        for i in range(0, 54, 3):
            tooth_up = (i // 3) % 2 == 0
            pts.append((saw_cx - 27 + i, saw_y - (3 if tooth_up else 0)))
            pts.append((saw_cx - 27 + i + 1, saw_y + 2))
        if len(pts) > 1:
            pygame.draw.lines(screen, (180, 180, 190), False, pts, 1)
        # Saw blade body
        pygame.draw.rect(screen, (160, 160, 170), (saw_cx - 27, saw_y - 5, 54, 3))
        # Handle (wooden grip)
        pygame.draw.rect(screen, (139, 90, 43), (saw_cx + 24, saw_y - 10, 10, 14))
        pygame.draw.rect(screen, (120, 75, 35), (saw_cx + 24, saw_y - 10, 10, 14), 1)
        # Handle grip lines
        pygame.draw.line(screen, (100, 60, 28), (saw_cx + 26, saw_y - 8),
                         (saw_cx + 32, saw_y - 8), 1)
        pygame.draw.line(screen, (100, 60, 28), (saw_cx + 26, saw_y - 4),
                         (saw_cx + 32, saw_y - 4), 1)

        # Sawdust particles falling
        if pct > 0:
            for si in range(int(pct * 6)):
                seed = int(time.time() * 10) + si * 13
                dx = cx + random.Random(seed).randint(-30, 30)
                dy = log_y + cut_depth + random.Random(seed + 7).randint(2, 15)
                pygame.draw.rect(screen, (200, 160, 70), (dx, dy, 1, 1))

        # Progress counter
        ct = fonts["big"].render(f"{self.count}/{self.target_count}", False,
                                 GREEN if pct >= 1.0 else WHITE)
        screen.blit(ct, (cx - ct.get_width() // 2, cy + 60))

        # B1/B2 indicators — larger and more visible
        b1c = NEON_GREEN if self.last_btn == 1 else (60, 60, 60)
        b2c = NEON_GREEN if self.last_btn == 2 else (60, 60, 60)
        # B1 box
        pygame.draw.rect(screen, b1c, (15, 18, 30, 16), 0 if self.last_btn == 1 else 1)
        l1 = fonts["med"].render("B1", False, BLACK if self.last_btn == 1 else b1c)
        screen.blit(l1, (22, 20))
        # Arrow
        arr = fonts["big"].render("<->", False, YELLOW)
        screen.blit(arr, (cx - arr.get_width() // 2, 20))
        # B2 box
        pygame.draw.rect(screen, b2c, (VIRT_W - 45, 18, 30, 16), 0 if self.last_btn == 2 else 1)
        l2 = fonts["med"].render("B2", False, BLACK if self.last_btn == 2 else b2c)
        screen.blit(l2, (VIRT_W - 38, 20))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        bench_y = cy + 5
        log_y = bench_y - 16
        # Workbench
        pygame.draw.rect(screen, (90, 60, 25), (20, bench_y, VIRT_W - 40, 8))
        pygame.draw.rect(screen, (50, 35, 18), (0, cy + 55, VIRT_W, VIRT_H - cy - 55))
        pygame.draw.rect(screen, (80, 55, 22), (30, bench_y + 8, 6, 45))
        pygame.draw.rect(screen, (80, 55, 22), (VIRT_W - 36, bench_y + 8, 6, 45))
        if won:
            # Log splits in two halves falling off bench
            gap = int(t * 60)
            fall = int(t * 40)
            pygame.draw.rect(screen, (90, 55, 20),
                             (cx - 42 - gap, log_y + fall, 38, 16))
            pygame.draw.rect(screen, (90, 55, 20),
                             (cx + 4 + gap, log_y + fall, 38, 16))
            # Sawdust burst
            for i in range(15):
                seed = i * 37 + 11
                sx = cx + random.Random(seed).randint(-30, 30)
                sy = log_y - random.Random(seed + 3).randint(0, int(max(t, 0.01) * 40))
                pygame.draw.rect(screen, (200, 160, 70), (sx, sy, 2, 2))
            txt = fonts["huge"].render("TIMBER!", False, NEON_GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 50))
        else:
            # Saw stuck in log
            pygame.draw.rect(screen, (90, 55, 20), (cx - 40, log_y, 80, 16))
            pygame.draw.rect(screen, (160, 160, 170), (cx - 3, log_y - 2, 6, 8))
            shake = random.randint(-1, 1)
            pygame.draw.rect(screen, (160, 160, 170), (cx - 3 + shake, log_y - 2, 6, 8))
            txt = fonts["huge"].render("STUCK!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 50))


# ── 12. Dodge — avoid falling objects with pot ────────────
class DodgeGame(MicroGame):
    name = "DODGE!"
    base_duration = 30.0  # safety cap; game ends when wave is done
    game_type = "survive"
    wave_based = True
    bg_color = (10, 5, 20)

    def reset(self, snap=None, speed_mult=1.0):
        self.pot = random.choice([1, 2])
        self.smooth_x = float(VIRT_W // 2)
        self.total_count = random.randint(10, 16)
        self.spawned = 0
        self.obstacles = []
        self.spawn_timer = 0.0
        self.spawn_interval = max(0.15, 0.35 * speed_mult)
        self.fall_speed_lo = 100 / speed_mult
        self.fall_speed_hi = 180 / speed_mult
        self.grace = 0.3
        self.hint = f"POT {self.pot}"

    def update(self, snap, dt):
        if self.grace > 0:
            self.grace -= dt
            return None
        val = snap[f"pot{self.pot}"]
        target_x = 10 + (val / 4095) * (VIRT_W - 20)
        self.smooth_x += (target_x - self.smooth_x) * 0.2
        player_x = self.smooth_x
        player_y = VIRT_H - 50

        # Spawn obstacles up to total
        if self.spawned < self.total_count:
            self.spawn_timer += dt
            if self.spawn_timer >= self.spawn_interval:
                self.spawn_timer = 0
                self.obstacles.append([random.randint(15, VIRT_W - 15), -10.0,
                                       random.uniform(self.fall_speed_lo, self.fall_speed_hi)])
                self.spawned += 1

        # Move and check collisions
        for obs in self.obstacles:
            obs[1] += obs[2] * dt
            if abs(obs[0] - player_x) < 10 and abs(obs[1] - player_y) < 10:
                return False

        # Remove off-screen
        self.obstacles = [o for o in self.obstacles if o[1] < VIRT_H + 10]

        # All rocks spawned and fallen = survived!
        if self.spawned >= self.total_count and len(self.obstacles) == 0:
            return True
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        px = int(self.smooth_x)
        player_y = VIRT_H - 50

        # Falling rocks
        for obs in self.obstacles:
            ox, oy = int(obs[0]), int(obs[1])
            # Spiky rock
            pygame.draw.polygon(screen, (120, 80, 60), [
                (ox, oy - 6), (ox - 5, oy + 2),
                (ox - 3, oy + 5), (ox + 3, oy + 5), (ox + 5, oy + 2)])
            pygame.draw.polygon(screen, (90, 60, 40), [
                (ox, oy - 6), (ox - 5, oy + 2),
                (ox - 3, oy + 5), (ox + 3, oy + 5), (ox + 5, oy + 2)], 1)

        # Player character (little running person)
        pygame.draw.circle(screen, CYAN, (px, player_y - 8), 4)
        pygame.draw.line(screen, CYAN, (px, player_y - 4), (px, player_y + 4), 1)
        step = int(time.time() * 8) % 2
        pygame.draw.line(screen, CYAN, (px, player_y + 4),
                         (px - 3 + step * 6, player_y + 10), 1)
        pygame.draw.line(screen, CYAN, (px, player_y + 4),
                         (px + 3 - step * 6, player_y + 10), 1)
        # Arms up (panicking)
        pygame.draw.line(screen, CYAN, (px, player_y - 2),
                         (px - 5, player_y - 8), 1)
        pygame.draw.line(screen, CYAN, (px, player_y - 2),
                         (px + 5, player_y - 8), 1)

        # Ground
        pygame.draw.line(screen, (40, 40, 40), (0, player_y + 12),
                         (VIRT_W, player_y + 12), 1)

        lbl = fonts["big"].render(f"POT {self.pot}", False, WHITE)
        screen.blit(lbl, (cx - lbl.get_width() // 2, 22))
        # Rocks remaining indicator
        left = self.total_count - self.spawned + len(self.obstacles)
        rem = fonts["small"].render(f"{left} rocks", False, GREY)
        screen.blit(rem, (cx - rem.get_width() // 2, VIRT_H - 30))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        player_y = VIRT_H - 50
        if won:
            # Character does a victory dance
            dance = int(t * 10) % 2
            px = cx
            py = player_y - int(dance * 3)
            pygame.draw.circle(screen, CYAN, (px, py - 8), 4)
            pygame.draw.line(screen, CYAN, (px, py - 4), (px, py + 4), 1)
            arm_a = math.sin(t * 15) * 8
            pygame.draw.line(screen, CYAN, (px, py - 2),
                             (px - 5, py - 8 + int(arm_a)), 1)
            pygame.draw.line(screen, CYAN, (px, py - 2),
                             (px + 5, py - 8 - int(arm_a)), 1)
            txt = fonts["huge"].render("SAFE!", False, NEON_GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 30))
        else:
            # Rock bonks player — stars circle head
            pygame.draw.circle(screen, CYAN, (cx, player_y + 5), 4)
            pygame.draw.polygon(screen, (120, 80, 60), [
                (cx, player_y - 5), (cx - 5, player_y + 3),
                (cx + 5, player_y + 3)])
            for i in range(5):
                sa = t * 5 + i * math.pi * 2 / 5
                sx = cx + int(math.cos(sa) * 10)
                sy = player_y - 5 + int(math.sin(sa) * 6)
                pygame.draw.rect(screen, YELLOW, (sx, sy, 2, 2))
            txt = fonts["huge"].render("BONK!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 30))


# ── 13. Charge — hold and release in target zone ──────────
class ChargeGame(MicroGame):
    name = "CHARGE!"
    base_duration = 6.0
    game_type = "action"
    bg_color = (10, 8, 22)

    def reset(self, snap=None, speed_mult=1.0):
        self.btn = random.choice([1, 2])
        # Power bar sweeps up while holding; target zone is random
        zone_size = max(0.10, 0.18 * speed_mult)
        zone_center = random.uniform(0.35, 0.85)
        self.zone_lo = max(0, zone_center - zone_size / 2)
        self.zone_hi = min(1, zone_center + zone_size / 2)
        self.charge = 0.0
        self.charge_speed = max(0.3, 0.5 * speed_mult)
        # Engine applies duration = base_duration * speed_mult, so divide
        # to guarantee enough real time to reach past the target zone
        needed_time = self.zone_hi / self.charge_speed + 1.5
        self.base_duration = needed_time / speed_mult
        self.holding = False
        self.released = False
        self.result_pct = 0.0
        self.particles = []
        self.hint = f"B{self.btn}"

    def update(self, snap, dt):
        if self.released:
            return self.zone_lo <= self.result_pct <= self.zone_hi
        pressed = snap[f"btn{self.btn}"]
        if pressed:
            self.holding = True
            self.charge += self.charge_speed * dt
            if self.charge >= 1.0:
                self.charge = 1.0
                self.released = True
                self.result_pct = 1.0
        elif self.holding:
            # Released the button
            self.released = True
            self.result_pct = self.charge
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2

        # Battery body
        bat_w, bat_h = 50, 180
        bat_x = cx - bat_w // 2
        bat_y = cy - bat_h // 2 + 10
        # Terminal nub
        pygame.draw.rect(screen, GREY, (cx - 10, bat_y - 8, 20, 10))
        # Outer shell
        pygame.draw.rect(screen, (40, 40, 55), (bat_x, bat_y, bat_w, bat_h))
        pygame.draw.rect(screen, (70, 70, 85), (bat_x, bat_y, bat_w, bat_h), 2)

        # Target zone
        zone_y_top = bat_y + int((1 - self.zone_hi) * bat_h)
        zone_y_bot = bat_y + int((1 - self.zone_lo) * bat_h)
        in_zone = self.zone_lo <= self.charge <= self.zone_hi
        zc = (0, 120, 0) if in_zone else (0, 55, 0)
        pygame.draw.rect(screen, zc,
                         (bat_x + 2, zone_y_top, bat_w - 4,
                          zone_y_bot - zone_y_top))
        zbc = NEON_GREEN if in_zone else (40, 80, 40)
        pygame.draw.rect(screen, zbc,
                         (bat_x, zone_y_top, bat_w, zone_y_bot - zone_y_top), 1)

        # Charge fill
        fill_h = int(self.charge * bat_h)
        if fill_h > 0:
            fill_y = bat_y + bat_h - fill_h
            if self.charge > 0.85:
                fc = RED
            elif in_zone:
                fc = NEON_GREEN
            elif self.charge > 0.5:
                fc = YELLOW
            else:
                fc = CYAN
            pygame.draw.rect(screen, fc,
                             (bat_x + 3, fill_y, bat_w - 6, fill_h))
            # Shimmer lines
            for sy in range(fill_y + 4, bat_y + bat_h - 2, 8):
                sc = (min(255, fc[0] + 40), min(255, fc[1] + 40),
                      min(255, fc[2] + 40))
                pygame.draw.line(screen, sc, (bat_x + 5, sy),
                                 (bat_x + bat_w - 5, sy), 1)

        # Lightning bolt icon when charging
        if self.holding and not self.released:
            pulse = abs(math.sin(time.time() * 8))
            lc = (int(200 + pulse * 55), int(200 + pulse * 55), 0)
            bolt_x = cx
            bolt_y = bat_y - 22
            pygame.draw.polygon(screen, lc, [
                (bolt_x - 3, bolt_y), (bolt_x + 2, bolt_y + 6),
                (bolt_x, bolt_y + 6), (bolt_x + 3, bolt_y + 12),
                (bolt_x - 2, bolt_y + 6), (bolt_x, bolt_y + 6)])
            # Energy sparks
            for _ in range(2):
                self.particles.append([
                    bat_x + random.randint(3, bat_w - 3),
                    bat_y + bat_h - fill_h + random.randint(-5, 5),
                    random.randint(3, 6),
                    random.choice([YELLOW, CYAN, WHITE])])

        # Particles
        new_p = []
        for p in self.particles:
            p[0] += random.uniform(-1, 1)
            p[1] -= random.uniform(0.3, 1.2)
            p[2] -= 1
            if p[2] > 0:
                pygame.draw.rect(screen, p[3], (int(p[0]), int(p[1]), 2, 2))
                new_p.append(p)
        self.particles = new_p[-30:]

        # Percentage
        pct_val = int(self.charge * 100)
        pc = NEON_GREEN if in_zone else WHITE
        pct_txt = fonts["big"].render(f"{pct_val}%", False, pc)
        screen.blit(pct_txt, (cx - pct_txt.get_width() // 2,
                              bat_y + bat_h + 10))

        # Instructions
        if not self.holding and not self.released:
            txt = fonts["big"].render(f"HOLD B{self.btn}", False, YELLOW)
            screen.blit(txt, (cx - txt.get_width() // 2, 24))
        elif self.holding and not self.released:
            txt = fonts["big"].render("RELEASE!", False, ORANGE)
            screen.blit(txt, (cx - txt.get_width() // 2, 24))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        if won:
            # Battery powers up — lightning bolts radiate
            pygame.draw.rect(screen, NEON_GREEN,
                             (cx - 25, cy - 80, 50, 160))
            pygame.draw.rect(screen, WHITE,
                             (cx - 25, cy - 80, 50, 160), 2)
            for i in range(int(t * 16)):
                a = i * 0.8 + t * 5
                d = 30 + t * 60
                bx = cx + int(math.cos(a) * d)
                by = cy + int(math.sin(a) * d)
                if 0 < bx < VIRT_W and 20 < by < VIRT_H:
                    pygame.draw.polygon(screen,
                                        random.choice([YELLOW, WHITE, CYAN]), [
                        (bx, by - 3), (bx + 2, by + 1),
                        (bx, by + 1), (bx + 1, by + 4),
                        (bx - 1, by + 1), (bx, by + 1)])
            txt = fonts["huge"].render("CHARGED!", False, NEON_GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, cy + 100))
        else:
            # Overcharge or undercharge — battery sparks/fizzles
            pygame.draw.rect(screen, (40, 40, 55),
                             (cx - 25, cy - 80, 50, 160))
            if self.result_pct > self.zone_hi:
                # Overcharged — sparks
                for i in range(12):
                    a = random.uniform(0, math.pi * 2)
                    d = t * random.uniform(15, 60)
                    sx = cx + int(math.cos(a) * d)
                    sy = cy + int(math.sin(a) * d)
                    pygame.draw.rect(screen,
                                     random.choice([RED, ORANGE, YELLOW]),
                                     (sx, sy, 2, 2))
                txt = fonts["huge"].render("OVERLOAD!", False, RED)
            else:
                # Undercharged — fizzle
                for i in range(int(t * 6)):
                    sx = cx + random.randint(-20, 20)
                    sy = cy + 80 - int(i * 5 + t * 30)
                    if sy > cy - 80:
                        pygame.draw.circle(screen, (60, 60, 60),
                                           (sx, sy), random.randint(1, 3))
                txt = fonts["huge"].render("WEAK!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy + 100))


# ── 14. Combo — crack a combination lock ──────────────────
class ComboGame(MicroGame):
    name = "COMBO!"
    base_duration = 7.0
    game_type = "action"
    bg_color = (10, 10, 20)

    def _far_target(self, current):
        lo, hi = 600, 3500
        if current < 2048:
            return random.randint(max(lo, current + 800), hi)
        else:
            return random.randint(lo, min(hi, current - 800))

    def reset(self, snap=None, speed_mult=1.0):
        pots = [1, 2]
        btns = [1, 2]
        random.shuffle(pots)
        random.shuffle(btns)
        self.steps = []
        cur1 = snap[f"pot{pots[0]}"] if snap else 2048
        self.steps.append({"type": "pot", "num": pots[0],
                           "target": self._far_target(cur1), "tol": 350})
        self.steps.append({"type": "btn", "num": btns[0]})
        cur2 = snap[f"pot{pots[1]}"] if snap else 2048
        self.steps.append({"type": "pot", "num": pots[1],
                           "target": self._far_target(cur2), "tol": 350})
        self.current_step = 0
        self.grace = 0.35
        self.smooth_pot1 = float(snap["pot1"]) if snap else 2048.0
        self.smooth_pot2 = float(snap["pot2"]) if snap else 2048.0
        self.step_flash = 0.0
        self._update_hint()

    def _update_hint(self):
        if self.current_step < len(self.steps):
            s = self.steps[self.current_step]
            self.hint = f"POT {s['num']}" if s["type"] == "pot" else f"B{s['num']}"

    def update(self, snap, dt):
        if self.grace > 0:
            self.grace -= dt
            return None
        self.smooth_pot1 += (snap["pot1"] - self.smooth_pot1) * 0.15
        self.smooth_pot2 += (snap["pot2"] - self.smooth_pot2) * 0.15
        step = self.steps[self.current_step]
        done = False
        if step["type"] == "pot":
            val = self.smooth_pot1 if step["num"] == 1 else self.smooth_pot2
            if abs(val - step["target"]) < step["tol"]:
                done = True
        else:
            if snap[f"btn{step['num']}"]:
                done = True
        if done:
            self.current_step += 1
            self.step_flash = 0.3
            if self.current_step >= len(self.steps):
                return True
            self._update_hint()
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2 - 5
        self.step_flash = max(0, self.step_flash - 0.02)

        # Vault door
        vault_r = 50
        pygame.draw.circle(screen, (35, 35, 48), (cx, cy), vault_r)
        pygame.draw.circle(screen, (55, 55, 68), (cx, cy), vault_r, 2)
        pygame.draw.circle(screen, (28, 28, 38), (cx, cy), vault_r - 6, 1)
        for a_deg in range(0, 360, 45):
            a = math.radians(a_deg)
            bx = cx + int(math.cos(a) * (vault_r - 3))
            by = cy + int(math.sin(a) * (vault_r - 3))
            pygame.draw.circle(screen, (75, 75, 85), (bx, by), 2)

        # Step progress at top
        step_y = 26
        total_w = len(self.steps) * 28
        sx0 = cx - total_w // 2
        for i, step in enumerate(self.steps):
            sx = sx0 + i * 28 + 14
            if i < self.current_step:
                pygame.draw.circle(screen, NEON_GREEN, (sx, step_y), 8)
                pygame.draw.line(screen, BLACK, (sx - 3, step_y),
                                 (sx - 1, step_y + 3), 1)
                pygame.draw.line(screen, BLACK, (sx - 1, step_y + 3),
                                 (sx + 4, step_y - 3), 1)
            elif i == self.current_step:
                pulse = abs(math.sin(time.time() * 4))
                c = (int(255 * pulse), int(200 * pulse), 0)
                pygame.draw.circle(screen, c, (sx, step_y), 9, 2)
                num = fonts["med"].render(str(i + 1), False, YELLOW)
                screen.blit(num, (sx - num.get_width() // 2,
                                  step_y - num.get_height() // 2))
            else:
                pygame.draw.circle(screen, GREY, (sx, step_y), 8, 1)
                num = fonts["med"].render(str(i + 1), False, GREY)
                screen.blit(num, (sx - num.get_width() // 2,
                                  step_y - num.get_height() // 2))
            if i < len(self.steps) - 1:
                lc = NEON_GREEN if i < self.current_step else GREY
                pygame.draw.line(screen, lc, (sx + 9, step_y),
                                 (sx + 19, step_y), 1)

        # Current step display on vault face
        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            if step["type"] == "pot":
                pot_num = step["num"]
                target = step["target"]
                tol = step["tol"]
                current = self.smooth_pot1 if pot_num == 1 else self.smooth_pot2

                # Dial ring with target zone arc
                dial_r = 28
                t_lo = (target - tol) / 4095 * 360
                t_hi = (target + tol) / 4095 * 360
                for a_deg in range(int(t_lo), int(t_hi), 3):
                    a = math.radians(a_deg - 90)
                    px = cx + int(math.cos(a) * dial_r)
                    py = cy + int(math.sin(a) * dial_r)
                    pygame.draw.rect(screen, (0, 80, 0), (px, py, 2, 2))

                # Needle
                in_zone = abs(current - target) < tol
                cur_angle = math.radians((current / 4095) * 360 - 90)
                nx = cx + int(math.cos(cur_angle) * (dial_r - 4))
                ny = cy + int(math.sin(cur_angle) * (dial_r - 4))
                nc = NEON_GREEN if in_zone else ORANGE
                pygame.draw.line(screen, nc, (cx, cy), (nx, ny), 2)
                pygame.draw.circle(screen, nc, (nx, ny), 3)
                pygame.draw.circle(screen, WHITE, (cx, cy), 3)

                txt = fonts["big"].render(f"TURN POT {pot_num}", False, YELLOW)
                screen.blit(txt, (cx - txt.get_width() // 2, cy + vault_r + 12))
            else:
                btn_num = step["num"]
                pressed = snap[f"btn{btn_num}"]
                bc = NEON_GREEN if pressed else RED
                pygame.draw.circle(screen, bc, (cx, cy), 18)
                pygame.draw.circle(screen, WHITE, (cx, cy), 18, 1)
                num = fonts["giant"].render(str(btn_num), False, BLACK)
                screen.blit(num, (cx - num.get_width() // 2,
                                  cy - num.get_height() // 2))
                txt = fonts["big"].render(f"PRESS B{btn_num}", False, YELLOW)
                screen.blit(txt, (cx - txt.get_width() // 2, cy + vault_r + 12))

        # Step complete flash border
        if self.step_flash > 0:
            pygame.draw.rect(screen, NEON_GREEN, (0, 20, VIRT_W, VIRT_H - 20), 3)

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        vault_r = 50
        if won:
            open_pct = min(t / 0.4, 1.0)
            w = int(vault_r * 2 * max(0.1, 1 - open_pct * 0.8))
            pygame.draw.ellipse(screen, (35, 35, 48),
                                (cx - w // 2, cy - vault_r, w, vault_r * 2))
            if open_pct > 0.3:
                for i in range(10):
                    gx = cx + random.randint(-20, 20)
                    gy = cy + random.randint(-15, 15)
                    pygame.draw.rect(screen, YELLOW, (gx, gy, 3, 2))
            for i in range(int(t * 18)):
                a = i * 0.6 + t * 4
                d = 10 + t * 60
                sx = cx + int(math.cos(a) * d)
                sy = cy + int(math.sin(a) * d)
                if 0 < sx < VIRT_W and 20 < sy < VIRT_H:
                    pygame.draw.rect(screen, random.choice([YELLOW, WHITE, ORANGE]),
                                     (sx, sy, 2, 2))
            txt = fonts["huge"].render("CRACKED!", False, NEON_GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, cy + vault_r + 8))
        else:
            pygame.draw.circle(screen, (35, 35, 48), (cx, cy), vault_r)
            pygame.draw.circle(screen, RED, (cx, cy), vault_r, 2)
            pygame.draw.line(screen, RED, (cx - 15, cy - 15),
                             (cx + 15, cy + 15), 2)
            pygame.draw.line(screen, RED, (cx + 15, cy - 15),
                             (cx - 15, cy + 15), 2)
            if int(t * 8) % 2:
                pygame.draw.rect(screen, (60, 0, 0),
                                 (0, 20, VIRT_W, VIRT_H - 20), 3)
            txt = fonts["huge"].render("LOCKED!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy + vault_r + 8))


# ── 15. Rhythm — hit notes on beat ───────────────────────
class RhythmGame(MicroGame):
    name = "RHYTHM!"
    hint = "B1 & B2"
    base_duration = 30.0
    game_type = "action"
    wave_based = True
    bg_color = (8, 5, 18)

    def reset(self, snap=None, speed_mult=1.0):
        self.note_count = random.randint(6, 8) + max(0, int((1.0 - speed_mult) * 8))
        self.notes = []
        self.hit_y = VIRT_H - 65
        self.fall_speed = 110 / speed_mult
        self.spawn_interval = max(0.35, 0.55 * speed_mult)
        self.hit_window = max(22, int(33 * speed_mult))
        self.spawned = 0
        self.spawn_timer = 0.5  # initial delay
        self.hits = 0
        self.misses = 0
        self._b1_prev = snap["btn1_presses"] if snap else 0
        self._b2_prev = snap["btn2_presses"] if snap else 0
        self.flash_l = 0
        self.flash_r = 0
        self.particles = []

    def update(self, snap, dt):
        # Spawn notes
        if self.spawned < self.note_count:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_timer = self.spawn_interval
                btn = random.choice([1, 2])
                self.notes.append({"btn": btn, "y": -10.0,
                                   "hit": False, "missed": False})
                self.spawned += 1

        # Move notes
        for note in self.notes:
            if not note["hit"]:
                note["y"] += self.fall_speed * dt

        # Detect new button presses
        b1_new = snap["btn1_presses"] != self._b1_prev
        b2_new = snap["btn2_presses"] != self._b2_prev
        self._b1_prev = snap["btn1_presses"]
        self._b2_prev = snap["btn2_presses"]

        # Check hits
        for btn_num, pressed in [(1, b1_new), (2, b2_new)]:
            if not pressed:
                continue
            best = None
            best_dist = float("inf")
            for note in self.notes:
                if note["btn"] == btn_num and not note["hit"] and not note["missed"]:
                    dist = abs(note["y"] - self.hit_y)
                    if dist < self.hit_window and dist < best_dist:
                        best = note
                        best_dist = dist
            if best:
                best["hit"] = True
                self.hits += 1
                if btn_num == 1:
                    self.flash_l = 0.2
                else:
                    self.flash_r = 0.2
                lane_x = VIRT_W // 4 if btn_num == 1 else 3 * VIRT_W // 4
                for _ in range(5):
                    self.particles.append([lane_x + random.randint(-8, 8),
                                          self.hit_y + random.randint(-5, 5),
                                          random.uniform(-20, 20),
                                          random.uniform(-40, -10), 0.4,
                                          random.choice([NEON_GREEN, CYAN, WHITE])])

        # Check misses
        for note in self.notes:
            if not note["hit"] and not note["missed"]:
                if note["y"] > self.hit_y + self.hit_window + 5:
                    note["missed"] = True
                    self.misses += 1

        # Update particles
        new_p = []
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
            if p[4] > 0:
                new_p.append(p)
        self.particles = new_p

        self.flash_l = max(0, self.flash_l - dt)
        self.flash_r = max(0, self.flash_r - dt)

        # End condition
        all_done = (self.spawned >= self.note_count and
                    all(n["hit"] or n["missed"] for n in self.notes))
        if all_done:
            target = max(1, int(self.note_count * 0.6))
            return self.hits >= target
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx = VIRT_W // 2
        lane_l = VIRT_W // 4
        lane_r = 3 * VIRT_W // 4
        lane_w = 30

        # Lane backgrounds
        pygame.draw.rect(screen, (15, 12, 30),
                         (lane_l - lane_w // 2, 40, lane_w, VIRT_H - 60))
        pygame.draw.rect(screen, (15, 12, 30),
                         (lane_r - lane_w // 2, 40, lane_w, VIRT_H - 60))
        pygame.draw.rect(screen, (30, 25, 55),
                         (lane_l - lane_w // 2, 40, lane_w, VIRT_H - 60), 1)
        pygame.draw.rect(screen, (30, 25, 55),
                         (lane_r - lane_w // 2, 40, lane_w, VIRT_H - 60), 1)

        # Hit zone lines
        hc_l = NEON_GREEN if self.flash_l > 0 else (40, 80, 40)
        hc_r = NEON_GREEN if self.flash_r > 0 else (40, 80, 40)
        pygame.draw.line(screen, hc_l,
                         (lane_l - lane_w // 2, self.hit_y),
                         (lane_l + lane_w // 2, self.hit_y), 2)
        pygame.draw.line(screen, hc_r,
                         (lane_r - lane_w // 2, self.hit_y),
                         (lane_r + lane_w // 2, self.hit_y), 2)

        # Notes (diamond shapes)
        for note in self.notes:
            if note["hit"]:
                continue
            lx = lane_l if note["btn"] == 1 else lane_r
            ny = int(note["y"])
            if ny < 30 or ny > VIRT_H:
                continue
            c = CYAN if note["btn"] == 1 else PINK
            if note["missed"]:
                c = (60, 30, 30)
            pygame.draw.polygon(screen, c, [
                (lx, ny - 6), (lx + 6, ny), (lx, ny + 6), (lx - 6, ny)])
            pygame.draw.polygon(screen, WHITE, [
                (lx, ny - 6), (lx + 6, ny), (lx, ny + 6), (lx - 6, ny)], 1)

        # Particles
        for p in self.particles:
            pygame.draw.rect(screen, p[5], (int(p[0]), int(p[1]), 2, 2))

        # Lane labels
        b1l = fonts["big"].render("B1", False, CYAN)
        b2l = fonts["big"].render("B2", False, PINK)
        screen.blit(b1l, (lane_l - b1l.get_width() // 2, 24))
        screen.blit(b2l, (lane_r - b2l.get_width() // 2, 24))

        # Score
        target = max(1, int(self.note_count * 0.6))
        sc = fonts["big"].render(f"{self.hits}/{target}", False,
                                 NEON_GREEN if self.hits >= target else WHITE)
        screen.blit(sc, (cx - sc.get_width() // 2, VIRT_H - 30))

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        if won:
            note_chars = ["*", "~", ".", "*"]
            for i in range(int(t * 20)):
                a = i * 0.7 + t * 5
                d = 15 + i * 3 + t * 40
                nx = cx + int(math.cos(a) * d)
                ny = cy + int(math.sin(a) * d * 0.7)
                if 0 < nx < VIRT_W and 20 < ny < VIRT_H:
                    nc = [CYAN, PINK, NEON_GREEN, YELLOW, WHITE][i % 5]
                    nt = fonts["med"].render(note_chars[i % 4], False, nc)
                    screen.blit(nt, (nx, ny))
            txt = fonts["huge"].render("GROOVY!", False, NEON_GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 15))
        else:
            for i in range(8):
                fx = random.Random(i + 5).randint(30, VIRT_W - 30)
                fy = VIRT_H - 50 + int(t * 30)
                pygame.draw.polygon(screen, (60, 30, 30), [
                    (fx, fy - 4), (fx + 4, fy), (fx, fy + 4), (fx - 4, fy)])
            txt = fonts["huge"].render("OFF BEAT!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 15))


# ── 16. Mirror — match both pots to target zones ─────────
class MirrorGame(MicroGame):
    name = "MIRROR!"
    hint = "POT 1 + POT 2"
    base_duration = 6.0
    game_type = "action"
    bg_color = (12, 5, 20)

    def reset(self, snap=None, speed_mult=1.0):
        self.targets = []
        for pot_num in [1, 2]:
            current = snap[f"pot{pot_num}"] if snap else 2048
            lo, hi = 500, 3600
            if current < 2048:
                t = random.randint(max(lo, current + 900), hi)
            else:
                t = random.randint(lo, min(hi, current - 900))
            self.targets.append({"pot": pot_num, "target": t,
                                 "tol": max(250, int(350 * speed_mult))})
        self.grace = 0.4
        self.smooth_pot1 = float(snap["pot1"]) if snap else 2048.0
        self.smooth_pot2 = float(snap["pot2"]) if snap else 2048.0
        self.match_timer = 0.0
        self.sparkles = []

    def update(self, snap, dt):
        if self.grace > 0:
            self.grace -= dt
            return None
        self.smooth_pot1 += (snap["pot1"] - self.smooth_pot1) * 0.15
        self.smooth_pot2 += (snap["pot2"] - self.smooth_pot2) * 0.15
        all_match = True
        for t in self.targets:
            val = self.smooth_pot1 if t["pot"] == 1 else self.smooth_pot2
            if abs(val - t["target"]) >= t["tol"]:
                all_match = False
                break
        if all_match:
            self.match_timer += dt
            if self.match_timer >= 0.3:
                return True
        else:
            self.match_timer = 0.0
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2

        title = fonts["big"].render("MATCH BOTH!", False, YELLOW)
        screen.blit(title, (cx - title.get_width() // 2, 24))

        # Two vertical gauge bars
        bar_h = 220
        bar_w = 20
        bar_y = 50
        gap = 50
        bar1_x = cx - gap - bar_w
        bar2_x = cx + gap

        for i, (bx, smooth_val) in enumerate([
                (bar1_x, self.smooth_pot1), (bar2_x, self.smooth_pot2)]):
            t = self.targets[i]
            target = t["target"]
            tol = t["tol"]
            pot_num = t["pot"]
            current = smooth_val

            # Bar background
            pygame.draw.rect(screen, (20, 15, 35), (bx, bar_y, bar_w, bar_h))
            pygame.draw.rect(screen, (40, 35, 60), (bx, bar_y, bar_w, bar_h), 1)

            # Target zone
            t_lo = max(0, (target - tol) / 4095)
            t_hi = min(1, (target + tol) / 4095)
            zone_y_top = bar_y + int((1 - t_hi) * bar_h)
            zone_y_bot = bar_y + int((1 - t_lo) * bar_h)
            in_zone = abs(current - target) < tol
            zc = (0, 140, 0) if in_zone else (0, 60, 0)
            pygame.draw.rect(screen, zc,
                             (bx + 1, zone_y_top, bar_w - 2,
                              zone_y_bot - zone_y_top))
            zbc = NEON_GREEN if in_zone else (40, 80, 40)
            pygame.draw.rect(screen, zbc,
                             (bx, zone_y_top, bar_w, zone_y_bot - zone_y_top), 1)

            # Current position indicator (arrow + line)
            cur_pct = current / 4095
            cur_y = bar_y + int((1 - cur_pct) * bar_h)
            ic = NEON_GREEN if in_zone else ORANGE
            if i == 0:
                pygame.draw.polygon(screen, ic, [
                    (bx - 2, cur_y), (bx - 8, cur_y - 4),
                    (bx - 8, cur_y + 4)])
            else:
                pygame.draw.polygon(screen, ic, [
                    (bx + bar_w + 2, cur_y),
                    (bx + bar_w + 8, cur_y - 4),
                    (bx + bar_w + 8, cur_y + 4)])
            pygame.draw.line(screen, ic, (bx + 1, cur_y),
                             (bx + bar_w - 1, cur_y), 2)

            # Pot label
            lbl = fonts["big"].render(f"P{pot_num}", False, WHITE)
            screen.blit(lbl, (bx + bar_w // 2 - lbl.get_width() // 2,
                              bar_y + bar_h + 6))
            pct_val = int(cur_pct * 100)
            pct_txt = fonts["med"].render(f"{pct_val}%", False, ic)
            screen.blit(pct_txt, (bx + bar_w // 2 - pct_txt.get_width() // 2,
                                  bar_y + bar_h + 20))

        # Center match indicator
        all_match = all(
            abs((self.smooth_pot1 if t["pot"] == 1 else self.smooth_pot2)
                - t["target"]) < t["tol"]
            for t in self.targets)
        if all_match:
            pulse = abs(math.sin(time.time() * 6))
            mc = (int(50 + pulse * 200), int(255 * pulse),
                  int(50 + pulse * 100))
            pygame.draw.circle(screen, mc, (cx, cy), 8)
            match_pct = min(self.match_timer / 0.3, 1.0)
            fill_h = int(16 * match_pct)
            if fill_h > 0:
                pygame.draw.rect(screen, NEON_GREEN,
                                 (cx - 7, cy + 8 - fill_h, 14, fill_h))
            mt = fonts["med"].render("HOLD!", False, NEON_GREEN)
            screen.blit(mt, (cx - mt.get_width() // 2, cy + 14))
            for _ in range(2):
                self.sparkles.append([cx + random.randint(-15, 15),
                                     cy + random.randint(-10, 10),
                                     random.randint(3, 6),
                                     random.choice([NEON_GREEN, CYAN, WHITE])])
        else:
            pygame.draw.circle(screen, GREY, (cx, cy), 8, 1)

        # Sparkles
        new_sp = []
        for sp in self.sparkles:
            sp[0] += random.uniform(-1, 1)
            sp[1] -= random.uniform(0.3, 1)
            sp[2] -= 1
            if sp[2] > 0:
                pygame.draw.rect(screen, sp[3],
                                 (int(sp[0]), int(sp[1]), 2, 2))
                new_sp.append(sp)
        self.sparkles = new_sp[-25:]

    def animate_result(self, screen, won, t, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        if won:
            for i in range(int(t * 25)):
                a = i * 0.5 + t * 6
                d = t * 70
                sx = cx + int(math.cos(a) * d)
                sy = cy + int(math.sin(a) * d)
                if 0 < sx < VIRT_W and 20 < sy < VIRT_H:
                    pygame.draw.rect(screen,
                                     random.choice([NEON_GREEN, CYAN, WHITE]),
                                     (sx, sy, 2, 2))
            txt = fonts["huge"].render("MATCHED!", False, NEON_GREEN)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 15))
        else:
            for bx in [cx - 70, cx + 50]:
                pygame.draw.rect(screen, (60, 20, 20), (bx, 50, 20, 220))
                if int(t * 6) % 2:
                    pygame.draw.rect(screen, RED, (bx, 50, 20, 220), 2)
            txt = fonts["huge"].render("WRONG!", False, RED)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - 15))


# ── All game instances ────────────────────────────────────
ALL_GAMES = [
    DontTouchGame(),
    PotMaxGame(),
    PotMinGame(),
    MatchTargetGame(),
    MashGame(),
    HoldGame(),
    QuickDrawGame(),
    CatchGame(),
    SawGame(),
    DodgeGame(),
    ChargeGame(),
    ComboGame(),
    RhythmGame(),
    MirrorGame(),
]


# ═══════════════════════════════════════════════════════════
#  GAME ENGINE
# ═══════════════════════════════════════════════════════════
class GameEngine:
    def __init__(self, serial_port="/dev/ttyACM0"):
        self.serial_port = serial_port
        self.state = HardwareState()
        self.comm = None

        pygame.init()
        self.real_screen = pygame.display.set_mode(
            (SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
        # Virtual low-res surface — everything draws here
        self.screen = pygame.Surface((VIRT_W, VIRT_H))
        pygame.display.set_caption("PiWare")
        self.clock = pygame.time.Clock()

        # Pixel-sized fonts for virtual resolution
        bold_ttf = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        self.fonts = {
            "small": pygame.font.Font(bold_ttf, 8),
            "med":   pygame.font.Font(bold_ttf, 11),
            "big":   pygame.font.Font(bold_ttf, 14),
            "huge":  pygame.font.Font(bold_ttf, 20),
            "giant": pygame.font.Font(bold_ttf, 28),
            "title": pygame.font.Font(bold_ttf, 24),
        }

        # Touch input
        self.touch_queue = []
        self.touch_res_x, self.touch_res_y = SCREEN_W, SCREEN_H
        td = find_touch_device()
        if td:
            caps = td.capabilities(absinfo=True)
            for code, absinfo in caps.get(ecodes.EV_ABS, []):
                if code in (ecodes.ABS_MT_POSITION_X, ecodes.ABS_X):
                    self.touch_res_x = absinfo.max
                elif code in (ecodes.ABS_MT_POSITION_Y, ecodes.ABS_Y):
                    self.touch_res_y = absinfo.max
            threading.Thread(
                target=touch_reader, args=(td, self.touch_queue), daemon=True
            ).start()
        else:
            print("Warning: no touchscreen found, touch input disabled.")

    # ── helpers ───────────────────────────────────────────
    def flip(self):
        """Scale virtual surface to real screen with nearest-neighbor."""
        pygame.transform.scale(self.screen, (SCREEN_W, SCREEN_H),
                               self.real_screen)
        pygame.display.flip()

    def get_touches(self):
        touches = []
        while self.touch_queue:
            rx, ry = self.touch_queue.pop(0)
            # Map to virtual coordinates
            touches.append((
                int(rx * VIRT_W / self.touch_res_x),
                int(ry * VIRT_H / self.touch_res_y),
            ))
        return touches

    def check_quit(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return True
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return True
        return False

    def center_text(self, text, font_key, color, y):
        txt = self.fonts[font_key].render(text, False, color)
        self.screen.blit(
            txt, (VIRT_W // 2 - txt.get_width() // 2, y))

    def set_led(self, color, on):
        if self.comm:
            self.comm.set_led(color, on)

    def all_leds_off(self):
        for c in ("r", "g", "b"):
            self.set_led(c, False)

    # ── LED feedback (runs in background thread) ──────────
    def _led_flash(self, color, times=3, on_time=0.08, off_time=0.08):
        for _ in range(times):
            self.set_led(color, True)
            time.sleep(on_time)
            self.set_led(color, False)
            time.sleep(off_time)

    def led_win(self):
        threading.Thread(
            target=self._led_flash, args=("g",), daemon=True).start()

    def led_lose(self):
        threading.Thread(
            target=self._led_flash, args=("r",), daemon=True).start()

    # ── draw: timer bar at top (retro segmented) ───────────
    def draw_timer(self, time_left, time_total):
        bar_h = 7
        pct = max(time_left / time_total, 0)
        segments = 12
        seg_w = (VIRT_W - 2) // segments
        filled = int(segments * pct)
        if pct > 0.5:
            color = NEON_GREEN
        elif pct > 0.25:
            color = YELLOW
        else:
            color = RED
        pygame.draw.rect(self.screen, (10, 10, 20), (0, 0, VIRT_W, bar_h))
        for i in range(filled):
            x = 1 + i * seg_w
            pygame.draw.rect(self.screen, color,
                             (x, 1, seg_w - 1, bar_h - 2))

    # ── draw: HUD (score + lives + speed) — retro ──────────
    def draw_hud(self, score, lives, speed_level):
        y = 9
        score_txt = f"SC:{score:04d}"
        draw_glow_text(self.screen, score_txt, self.fonts["small"],
                       NEON_GREEN, (4, y), (0, 100, 0))
        # Lives as pixel squares
        for i in range(3):
            hx = VIRT_W - 10 - i * 12
            color = RED if i < lives else (40, 10, 10)
            pygame.draw.rect(self.screen, color, (hx, y + 1, 8, 8))
        if speed_level > 1:
            sp = f"LV{speed_level}"
            draw_glow_text(self.screen, sp, self.fonts["small"],
                           YELLOW, (VIRT_W // 2 - 10, y), (80, 80, 0))

    # ── full-screen flash (retro) ────────────────────────────
    def flash_screen(self, text, color, bg, duration=0.8, subtitle=""):
        start = time.time()
        while time.time() - start < duration:
            if self.check_quit():
                return
            self.screen.fill(bg)
            cx, cy = VIRT_W // 2, VIRT_H // 2
            draw_glow_text(self.screen, text, self.fonts["giant"], color,
                           (cx - self.fonts["giant"].size(text)[0] // 2,
                            cy - self.fonts["giant"].size(text)[1] // 2 - 8),
                           glow_radius=1)
            if subtitle:
                st = self.fonts["big"].render(subtitle, False, WHITE)
                self.screen.blit(st, (cx - st.get_width() // 2,
                                      cy + self.fonts["giant"].size(text)[1] // 2))
            self.flip()
            self.clock.tick(FPS)

    def flash_win(self, duration=0.55):
        """Animated win screen with expanding rings and confetti."""
        start = time.time()
        confetti = [[random.randint(0, VIRT_W), random.randint(-20, -5),
                      random.uniform(0.5, 2.5), random.uniform(-0.5, 0.5),
                      random.choice([YELLOW, CYAN, PINK, NEON_GREEN, ORANGE, WHITE])]
                    for _ in range(40)]
        while time.time() - start < duration:
            if self.check_quit():
                return
            t = time.time() - start
            self.screen.fill((10, 50, 10))
            cx, cy = VIRT_W // 2, VIRT_H // 2

            # Expanding rings
            for i in range(3):
                r = int((t * 120 + i * 25) % 100)
                alpha_pct = max(0, 1.0 - r / 100)
                c = (int(50 * alpha_pct), int(255 * alpha_pct), int(100 * alpha_pct))
                pygame.draw.circle(self.screen, c, (cx, cy), r, 1)

            # Confetti
            for p in confetti:
                p[0] += p[3]
                p[1] += p[2]
                if p[1] < VIRT_H:
                    pygame.draw.rect(self.screen, p[4],
                                     (int(p[0]), int(p[1]), 2, 2))

            # Checkmark
            scale = min(t / 0.2, 1.0)
            if scale > 0:
                pts = [(cx - int(12 * scale), cy),
                       (cx - int(3 * scale), cy + int(10 * scale)),
                       (cx + int(14 * scale), cy - int(10 * scale))]
                pygame.draw.lines(self.screen, NEON_GREEN, False, pts, 3)

            draw_glow_text(self.screen, "WIN!", self.fonts["giant"], GREEN,
                           (cx - self.fonts["giant"].size("WIN!")[0] // 2,
                            cy - 50),
                           (0, 100, 0), 1)
            self.flip()
            self.clock.tick(FPS)

    def flash_lose(self, duration=0.65):
        """Animated lose screen with screen shake and cracks."""
        start = time.time()
        while time.time() - start < duration:
            if self.check_quit():
                return
            t = time.time() - start
            # Screen shake (decays over time)
            shake = max(0, int(4 * (1 - t / duration)))
            ox = random.randint(-shake, shake) if shake > 0 else 0
            oy = random.randint(-shake, shake) if shake > 0 else 0

            self.screen.fill((50, 10, 10))
            cx, cy = VIRT_W // 2 + ox, VIRT_H // 2 + oy

            # Cracks radiating from center
            crack_len = min(t / 0.15, 1.0) * 60
            for angle_deg in range(0, 360, 45):
                angle = math.radians(angle_deg + random.randint(-5, 5))
                ex = cx + int(math.cos(angle) * crack_len)
                ey = cy + int(math.sin(angle) * crack_len)
                pygame.draw.line(self.screen, (120, 30, 30),
                                 (cx, cy), (ex, ey), 1)

            # Big X
            xs = int(min(t / 0.2, 1.0) * 20)
            pygame.draw.line(self.screen, RED,
                             (cx - xs, cy - xs), (cx + xs, cy + xs), 3)
            pygame.draw.line(self.screen, RED,
                             (cx + xs, cy - xs), (cx - xs, cy + xs), 3)

            draw_glow_text(self.screen, "LOSE!", self.fonts["giant"], RED,
                           (cx - self.fonts["giant"].size("LOSE!")[0] // 2,
                            cy - 55),
                           (100, 0, 0), 1)
            self.flip()
            self.clock.tick(FPS)

    # ══════════════════════════════════════════════════════
    #  SCREENS
    # ══════════════════════════════════════════════════════

    # ── MENU SCREEN ───────────────────────────────────────
    def run_menu(self):
        """Returns 'serial', 'wifi', or 'lte'."""
        btn_w, btn_h = 190, 30
        gap = 8
        x0 = (VIRT_W - btn_w) // 2
        y0 = 195

        buttons = [
            ("serial", ">> SERIAL <<",  NEON_BLUE,  x0, y0),
            ("wifi",   ">> WiFi <<",    NEON_GREEN, x0, y0 + btn_h + gap),
            ("lte",    ">> LTE <<",     ORANGE,     x0, y0 + 2 * (btn_h + gap)),
        ]

        # Load high scores for display
        hi_scores = load_highscores()
        hi_top = hi_scores[0] if hi_scores else 0

        frame = 0
        while True:
            if self.check_quit():
                pygame.quit()
                sys.exit()

            for tx, ty in self.get_touches():
                for mode, _lbl, _c, bx, by in buttons:
                    if pygame.Rect(bx, by, btn_w, btn_h).collidepoint(tx, ty):
                        return mode

            self.screen.fill(MENU_BG)
            frame += 1

            # Retro grid background
            grid_c = (15, 15, 35)
            for gx in range(0, VIRT_W, 14):
                pygame.draw.line(self.screen, grid_c, (gx, 0), (gx, VIRT_H))
            for gy in range(0, VIRT_H, 14):
                offset = (frame // 2) % 14
                pygame.draw.line(self.screen, grid_c,
                                 (0, gy + offset), (VIRT_W, gy + offset))

            # Title with glow
            cx = VIRT_W // 2
            title_font = self.fonts["title"]
            pw = title_font.size("PiWare")[0]
            draw_glow_text(self.screen, "PiWare", title_font, CYAN,
                           (cx - pw // 2, 50), (0, 80, 100), 1)

            # Subtitle
            sub = self.fonts["med"].render("MICRO ARCADE", False, YELLOW)
            self.screen.blit(sub, (cx - sub.get_width() // 2, 88))

            # Animated stars
            for i in range(8):
                sx = int(30 + i * 25 + math.sin(time.time() * 2 + i) * 3)
                sy = int(120 + math.cos(time.time() * 3 + i * 1.3) * 3)
                blink = int(time.time() * 5 + i) % 3
                if blink != 0:
                    sc = [YELLOW, CYAN, PINK, NEON_GREEN, ORANGE, PURPLE, RED, WHITE][i]
                    pygame.draw.rect(self.screen, sc, (sx, sy, 1, 1))

            # High score display
            if hi_top > 0:
                hs_txt = f"HI-SCORE: {hi_top:04d}"
                draw_glow_text(self.screen, hs_txt, self.fonts["small"],
                               YELLOW, (cx - self.fonts["small"].size(hs_txt)[0] // 2, 140),
                               (80, 80, 0))

            # Connection mode label
            sel = self.fonts["small"].render("[ SELECT MODE ]", False, GREY)
            self.screen.blit(sel, (cx - sel.get_width() // 2, 170))

            # Buttons — retro pixel style
            for mode, label, color, bx, by in buttons:
                rect = pygame.Rect(bx, by, btn_w, btn_h)
                # Dark fill
                pygame.draw.rect(self.screen, (color[0] // 8, color[1] // 8, color[2] // 8), rect)
                # Neon border
                draw_pixel_border(self.screen, rect, color, 1)
                # Label
                txt = self.fonts["med"].render(label, False, color)
                self.screen.blit(
                    txt,
                    (bx + btn_w // 2 - txt.get_width() // 2,
                     by + btn_h // 2 - txt.get_height() // 2))

            # Footer
            foot = self.fonts["small"].render("ESP32 + RPi", False,
                                              (40, 40, 60))
            self.screen.blit(foot, (cx - foot.get_width() // 2, VIRT_H - 12))

            self.flip()
            self.clock.tick(FPS)

    # ── WAITING FOR CONNECTION ────────────────────────────
    def wait_for_connection(self):
        dots = 0
        last_dot = time.time()
        frame = 0
        while True:
            if self.check_quit():
                return False
            snap = self.state.snapshot()
            if snap["connected"]:
                return True
            if time.time() - last_dot > 0.4:
                dots = (dots + 1) % 4
                last_dot = time.time()
            frame += 1
            self.screen.fill(BG)
            # Spinning pixel animation
            cx, cy = VIRT_W // 2, VIRT_H // 2 - 30
            for i in range(8):
                angle = (frame * 3 + i * 45) * math.pi / 180
                px = cx + int(math.cos(angle) * 20)
                py = cy + int(math.sin(angle) * 20)
                alpha = 255 if i < (frame // 4) % 8 else 60
                c = (0, alpha, alpha)
                pygame.draw.rect(self.screen, c, (px - 2, py - 2, 4, 4))
            txt = "LINKING" + "." * dots
            draw_glow_text(self.screen, txt, self.fonts["big"], CYAN,
                           (cx - self.fonts["big"].size(txt)[0] // 2, cy + 35),
                           (0, 60, 80))
            sub = self.fonts["small"].render("Waiting for ESP32...", False, GREY)
            self.screen.blit(sub, (cx - sub.get_width() // 2, cy + 55))
            self.flip()
            self.clock.tick(FPS)

    # ── TITLE / READY SCREEN ─────────────────────────────
    def title_screen(self):
        """Returns 'arcade', 'practice', or False (quit)."""
        blink = True
        last_blink = time.time()
        time.sleep(0.3)
        frame = 0
        # Two touch buttons
        btn_w, btn_h = 160, 26
        cx = VIRT_W // 2
        arcade_rect = pygame.Rect(cx - btn_w // 2, 200, btn_w, btn_h)
        practice_rect = pygame.Rect(cx - btn_w // 2, 236, btn_w, btn_h)

        # Debounce: use press counters, not raw button state
        _snap0 = self.state.snapshot()
        _prev_b1 = _snap0["btn1_presses"]
        _prev_b2 = _snap0["btn2_presses"]

        while True:
            if self.check_quit():
                return False
            touches = self.get_touches()
            snap = self.state.snapshot()
            # Detect NEW presses only
            b1_new = snap["btn1_presses"] != _prev_b1
            b2_new = snap["btn2_presses"] != _prev_b2
            _prev_b1 = snap["btn1_presses"]
            _prev_b2 = snap["btn2_presses"]
            if b1_new:
                return "arcade"
            if b2_new:
                return "practice"
            for tx, ty in touches:
                if arcade_rect.collidepoint(tx, ty):
                    return "arcade"
                if practice_rect.collidepoint(tx, ty):
                    return "practice"

            if time.time() - last_blink > 0.4:
                blink = not blink
                last_blink = time.time()
            frame += 1

            self.screen.fill(MENU_BG)

            # Retro starfield
            for i in range(20):
                sx = (i * 137 + frame * (i % 3 + 1)) % VIRT_W
                sy = (i * 89 + frame * (i % 2 + 1)) % VIRT_H
                pygame.draw.rect(self.screen, (60, 60, 80), (sx, sy, 1, 1))

            pw = self.fonts["title"].size("PiWare")[0]
            draw_glow_text(self.screen, "PiWare", self.fonts["title"], CYAN,
                           (cx - pw // 2, 60), (0, 80, 100), 1)

            sub = self.fonts["med"].render("MICRO ARCADE", False, YELLOW)
            self.screen.blit(sub, (cx - sub.get_width() // 2, 100))

            # Mode selection label
            sel = self.fonts["small"].render("[ SELECT MODE ]", False, GREY)
            self.screen.blit(sel, (cx - sel.get_width() // 2, 180))

            # Arcade button (B1)
            pygame.draw.rect(self.screen, (0, 10, 30), arcade_rect)
            draw_pixel_border(self.screen, arcade_rect, NEON_GREEN, 1)
            atxt = self.fonts["med"].render("B1  ARCADE", False, NEON_GREEN)
            self.screen.blit(atxt, (cx - atxt.get_width() // 2,
                                    arcade_rect.y + btn_h // 2 - atxt.get_height() // 2))

            # Practice button (B2)
            pygame.draw.rect(self.screen, (15, 10, 25), practice_rect)
            draw_pixel_border(self.screen, practice_rect, CYAN, 1)
            ptxt = self.fonts["med"].render("B2  PRACTICE", False, CYAN)
            self.screen.blit(ptxt, (cx - ptxt.get_width() // 2,
                                    practice_rect.y + btn_h // 2 - ptxt.get_height() // 2))

            # High scores
            hi_scores = load_highscores()
            if hi_scores:
                ht = self.fonts["small"].render("- HIGH SCORES -", False, YELLOW)
                self.screen.blit(ht, (cx - ht.get_width() // 2, 280))
                for i, sc in enumerate(hi_scores[:5]):
                    rank_colors = [YELLOW, WHITE, ORANGE, GREY, GREY]
                    entry = f"{i + 1}. {sc:04d}"
                    et = self.fonts["small"].render(entry, False, rank_colors[i])
                    self.screen.blit(et, (cx - et.get_width() // 2, 298 + i * 16))

            if blink:
                ins = self.fonts["small"].render("PRESS B1 OR B2", False, (60, 60, 80))
                self.screen.blit(ins, (cx - ins.get_width() // 2, VIRT_H - 20))

            self.flip()
            self.clock.tick(FPS)

    # ── PRACTICE SELECT SCREEN ────────────────────────────
    def practice_select_screen(self):
        """Select a minigame and difficulty. Returns (game_idx, speed_mult) or None."""
        selected = 0
        level = 1  # 1–13, matching arcade speed levels exactly
        scroll_y = 0.0
        _prev_b1 = 0
        _prev_b2 = 0
        _first_snap = True

        max_level = 13
        games = ALL_GAMES
        item_h = 22
        visible_items = 12
        cx = VIRT_W // 2

        def level_to_mult(lv):
            # Exact arcade formula: speed_mult = max(0.4, 1.0 - (level-1)*0.05)
            return max(0.4, 1.0 - (lv - 1) * 0.05)

        def level_color(lv):
            # Green → Yellow → Orange → Red
            frac = (lv - 1) / (max_level - 1)
            if frac < 0.33:
                return GREEN
            elif frac < 0.66:
                return YELLOW
            elif frac < 0.85:
                return ORANGE
            return RED

        while True:
            if self.check_quit():
                return None
            snap = self.state.snapshot()
            touches = self.get_touches()

            if _first_snap:
                _prev_b1 = snap["btn1_presses"]
                _prev_b2 = snap["btn2_presses"]
                _first_snap = False

            b1_new = snap["btn1_presses"] != _prev_b1
            b2_new = snap["btn2_presses"] != _prev_b2
            _prev_b1 = snap["btn1_presses"]
            _prev_b2 = snap["btn2_presses"]

            # POT1 scrolls game list
            pot_idx = int(snap["pot1"] / 4095 * (len(games) - 1) + 0.5)
            selected = max(0, min(pot_idx, len(games) - 1))

            # POT2 selects level (1–20)
            level = int(snap["pot2"] / 4095 * (max_level - 1) + 0.5) + 1
            level = max(1, min(level, max_level))

            if b1_new:
                return (selected, level_to_mult(level))
            if b2_new:
                return None

            # Touch: tap a game name
            for tx, ty in touches:
                list_y_start = 74
                for i in range(len(games)):
                    iy = list_y_start + i * item_h - int(scroll_y)
                    if list_y_start - 5 < iy < VIRT_H - 60:
                        if pygame.Rect(10, iy, VIRT_W - 20, item_h).collidepoint(tx, ty):
                            selected = i
                            return (selected, level_to_mult(level))

            # Smooth scroll
            target_scroll = max(0, selected * item_h - (visible_items // 2) * item_h)
            scroll_y += (target_scroll - scroll_y) * 0.2

            # ── Draw ──
            self.screen.fill(MENU_BG)

            # Header
            title = self.fonts["big"].render("PRACTICE MODE", False, CYAN)
            self.screen.blit(title, (cx - title.get_width() // 2, 10))
            hint = self.fonts["small"].render("POT1:Select  POT2:Level", False, GREY)
            self.screen.blit(hint, (cx - hint.get_width() // 2, 30))

            # Level bar
            lc = level_color(level)
            lbl = self.fonts["med"].render(f"LV {level}/{max_level}", False, lc)
            self.screen.blit(lbl, (cx - lbl.get_width() // 2, 44))
            bar_w = VIRT_W - 40
            bar_h = 6
            bar_x = 20
            bar_y = 60
            pygame.draw.rect(self.screen, (30, 30, 40), (bar_x, bar_y, bar_w, bar_h))
            fill_w = int(bar_w * (level / max_level))
            pygame.draw.rect(self.screen, lc, (bar_x, bar_y, fill_w, bar_h))
            draw_pixel_border(self.screen, pygame.Rect(bar_x, bar_y, bar_w, bar_h), GREY, 1)

            # Game list
            list_y_start = 74
            for i, game in enumerate(games):
                iy = list_y_start + i * item_h - int(scroll_y)
                if iy < list_y_start - 5 or iy > VIRT_H - 55:
                    continue
                is_sel = (i == selected)
                if is_sel:
                    pygame.draw.rect(self.screen, (20, 30, 50),
                                     (8, iy, VIRT_W - 16, item_h - 2))
                    draw_pixel_border(self.screen,
                                      pygame.Rect(8, iy, VIRT_W - 16, item_h - 2),
                                      YELLOW, 1)
                    nc = YELLOW
                else:
                    nc = GREY
                name = self.fonts["med"].render(game.name, False, nc)
                self.screen.blit(name, (18, iy + 3))
                hint_txt = self.fonts["small"].render(game.hint, False,
                                                      (80, 80, 100))
                self.screen.blit(hint_txt, (VIRT_W - 18 - hint_txt.get_width(),
                                            iy + 5))

            # Footer
            foot1 = self.fonts["small"].render("B1:Play  B2:Back", False, GREY)
            self.screen.blit(foot1, (cx - foot1.get_width() // 2, VIRT_H - 18))

            self.flip()
            self.clock.tick(FPS)

    # ── RUN PRACTICE (single game loop) ───────────────────
    def run_practice(self, game_idx, speed_mult):
        """Loop a single minigame at fixed difficulty until B2 exits."""
        game = ALL_GAMES[game_idx]
        speed_level = max(1, int((1.0 - speed_mult) / 0.05) + 1)
        wins = 0
        plays = 0

        self.all_leds_off()
        self.set_led("b", True)

        while True:
            snap = self.state.snapshot()
            game.reset(snap, speed_mult)

            self.flash_screen(game.name, YELLOW, game.bg_color, 0.6,
                              subtitle=game.hint)

            if game.wave_based:
                duration = game.base_duration
            else:
                duration = game.base_duration * speed_mult
            start_time = time.time()
            result = None

            while True:
                if self.check_quit():
                    self.set_led("b", False)
                    return

                dt = 1.0 / FPS
                elapsed = time.time() - start_time
                time_left = duration - elapsed

                if time_left <= 0:
                    result = (game.game_type == "survive")
                    break

                snap = self.state.snapshot()
                check = game.update(snap, dt)
                if check is not None:
                    result = check
                    break

                self.screen.fill(game.bg_color)
                game.draw(self.screen, snap, time_left, duration, self.fonts)
                if not game.wave_based:
                    self.draw_timer(time_left, duration)
                # Practice HUD: wins/plays instead of score/lives
                cx = VIRT_W // 2
                stat = self.fonts["small"].render(
                    f"W:{wins}/{plays}", False, GREY)
                self.screen.blit(stat, (VIRT_W - stat.get_width() - 4, 4))
                self.flip()
                self.clock.tick(FPS)

            plays += 1
            if result:
                wins += 1
                self.led_win()
            else:
                self.led_lose()

            anim_start = time.time()
            anim_dur = game.RESULT_DURATION
            while time.time() - anim_start < anim_dur:
                if self.check_quit():
                    self.set_led("b", False)
                    return
                anim_t = time.time() - anim_start
                self.screen.fill(game.bg_color)
                game.animate_result(self.screen, result, anim_t, self.fonts)
                self.flip()
                self.clock.tick(FPS)

            # Brief pause — check B2 to exit
            pause_start = time.time()
            while time.time() - pause_start < 0.5:
                if self.check_quit():
                    self.set_led("b", False)
                    return
                snap = self.state.snapshot()
                if snap["btn2"]:
                    self.set_led("b", False)
                    return
                self.screen.fill(MENU_BG)
                cx = VIRT_W // 2
                stat = self.fonts["big"].render(
                    f"{wins}/{plays}", False, NEON_GREEN if wins > plays // 2 else ORANGE)
                self.screen.blit(stat, (cx - stat.get_width() // 2, VIRT_H // 2))
                hint = self.fonts["small"].render("B2 to quit", False, GREY)
                self.screen.blit(hint, (cx - hint.get_width() // 2, VIRT_H // 2 + 20))
                self.flip()
                self.clock.tick(FPS)

        self.set_led("b", False)

    # ── GAME OVER SCREEN ─────────────────────────────────
    def game_over_screen(self, score):
        self.all_leds_off()
        time.sleep(0.4)

        # Save high score
        new_hi = is_highscore(score)
        if score > 0:
            scores = load_highscores()
            scores.append(score)
            save_highscores(scores)
        hi_scores = load_highscores()

        frame = 0
        while True:
            if self.check_quit():
                return False
            touches = self.get_touches()
            snap = self.state.snapshot()
            if touches or snap["btn1"] or snap["btn2"]:
                time.sleep(0.3)
                return True
            frame += 1

            self.screen.fill((10, 0, 0))

            # Retro static noise
            for _ in range(30):
                nx = random.randint(0, VIRT_W - 1)
                ny = random.randint(0, VIRT_H - 1)
                nv = random.randint(15, 35)
                pygame.draw.rect(self.screen, (nv, 0, 0), (nx, ny, 1, 1))

            cx = VIRT_W // 2

            # GAME OVER with glow
            go_txt = "GAME OVER"
            draw_glow_text(self.screen, go_txt, self.fonts["title"], RED,
                           (cx - self.fonts["title"].size(go_txt)[0] // 2, 60),
                           (100, 0, 0), 1)

            # Score
            sc_txt = f"{score:04d}"
            draw_glow_text(self.screen, sc_txt, self.fonts["giant"], WHITE,
                           (cx - self.fonts["giant"].size(sc_txt)[0] // 2, 110),
                           (60, 60, 60), 1)

            # NEW HIGH SCORE flash
            if new_hi and int(time.time() * 3) % 2:
                nh = "* NEW HIGH SCORE *"
                draw_glow_text(self.screen, nh, self.fonts["small"], YELLOW,
                               (cx - self.fonts["small"].size(nh)[0] // 2, 170),
                               (80, 80, 0))

            # Leaderboard
            lb = self.fonts["small"].render("- LEADERBOARD -", False, CYAN)
            self.screen.blit(lb, (cx - lb.get_width() // 2, 200))
            for i, sc in enumerate(hi_scores[:5]):
                rank_colors = [YELLOW, WHITE, ORANGE, GREY, GREY]
                is_current = (sc == score and new_hi)
                color = NEON_GREEN if is_current and int(time.time() * 4) % 2 else rank_colors[i]
                entry = f"{i + 1}. {sc:04d}"
                et = self.fonts["small"].render(entry, False, color)
                self.screen.blit(et, (cx - et.get_width() // 2, 218 + i * 16))

            blink = int(time.time() * 2) % 2
            if blink:
                ct = self.fonts["small"].render("PRESS TO CONTINUE", False, GREY)
                self.screen.blit(ct, (cx - ct.get_width() // 2, 320))

            self.flip()
            self.clock.tick(FPS)

    # ══════════════════════════════════════════════════════
    #  MAIN GAME LOOP
    # ══════════════════════════════════════════════════════
    def run_game(self):
        lives = 3
        score = 0
        speed_level = 1
        games_played = 0
        speed_mult = 1.0
        last_game_idx = -1

        self.all_leds_off()
        self.set_led("b", True)  # blue = game active

        while lives > 0:
            # Speed up every 5 games
            if games_played > 0 and games_played % 5 == 0:
                speed_level += 1
                speed_mult = max(0.4, 1.0 - (speed_level - 1) * 0.05)
                self.flash_screen("SPEED UP!", ORANGE, (40, 20, 0), 0.7)

            # Pick a random microgame (avoid repeats)
            idx = last_game_idx
            while idx == last_game_idx:
                idx = random.randint(0, len(ALL_GAMES) - 1)
            last_game_idx = idx
            game = ALL_GAMES[idx]
            snap = self.state.snapshot()
            game.reset(snap, speed_mult)

            # Instruction flash
            self.flash_screen(game.name, YELLOW, game.bg_color, 0.8,
                              subtitle=game.hint)

            # Run the microgame
            if game.wave_based:
                duration = game.base_duration  # wave games manage their own pacing
            else:
                duration = game.base_duration * speed_mult
            start_time = time.time()
            result = None

            while True:
                if self.check_quit():
                    self.set_led("b", False)
                    return score

                dt = 1.0 / FPS
                elapsed = time.time() - start_time
                time_left = duration - elapsed

                if time_left <= 0:
                    result = (game.game_type == "survive")
                    break

                snap = self.state.snapshot()
                check = game.update(snap, dt)
                if check is not None:
                    result = check
                    break

                # Draw
                self.screen.fill(game.bg_color)
                game.draw(self.screen, snap, time_left, duration, self.fonts)
                if not game.wave_based:
                    self.draw_timer(time_left, duration)
                self.draw_hud(score, lives, speed_level)
                self.flip()
                self.clock.tick(FPS)

            games_played += 1

            # Per-game result animation
            if result:
                score += speed_level
                self.led_win()
            else:
                lives -= 1
                self.led_lose()
            anim_start = time.time()
            anim_dur = game.RESULT_DURATION
            while time.time() - anim_start < anim_dur:
                if self.check_quit():
                    self.set_led("b", False)
                    return score
                anim_t = time.time() - anim_start
                self.screen.fill(game.bg_color)
                game.animate_result(self.screen, result, anim_t, self.fonts)
                self.draw_hud(score, lives, speed_level)
                self.flip()
                self.clock.tick(FPS)

            time.sleep(0.2)

        self.set_led("b", False)
        return score

    # ══════════════════════════════════════════════════════
    #  RUN
    # ══════════════════════════════════════════════════════
    def run(self):
        try:
            mode = self.run_menu()

            if mode == "serial":
                self.comm = SerialBackend(self.state, self.serial_port)
            else:
                self.comm = MQTTBackend(self.state)
            self.comm.start()

            if not self.wait_for_connection():
                return

            while True:
                choice = self.title_screen()
                if not choice:
                    break
                if choice == "practice":
                    result = self.practice_select_screen()
                    if result is not None:
                        self.run_practice(*result)
                    continue
                # Arcade mode
                score = self.run_game()
                if not self.game_over_screen(score):
                    break
        finally:
            self.all_leds_off()
            if self.comm:
                self.comm.stop()
            pygame.quit()


# ═══════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="PiWare - Retro Micro Arcade")
    parser.add_argument(
        "--port", default="/dev/ttyACM0",
        help="Serial port for ESP32 (serial mode only)")
    args = parser.parse_args()

    engine = GameEngine(serial_port=args.port)
    engine.run()


if __name__ == "__main__":
    main()
