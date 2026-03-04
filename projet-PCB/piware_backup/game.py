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

        client_id = f"pi-warioware-{int(time.time())}"
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
    base_duration = 4.0
    game_type = "action"    # "action" = win early, "survive" = don't fail
    bg_color = BG

    def reset(self, snap=None):
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


# ── 1. Press a specific button ────────────────────────────
class PressButtonGame(MicroGame):
    name = "PRESS!"
    base_duration = 3.5
    game_type = "action"

    def reset(self, snap=None):
        self.target = random.choice([1, 2])
        self.bg_color = (20, 30, 50) if self.target == 1 else (50, 20, 30)

    def update(self, snap, dt):
        if snap[f"btn{self.target}"]:
            return True
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2 - 20
        txt = fonts["huge"].render(f"BTN {self.target}", False, WHITE)
        screen.blit(txt, (cx - txt.get_width() // 2, cy - 35))

        pressed = snap[f"btn{self.target}"]
        btn_color = YELLOW if pressed else GREY
        pygame.draw.circle(screen, btn_color, (cx, cy + 30), 28)
        pygame.draw.circle(screen, WHITE, (cx, cy + 30), 28, 1)
        num = fonts["giant"].render(str(self.target), False, BLACK)
        screen.blit(num, (cx - num.get_width() // 2,
                          cy + 30 - num.get_height() // 2))


# ── 2. Press both buttons ────────────────────────────────
class PressBothGame(MicroGame):
    name = "BOTH!"
    base_duration = 3.5
    game_type = "action"
    bg_color = (30, 20, 50)

    def update(self, snap, dt):
        if snap["btn1"] and snap["btn2"]:
            return True
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2 - 10
        for i, (bx, key) in enumerate([(cx - 43, "btn1"), (cx + 43, "btn2")]):
            color = GREEN if snap[key] else GREY
            pygame.draw.circle(screen, color, (bx, cy + 20), 25)
            pygame.draw.circle(screen, WHITE, (bx, cy + 20), 25, 1)
            num = fonts["big"].render(str(i + 1), False, BLACK)
            screen.blit(num, (bx - num.get_width() // 2,
                              cy + 20 - num.get_height() // 2))


# ── 3. Don't touch anything ──────────────────────────────
class DontTouchGame(MicroGame):
    name = "DON'T TOUCH!"
    base_duration = 3.0
    game_type = "survive"
    bg_color = (40, 15, 15)

    def reset(self, snap=None):
        self.grace = 0.35
        # Record initial pot positions to detect movement
        self.initial_pot1 = snap["pot1"] if snap else None
        self.initial_pot2 = snap["pot2"] if snap else None
        self.pot_margin = 25  # noise tolerance

    def update(self, snap, dt):
        if self.grace > 0:
            self.grace -= dt
            return None
        if snap["btn1"] or snap["btn2"]:
            return False
        # Check if pots moved beyond noise margin
        if self.initial_pot1 is not None:
            if abs(snap["pot1"] - self.initial_pot1) > self.pot_margin:
                return False
            if abs(snap["pot2"] - self.initial_pot2) > self.pot_margin:
                return False
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2
        pulse = abs(math.sin(time.time() * 5))
        sz = int(20 + pulse * 10)
        pygame.draw.line(screen, RED,
                         (cx - sz, cy - sz), (cx + sz, cy + sz), 3)
        pygame.draw.line(screen, RED,
                         (cx + sz, cy - sz), (cx - sz, cy + sz), 3)
        warn = fonts["med"].render("HANDS OFF!", False, ORANGE)
        screen.blit(warn, (cx - warn.get_width() // 2, cy + 40))


# ── 4. Turn potentiometer to MAX ─────────────────────────
class PotMaxGame(MicroGame):
    name = "MAX!"
    base_duration = 4.0
    game_type = "action"

    def reset(self, snap=None):
        candidates = [1, 2]
        random.shuffle(candidates)
        self.pot = candidates[0]
        if snap:
            # Prefer a pot that is NOT already above threshold
            for c in candidates:
                if snap[f"pot{c}"] <= 3400:
                    self.pot = c
                    break
            # If both pots are very high, pick the lower one
            else:
                self.pot = min(candidates,
                               key=lambda c: snap[f"pot{c}"])
        self.bg_color = (15, 35, 20)
        # Grace: ignore first 0.4s so initial position doesn't auto-win
        self.grace = 0.4

    def update(self, snap, dt):
        if self.grace > 0:
            self.grace -= dt
            return None
        if snap[f"pot{self.pot}"] > 3800:
            return True
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2 - 10
        val = snap[f"pot{self.pot}"]
        pct = val / 4095.0

        txt = fonts["big"].render(f"POT {self.pot} MAX!", False, WHITE)
        screen.blit(txt, (cx - txt.get_width() // 2, cy - 55))

        bar_w, bar_h = 40, 120
        bar_x, bar_y = cx - bar_w // 2, cy - 15
        pygame.draw.rect(screen, DARK_GREY, (bar_x, bar_y, bar_w, bar_h))
        fill_h = int(bar_h * pct)
        if fill_h > 0:
            color = GREEN if pct > 0.9 else YELLOW if pct > 0.5 else ORANGE
            pygame.draw.rect(screen, color,
                             (bar_x, bar_y + bar_h - fill_h, bar_w, fill_h))
        ty = bar_y + int(bar_h * (1 - 3800 / 4095))
        pygame.draw.line(screen, WHITE,
                         (bar_x - 5, ty), (bar_x + bar_w + 5, ty), 1)
        lbl = fonts["med"].render(f"{int(pct * 100)}%", False, WHITE)
        screen.blit(lbl, (cx - lbl.get_width() // 2, bar_y + bar_h + 6))


# ── 5. Turn potentiometer to MIN ─────────────────────────
class PotMinGame(MicroGame):
    name = "MINIMUM!"
    base_duration = 4.0
    game_type = "action"

    def reset(self, snap=None):
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
        self.bg_color = (35, 15, 20)
        self.grace = 0.4

    def update(self, snap, dt):
        if self.grace > 0:
            self.grace -= dt
            return None
        if snap[f"pot{self.pot}"] < 300:
            return True
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2 - 10
        val = snap[f"pot{self.pot}"]
        pct = val / 4095.0

        txt = fonts["big"].render(f"POT {self.pot} MIN!", False, WHITE)
        screen.blit(txt, (cx - txt.get_width() // 2, cy - 55))

        bar_w, bar_h = 40, 120
        bar_x, bar_y = cx - bar_w // 2, cy - 15
        pygame.draw.rect(screen, DARK_GREY, (bar_x, bar_y, bar_w, bar_h))
        fill_h = int(bar_h * pct)
        if fill_h > 0:
            color = GREEN if pct < 0.1 else ORANGE if pct < 0.5 else RED
            pygame.draw.rect(screen, color,
                             (bar_x, bar_y + bar_h - fill_h, bar_w, fill_h))
        ty = bar_y + int(bar_h * (1 - 300 / 4095))
        pygame.draw.line(screen, WHITE,
                         (bar_x - 5, ty), (bar_x + bar_w + 5, ty), 1)
        lbl = fonts["med"].render(f"{int(pct * 100)}%", False, WHITE)
        screen.blit(lbl, (cx - lbl.get_width() // 2, bar_y + bar_h + 6))


# ── 6. Match a target zone with a pot ─────────────────────
class MatchTargetGame(MicroGame):
    name = "MATCH!"
    base_duration = 5.0
    game_type = "action"
    bg_color = (20, 25, 40)

    def reset(self, snap=None):
        self.pot = random.choice([1, 2])
        self.tolerance = 200
        current = snap[f"pot{self.pot}"] if snap else 2048
        # Pick a target at least 800 away from current position
        lo, hi = 400, 3700
        far_lo = max(lo, current + 800)
        far_hi = min(hi, current - 800)
        if far_lo <= hi:
            self.target = random.randint(far_lo, hi)
        elif far_hi >= lo:
            self.target = random.randint(lo, far_hi)
        else:
            # Fallback: just pick the opposite end
            self.target = lo if current > 2048 else hi
        self.grace = 0.4

    def update(self, snap, dt):
        if self.grace > 0:
            self.grace -= dt
            return None
        if abs(snap[f"pot{self.pot}"] - self.target) < self.tolerance:
            return True
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2 - 10
        val = snap[f"pot{self.pot}"]

        txt = fonts["big"].render(f"POT {self.pot} TARGET!", False, WHITE)
        screen.blit(txt, (cx - txt.get_width() // 2, cy - 55))

        bar_w, bar_h = 70, 18
        bar_x = (VIRT_W - bar_w) // 2
        bar_y = cy + 8
        pygame.draw.rect(screen, DARK_GREY, (bar_x, bar_y, bar_w, bar_h))

        t_lo = int((self.target - self.tolerance) / 4095 * bar_w)
        t_hi = int((self.target + self.tolerance) / 4095 * bar_w)
        pygame.draw.rect(screen, (40, 110, 40),
                         (bar_x + t_lo, bar_y, t_hi - t_lo, bar_h))

        pos_x = bar_x + int(val / 4095 * bar_w)
        in_zone = abs(val - self.target) < self.tolerance
        mc = GREEN if in_zone else ORANGE
        pygame.draw.rect(screen, mc, (pos_x - 1, bar_y - 4, 3, bar_h + 8))

        vt = fonts["med"].render(str(val), False, WHITE)
        screen.blit(vt, (cx - vt.get_width() // 2, bar_y + bar_h + 10))


# ── 7. Mash a button N times ─────────────────────────────
class MashGame(MicroGame):
    name = "MASH!"
    base_duration = 6.0
    game_type = "action"
    bg_color = (40, 30, 10)

    def reset(self, snap=None):
        self.target_count = random.randint(8, 16)
        self.count = 0
        self.btn = random.choice([1, 2])
        self._baseline = None  # set on first update from press counter

    def update(self, snap, dt):
        presses = snap[f"btn{self.btn}_presses"]
        if self._baseline is None:
            self._baseline = presses
            return None
        self.count = presses - self._baseline
        if self.count >= self.target_count:
            return True
        return None

    def draw(self, screen, snap, tl, tt, fonts):
        cx, cy = VIRT_W // 2, VIRT_H // 2 - 15
        txt = fonts["big"].render(f"BTN {self.btn}!", False, WHITE)
        screen.blit(txt, (cx - txt.get_width() // 2, cy - 45))

        done = self.count >= self.target_count
        ct = fonts["giant"].render(
            f"{self.count}/{self.target_count}", False,
            GREEN if done else YELLOW)
        screen.blit(ct, (cx - ct.get_width() // 2, cy - 5))

        bar_w, bar_h = 170, 10
        bar_x = (VIRT_W - bar_w) // 2
        bar_y = cy + 42
        pct = min(self.count / self.target_count, 1.0)
        pygame.draw.rect(screen, DARK_GREY, (bar_x, bar_y, bar_w, bar_h))
        fw = int(bar_w * pct)
        if fw > 0:
            pygame.draw.rect(screen, YELLOW, (bar_x, bar_y, fw, bar_h))


# ── 8. Hold a button for the duration ────────────────────
class HoldGame(MicroGame):
    name = "HOLD!"
    base_duration = 4.0
    game_type = "survive"
    bg_color = (15, 30, 45)

    def reset(self, snap=None):
        self.btn = random.choice([1, 2])
        self.started = False
        self.wait_time = 0.0

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

        txt = fonts["big"].render(f"HOLD BTN {self.btn}!", False, WHITE)
        screen.blit(txt, (cx - txt.get_width() // 2, cy - 40))

        color = GREEN if pressed else RED
        pygame.draw.circle(screen, color, (cx, cy + 20), 28)
        pygame.draw.circle(screen, WHITE, (cx, cy + 20), 28, 1)

        if not self.started:
            status, sc = "PRESS NOW!", YELLOW
        elif pressed:
            status, sc = "HOLDING!", GREEN
        else:
            status, sc = "RELEASED!", RED
        st = fonts["med"].render(status, False, sc)
        screen.blit(st, (cx - st.get_width() // 2, cy + 60))


# ── All game instances ────────────────────────────────────
ALL_GAMES = [
    PressButtonGame(),
    PressBothGame(),
    DontTouchGame(),
    PotMaxGame(),
    PotMinGame(),
    MatchTargetGame(),
    MashGame(),
    HoldGame(),
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
        mono = "monospace"
        self.fonts = {
            "small": pygame.font.SysFont(mono, 8),
            "med":   pygame.font.SysFont(mono, 12, bold=True),
            "big":   pygame.font.SysFont(mono, 16, bold=True),
            "huge":  pygame.font.SysFont(mono, 22, bold=True),
            "giant": pygame.font.SysFont(mono, 32, bold=True),
            "title": pygame.font.SysFont(mono, 27, bold=True),
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
    def flash_screen(self, text, color, bg, duration=0.8):
        start = time.time()
        while time.time() - start < duration:
            if self.check_quit():
                return
            self.screen.fill(bg)
            # Retro grid background
            cx, cy = VIRT_W // 2, VIRT_H // 2
            draw_glow_text(self.screen, text, self.fonts["giant"], color,
                           (cx - self.fonts["giant"].size(text)[0] // 2,
                            cy - self.fonts["giant"].size(text)[1] // 2),
                           glow_radius=1)
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
        blink = True
        last_blink = time.time()
        time.sleep(0.3)
        frame = 0

        while True:
            if self.check_quit():
                return False
            touches = self.get_touches()
            snap = self.state.snapshot()
            if touches or snap["btn1"] or snap["btn2"]:
                return True
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

            cx = VIRT_W // 2
            pw = self.fonts["title"].size("PiWare")[0]
            draw_glow_text(self.screen, "PiWare", self.fonts["title"], CYAN,
                           (cx - pw // 2, 100), (0, 80, 100), 1)

            sub = self.fonts["med"].render("MICRO ARCADE", False, YELLOW)
            self.screen.blit(sub, (cx - sub.get_width() // 2, 140))

            if blink:
                ins = "INSERT COIN"
                draw_glow_text(self.screen, ins, self.fonts["med"], NEON_GREEN,
                               (cx - self.fonts["med"].size(ins)[0] // 2, 210),
                               (0, 60, 0))

            # High scores
            hi_scores = load_highscores()
            if hi_scores:
                ht = self.fonts["small"].render("- HIGH SCORES -", False, YELLOW)
                self.screen.blit(ht, (cx - ht.get_width() // 2, 260))
                for i, sc in enumerate(hi_scores[:5]):
                    rank_colors = [YELLOW, WHITE, ORANGE, GREY, GREY]
                    entry = f"{i + 1}. {sc:04d}"
                    et = self.fonts["small"].render(entry, False, rank_colors[i])
                    self.screen.blit(et, (cx - et.get_width() // 2, 278 + i * 16))

            self.flip()
            self.clock.tick(FPS)

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
            game.reset(snap)

            # Instruction flash
            self.flash_screen(game.name, YELLOW, game.bg_color, 0.8)

            # Run the microgame
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
                self.draw_timer(time_left, duration)
                self.draw_hud(score, lives, speed_level)
                self.flip()
                self.clock.tick(FPS)

            games_played += 1

            if result:
                score += speed_level
                self.flash_screen("WIN!", GREEN, (10, 50, 10), 0.5)
                self.led_win()
            else:
                lives -= 1
                self.flash_screen("LOSE!", RED, (50, 10, 10), 0.6)
                self.led_lose()

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
                if not self.title_screen():
                    break
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
