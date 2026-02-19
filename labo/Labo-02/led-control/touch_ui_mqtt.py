import threading
import time
from queue import Queue

import curses
from evdev import InputDevice, ecodes, list_devices
import paho.mqtt.client as mqtt
import ssl

# Configuration MQTT
from mqtt_config import MQTT_CONFIG


# ---------- GESTION DU TOUCH ----------

class TouchReader(threading.Thread):
    def __init__(self, event_queue: Queue):
        super().__init__(daemon=True)
        self.event_queue = event_queue
        self.device = self._find_touch_device()
        if not self.device:
            raise RuntimeError("Aucun périphérique touchscreen trouvé.")

        abs_x = self.device.absinfo(ecodes.ABS_MT_POSITION_X)
        abs_y = self.device.absinfo(ecodes.ABS_MT_POSITION_Y)

        self.min_x, self.max_x = abs_x.min, abs_x.max
        self.min_y, self.max_y = abs_y.min, abs_y.max

        self.current_x = (self.min_x + self.max_x) // 2
        self.current_y = (self.min_y + self.max_y) // 2

    def _find_touch_device(self):
        for path in list_devices():
            dev = InputDevice(path)
            name = dev.name.lower()
            if "touch" in name or "ft5406" in name:
                print(f"[TouchReader] Using device: {dev.name} ({path})")
                return dev
        return None

    def run(self):
        for event in self.device.read_loop():
            if event.type == ecodes.EV_ABS:
                if event.code == ecodes.ABS_MT_POSITION_X:
                    self.current_x = event.value
                elif event.code == ecodes.ABS_MT_POSITION_Y:
                    self.current_y = event.value
            elif event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
                if event.value == 1:
                    self.event_queue.put(("tap", self.current_x, self.current_y))


# ---------- UI CURSES ----------

