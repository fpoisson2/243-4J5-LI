"""Simple touchscreen-friendly UI starter for Raspberry Pi 5.

The script ensures the UI is launched on the primary X display (e.g. the
Raspberry Pi official touchscreen). It is safe to start over SSH: when no
``DISPLAY`` variable is present it defaults to ``:0`` so the window opens on
the connected monitor rather than the SSH pseudo-terminal.

Signal handlers are installed to close the Tkinter loop cleanly on shutdown
(SIGHUP, SIGINT, SIGTERM), ensuring the next start does not complain about an
existing process holding the display.
"""
from __future__ import annotations

import os
import signal
import sys

try:
    import tkinter as tk
except ImportError as exc:  # pragma: no cover - guidance for missing system dep
    sys.stderr.write(
        "Tkinter n'est pas disponible. Installez-le avec :\n"
        "  sudo apt update && sudo apt install -y python3-tk\n"
        "Puis relancez le script avec /usr/bin/python3 (ou dans un venv basé sur python3).\n"
    )
    raise SystemExit(1) from exc
from dataclasses import dataclass
from typing import Callable


@dataclass
class TouchscreenApp:
    """Basic Tkinter UI intended for Raspberry Pi touchscreens."""

    title: str = "Tableau de bord"
    background: str = "#0d1b2a"
    foreground: str = "#e0e1dd"
    running: bool = False

    def __post_init__(self) -> None:
        self._ensure_display()
        self.root = tk.Tk()
        self.root.title(self.title)
        self.root.configure(bg=self.background)
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda event: self.stop())
        self._register_signal_handlers()
        self._build_ui()

    def _ensure_display(self) -> None:
        """Force the UI to launch on the main display when started over SSH."""
        if "DISPLAY" not in os.environ:
            os.environ["DISPLAY"] = ":0"

    def _register_signal_handlers(self) -> None:
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(sig, self._make_signal_handler(sig))

    def _make_signal_handler(self, sig: signal.Signals) -> Callable[[int, object], None]:
        def handler(_signum: int, _frame: object) -> None:
            print(f"Reçu {sig.name}, fermeture propre en cours…", file=sys.stderr)
            self.stop()

        return handler

    def _build_ui(self) -> None:
        frame = tk.Frame(self.root, bg=self.background)
        frame.pack(expand=True, fill=tk.BOTH, padx=32, pady=32)

        title_label = tk.Label(
            frame,
            text="Interface tactile prête",
            font=("Arial", 28, "bold"),
            bg=self.background,
            fg=self.foreground,
        )
        title_label.pack(pady=(0, 16))

        info_label = tk.Label(
            frame,
            text=(
                "Cette fenêtre s'ouvre sur l'écran tactile du Raspberry Pi 5.\n"
                "Appuyez sur Échap pour quitter ou stoppez le service."
            ),
            font=("Arial", 16),
            bg=self.background,
            fg=self.foreground,
            justify=tk.CENTER,
        )
        info_label.pack()

        quit_button = tk.Button(
            frame,
            text="Quitter proprement",
            font=("Arial", 16, "bold"),
            bg="#1b263b",
            fg=self.foreground,
            activebackground="#415a77",
            activeforeground=self.foreground,
            relief=tk.RAISED,
            bd=3,
            command=self.stop,
        )
        quit_button.pack(pady=24)

    def run(self) -> None:
        self.running = True
        try:
            self.root.mainloop()
        finally:
            self.running = False
            self.root.destroy()

    def stop(self) -> None:
        if self.running:
            self.running = False
            self.root.after_idle(self.root.quit)


def main() -> None:
    app = TouchscreenApp()
    app.run()


if __name__ == "__main__":
    main()