class LEDControlUI:
    def __init__(self, stdscr, touch_reader: TouchReader, event_queue: Queue, mqtt_config: dict):
        self.stdscr = stdscr
        self.touch_reader = touch_reader
        self.event_queue = event_queue
        self.running = True
        self.status_message = "READY - Arcade tactile en ligne"

        # Configuration MQTT
        self.mqtt_config = mqtt_config
        self.mqtt_client = None
        self.mqtt_connected = False

        # Topics MQTT pour les LEDs du LilyGo
        device_id = mqtt_config.get("device_id", "esp32-XXXX")
        self.led1_topic = f"{device_id}/led/1/set"
        self.led2_topic = f"{device_id}/led/2/set"
        self.led1_state_topic = f"{device_id}/led/1/state"
        self.led2_state_topic = f"{device_id}/led/2/state"

        self._init_mqtt()

        self.buttons = []  # rempli à chaque redraw en fonction de la taille écran

        # États des LEDs (pour les toggle switches)
        self.led1_state = False  # False = OFF, True = ON
        self.led2_state = False

        # Buffer pour les messages MQTT reçus (max 10 lignes)
        self.mqtt_feedback = []
        self.max_feedback_lines = 10

    def _init_mqtt(self):
        """
        Initialise la connexion MQTT via WebSocket Secure (WSS)
        """
        try:
            # Créer le client MQTT avec transport WebSocket
            client_id = f"python-control-{int(time.time())}"
            self.mqtt_client = mqtt.Client(
                client_id=client_id,
                transport="websockets"
            )

            # Configuration SSL pour WSS
            self.mqtt_client.tls_set(
                ca_certs=None,
                certfile=None,
                keyfile=None,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
                ciphers=None
            )

            # Authentification
            username = self.mqtt_config.get("username", "esp_user")
            password = self.mqtt_config.get("password", "")
            self.mqtt_client.username_pw_set(username, password)

            # Callbacks
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            self.mqtt_client.on_message = self._on_mqtt_message

            # Connexion
            broker = self.mqtt_config.get("broker", "mqtt.edxo.ca")
            port = self.mqtt_config.get("port", 443)

            self.status_message = f"Connexion à {broker}:{port}..."
            self.mqtt_client.connect(broker, port, 60)

            # Démarrer la boucle réseau dans un thread
            self.mqtt_client.loop_start()

        except Exception as e:
            self.status_message = f"Erreur MQTT: {str(e)}"
            self.mqtt_client = None

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback appelé lors de la connexion MQTT"""
        if rc == 0:
            self.mqtt_connected = True
            self.status_message = "MQTT connecté!"
            self._add_feedback("✓ Connecté au broker MQTT")

            # S'abonner aux topics de statut des boutons (optionnel)
            device_id = self.mqtt_config.get("device_id", "esp32-XXXX")
            button1_topic = f"{device_id}/button/1/state"
            button2_topic = f"{device_id}/button/2/state"
            led1_state_topic = f"{device_id}/led/1/state"
            led2_state_topic = f"{device_id}/led/2/state"
            client.subscribe(button1_topic)
            client.subscribe(button2_topic)
            client.subscribe(led1_state_topic)
            client.subscribe(led2_state_topic)

        else:
            self.mqtt_connected = False
            error_messages = {
                1: "Protocole incorrect",
                2: "Client ID rejeté",
                3: "Serveur indisponible",
                4: "Username/Password incorrect",
                5: "Non autorisé"
            }
            msg = error_messages.get(rc, f"Erreur inconnue ({rc})")
            self.status_message = f"Échec connexion MQTT: {msg}"
            self._add_feedback(f"✗ Erreur: {msg}")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback appelé lors de la déconnexion MQTT"""
        self.mqtt_connected = False
        if rc != 0:
            self.status_message = f"Déconnexion MQTT inattendue (code {rc})"
            self._add_feedback("⚠ Connexion perdue, reconnexion...")

    def _on_mqtt_message(self, client, userdata, msg):
        """Callback appelé lors de la réception d'un message MQTT"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8', errors='ignore')
        if topic == self.led1_state_topic and payload in ("ON", "OFF"):
            self.led1_state = payload == "ON"
        elif topic == self.led2_state_topic and payload in ("ON", "OFF"):
            self.led2_state = payload == "ON"
        self._add_feedback(f"← {topic}: {payload}")

    def _add_feedback(self, message):
        """Ajoute un message au buffer de feedback"""
        self.mqtt_feedback.append(message)
        if len(self.mqtt_feedback) > self.max_feedback_lines:
            self.mqtt_feedback.pop(0)

    def _publish_mqtt(self, topic, message):
        """
        Publie un message MQTT
        """
        if self.mqtt_client and self.mqtt_connected:
            try:
                result = self.mqtt_client.publish(topic, message, qos=0)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self.status_message = f"Envoyé: {topic} = {message}"
                    self._add_feedback(f"→ {topic}: {message}")
                else:
                    self.status_message = f"Erreur publication: {result.rc}"
            except Exception as e:
                self.status_message = f"Erreur: {str(e)}"
        else:
            self.status_message = "MQTT non connecté"

    def _init_colors(self):
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_RED)
        curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(11, curses.COLOR_YELLOW, curses.COLOR_RED)
        curses.init_pair(12, curses.COLOR_WHITE, curses.COLOR_GREEN)

    def _build_buttons(self, h, w):
        self.buttons = []
        usable_w = w - 6
        btn_gap = 4
        btn_width = max(20, (usable_w - btn_gap) // 2)
        quit_h = 3
        btn_height = max(8, h - 18 - quit_h)
        start_col = 3
        btn_row = 9

        self.buttons.append({
            "name": "LED1", "label": "LED ROUGE",
            "state_attr": "led1_state",
            "row": btn_row, "col": start_col,
            "height": btn_height, "width": btn_width,
            "active": False, "topic": self.led1_topic,
            "color_on": 1, "color_off": 1,
        })
        self.buttons.append({
            "name": "LED2", "label": "LED VERTE",
            "state_attr": "led2_state",
            "row": btn_row, "col": start_col + btn_width + btn_gap,
            "height": btn_height, "width": btn_width,
            "active": False, "topic": self.led2_topic,
            "color_on": 2, "color_off": 2,
        })
        quit_row = btn_row + btn_height + 1
        self.buttons.append({
            "name": "QUIT", "label": "EXIT GAME",
            "state_attr": None,
            "row": quit_row, "col": start_col,
            "height": quit_h, "width": usable_w,
            "active": False, "topic": None,
            "color_on": 10, "color_off": 10,
        })

    def _safe_addstr(self, row, col, text, attr=0):
        h, w = self.stdscr.getmaxyx()
        if row < 0 or row >= h or not text:
            return
        if col < 0:
            text = text[-col:]
            col = 0
        if col >= w:
            return
        text = text[:max(0, w - col - 1)]
        if not text:
            return
        try:
            if attr:
                self.stdscr.attron(attr)
            self.stdscr.addstr(row, col, text)
            if attr:
                self.stdscr.attroff(attr)
        except curses.error:
            pass

    def _draw(self):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        t = time.time()

        # ═══ OUTER BORDER (gradient neon frame) ═══
        border_attr = curses.color_pair(5) | curses.A_BOLD
        self._safe_addstr(0, 0, "▓" * (w - 1), border_attr)
        self._safe_addstr(h - 1, 0, "▓" * (w - 1), border_attr)
        for r in range(1, h - 1):
            self._safe_addstr(r, 0, "▓▓", border_attr)
            self._safe_addstr(r, w - 3, "▓▓", border_attr)

        # ═══ ASCII ART TITLE ═══
        title = [
            "█   ████ ████   ████ ████ █  █ █████ ████  ████ █    ",
            "█   █    █  █   █    █  █ ██ █   █   █   █ █  █ █    ",
            "█   ███  █  █   █    █  █ █ ██   █   ████  █  █ █    ",
            "█   █    █  █   █    █  █ █  █   █   █  █  █  █ █    ",
            "████ ████ ████   ████ ████ █  █   █   █  █  ████ ████ ",
        ]
        title_attr = curses.color_pair(3) | curses.A_BOLD
        if w > 58:
            for i, line in enumerate(title):
                self._safe_addstr(1 + i, max(3, (w - len(line)) // 2), line, title_attr)
            sub_row = 6
        else:
            fallback = "★ ★ ★  L E D   C O N T R O L  ★ ★ ★"
            self._safe_addstr(1, max(3, (w - len(fallback)) // 2), fallback, title_attr)
            sub_row = 3

        sub = "A R C A D E    C O N T R O L    P A N E L"
        self._safe_addstr(sub_row, max(3, (w - len(sub)) // 2), sub,
                          curses.color_pair(5) | curses.A_BOLD)

        # ═══ ANIMATED STAR SEPARATOR ═══
        phase = int(t * 4) % 4
        pats = ["★ · ✦ · ", "· ★ · ✦ ", "✦ · ★ · ", "· ✦ · ★ "]
        sep = (pats[phase] * ((w - 6) // len(pats[phase]) + 1))[:w - 7]
        self._safe_addstr(sub_row + 1, 3, sep, curses.color_pair(3))

        # ═══ STATUS INDICATORS ═══
        if self.mqtt_connected:
            self._safe_addstr(8, 3, " ● LINK ONLINE ",
                              curses.color_pair(2) | curses.A_BOLD)
        else:
            icon = "●" if int(t * 2) % 2 else "○"
            self._safe_addstr(8, 3, f" {icon} LINK OFFLINE ",
                              curses.color_pair(1) | curses.A_BOLD)
        credit = f"CREDIT {int(t) % 100:02d}"
        self._safe_addstr(8, w - len(credit) - 4, credit,
                          curses.color_pair(3) | curses.A_BOLD)

        # ═══ BUILD BUTTON LAYOUT ═══
        self._build_buttons(h, w)

        # ═══ DRAW ARCADE BUTTONS ═══
        for btn in self.buttons:
            is_on = False
            if btn["state_attr"]:
                is_on = getattr(self, btn["state_attr"], False)

            cpair = btn["color_on"] if is_on else btn["color_off"]
            fill = curses.color_pair(cpair) | curses.A_BOLD
            if btn["state_attr"] and not is_on:
                fill |= curses.A_DIM
            rt = btn["row"]
            rb = rt + btn["height"] - 1
            cl = btn["col"]
            bw = btn["width"]

            if btn["name"] in ("LED1", "LED2"):
                # Rounded arcade button using block characters
                pad1 = min(6, max(2, bw // 6))
                pad2 = min(3, max(1, bw // 10))

                # Top curve (narrow → wide)
                self._safe_addstr(rt, cl + pad1, "▄" * (bw - 2 * pad1), fill)
                self._safe_addstr(rt + 1, cl + pad2, "█" * (bw - 2 * pad2), fill)
                # Full-width body
                for r in range(rt + 2, rb - 1):
                    self._safe_addstr(r, cl, "█" * bw, fill)
                # Bottom curve (wide → narrow)
                self._safe_addstr(rb - 1, cl + pad2, "█" * (bw - 2 * pad2), fill)
                self._safe_addstr(rb, cl + pad1, "▀" * (bw - 2 * pad1), fill)

                # Label with stars
                label = f"★ {btn['label']} ★"
                lc = cl + max(0, (bw - len(label)) // 2)
                self._safe_addstr(rt + 3, lc, label, fill | curses.A_REVERSE)

                # Glowing state indicator (inner circle)
                state_txt = "  O N  " if is_on else " O F F "
                glow_w = len(state_txt) + 6
                glow_bar = "█" * glow_w
                glow_mid = "███" + state_txt + "███"
                mid = rt + btn["height"] // 2
                gc = cl + (bw - glow_w) // 2
                self._safe_addstr(mid - 2, gc + 2, "▄" * (glow_w - 4), fill)
                self._safe_addstr(mid - 1, gc, glow_bar, fill)
                self._safe_addstr(mid,     gc, glow_mid, fill | curses.A_REVERSE)
                self._safe_addstr(mid + 1, gc, glow_bar, fill)
                self._safe_addstr(mid + 2, gc + 2, "▀" * (glow_w - 4), fill)

                # Touch hint
                hint = "[ T O U C H ]"
                hc = cl + (bw - len(hint)) // 2
                self._safe_addstr(rb - 3, hc, hint, fill | curses.A_REVERSE)

            else:
                # Quit bar – flat rounded
                pad = min(3, max(1, bw // 15))
                self._safe_addstr(rt, cl + pad, "▄" * (bw - 2 * pad), fill)
                for r in range(rt + 1, rb):
                    self._safe_addstr(r, cl, "█" * bw, fill)
                self._safe_addstr(rb, cl + pad, "▀" * (bw - 2 * pad), fill)
                qt = "★  G A M E   O V E R  ·  P R E S S   T O   Q U I T  ★"
                if len(qt) > bw - 4:
                    qt = "★ PRESS TO QUIT ★"
                qc = cl + max(0, (bw - len(qt)) // 2)
                qr = rt + btn["height"] // 2
                self._safe_addstr(qr, qc, qt, fill | curses.A_REVERSE)

        # ═══ MQTT GAME LOG (last 2 messages) ═══
        log_attr = curses.color_pair(4)
        for i, msg in enumerate(self.mqtt_feedback[-2:]):
            self._safe_addstr(h - 4 + i, 4, f"  > {msg}"[:w - 8], log_attr)

        # ═══ STATUS BAR ═══
        status = f"► {self.status_message}"[:w - 30]
        self._safe_addstr(h - 2, 3, status, curses.color_pair(4) | curses.A_BOLD)
        help_txt = "TOUCH TO PLAY · Q=QUIT"
        self._safe_addstr(h - 2, max(3, w - len(help_txt) - 4), help_txt,
                          curses.color_pair(6))

        self.stdscr.refresh()

    def _touch_to_rowcol(self, x_raw, y_raw):
        h, w = self.stdscr.getmaxyx()

        dx = max(1, self.touch_reader.max_x - self.touch_reader.min_x)
        dy = max(1, self.touch_reader.max_y - self.touch_reader.min_y)

        x_norm = (x_raw - self.touch_reader.min_x) / dx
        y_norm = (y_raw - self.touch_reader.min_y) / dy

        col = int(x_norm * (w - 1))
        row = int(y_norm * (h - 1))

        row = max(0, min(h - 1, row))
        col = max(0, min(w - 1, col))
        return row, col

    def _handle_touch_tap(self, x_raw, y_raw):
        row, col = self._touch_to_rowcol(x_raw, y_raw)

        clicked_btn = None
        for btn in self.buttons:
            if (btn["row"] <= row < btn["row"] + btn["height"] and
                    btn["col"] <= col < btn["col"] + btn["width"]):
                clicked_btn = btn
                break

        if not clicked_btn:
            self.status_message = f"Touché hors bouton: row={row}, col={col}"
            return

        btn_name = clicked_btn["name"]
        if btn_name == "QUIT":
            self.status_message = "Arrêt demandé..."
            self.running = False
        elif btn_name == "LED1":
            self.led1_state = not self.led1_state
            message = "ON" if self.led1_state else "OFF"
            self._publish_mqtt(clicked_btn["topic"], message)
            self.status_message = f"LED ROUGE: {message}"
        elif btn_name == "LED2":
            self.led2_state = not self.led2_state
            message = "ON" if self.led2_state else "OFF"
            self._publish_mqtt(clicked_btn["topic"], message)
            self.status_message = f"LED VERTE: {message}"

    def run(self):
        self.stdscr.nodelay(True)
        curses.curs_set(0)
        self._init_colors()

        last_redraw = 0

        while self.running:
            now = time.time()
            if now - last_redraw > 0.05:  # ~20 FPS
                self._draw()
                last_redraw = now

            # Lecture touches clavier
            try:
                ch = self.stdscr.getch()
            except curses.error:
                ch = -1

            if ch == ord('q'):
                self.status_message = "Quit avec 'q'."
                self.running = False

            # Gestion des événements tactiles
            try:
                event = self.event_queue.get_nowait()
            except Exception:
                event = None

            if event:
                kind = event[0]
                if kind == "tap":
                    _, x_raw, y_raw = event
                    self._handle_touch_tap(x_raw, y_raw)

            time.sleep(0.01)

        # Fermer la connexion MQTT à la fin
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()


# ---------- ENTRY POINT ----------

def main(stdscr):
    event_queue = Queue()
    touch_reader = TouchReader(event_queue)
    touch_reader.start()

    ui = LEDControlUI(stdscr, touch_reader, event_queue, MQTT_CONFIG)
    ui.run()


if __name__ == "__main__":
    curses.wrapper(main)
