"""UI utilitaire : graphique (Tk) ou console (texte).

Le mode par défaut (``auto``) lance l'interface graphique Tk si elle est
disponible. Si Tkinter est absent ou que l'affichage X n'est pas joignable
(cas typique sur une machine headless ou en SSH sans X11), l'application se
rabats sur une interface console simple, pilotable au clavier.
"""
from __future__ import annotations

import argparse
import importlib
import os
import signal
import sys
from dataclasses import dataclass
from types import ModuleType
from typing import Callable, Optional, TextIO


class DisplayUnavailable(RuntimeError):
    """Affichage graphique inaccessible."""


def _load_tkinter() -> tuple[Optional[ModuleType], Optional[type]]:
    """Charge Tkinter si disponible sans try/except autour de l'import.

    - Retourne ``(None, None)`` si le module n'existe pas (ex. Ubuntu minimal
      sans ``python3-tk``).
    - Retourne le module et ``TclError`` sinon.
    """

    spec = importlib.util.find_spec("tkinter")
    if spec is None:
        return None, None

    module = importlib.import_module("tkinter")
    tcl_error = getattr(module, "TclError")
    return module, tcl_error


def _is_ssh_session() -> bool:
    return any(var in os.environ for var in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY"))


def _is_forwarded_display(display: str) -> bool:
    return display.startswith("localhost:") or display.startswith("127.0.0.1:") or display.startswith("::1:")


def _guess_xauthority() -> Optional[str]:
    """Retourne un chemin Xauthority plausible si absent."""

    candidates = [os.environ.get("XAUTHORITY"), os.path.expanduser("~/.Xauthority")]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


@dataclass
class TouchscreenApp:
    """Interface graphique Tk pour écran tactile."""

    tk_mod: ModuleType
    tcl_error: type
    title: str = "Tableau de bord"
    background: str = "#0d1b2a"
    foreground: str = "#e0e1dd"
    running: bool = False

    def __post_init__(self) -> None:
        self._ensure_display()
        self.root = self._create_root()
        self.root.title(self.title)
        self.root.configure(bg=self.background)
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda event: self.stop())
        self._register_signal_handlers()
        self._build_ui()

    def _ensure_display(self) -> None:
        """Force le lancement sur l'écran local même en session SSH avec X11."""

        prefer_ssh_display = os.environ.get("PREFER_SSH_DISPLAY") == "1"
        display = os.environ.get("DISPLAY")

        if display is None:
            os.environ["DISPLAY"] = ":0"
        elif _is_ssh_session() and _is_forwarded_display(display) and not prefer_ssh_display:
            os.environ["DISPLAY"] = ":0"

        if "XAUTHORITY" not in os.environ:
            guessed = _guess_xauthority()
            if guessed:
                os.environ["XAUTHORITY"] = guessed

    def _create_root(self):  # type: ignore[override]
        try:
            return self.tk_mod.Tk()
        except self.tcl_error as exc:
            sys.stderr.write(
                "Impossible de se connecter à l'affichage"
                f" {os.environ.get('DISPLAY', 'non défini')}\n"
                "Vérifiez qu'une session graphique est ouverte (bureau, `startx`,"
                " ou équivalent Wayland/X11) et que Xauthority est accessible.\n"
                "Depuis une connexion SSH, exportez par exemple :\n"
                "  export DISPLAY=:0\n"
                "  export XAUTHORITY=/home/pi/.Xauthority\n"
                "Puis relancez le script lorsque l'écran est actif.\n"
            )
            raise DisplayUnavailable("Affichage graphique indisponible") from exc

    def _register_signal_handlers(self) -> None:
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(sig, self._make_signal_handler(sig))

    def _make_signal_handler(self, sig: signal.Signals) -> Callable[[int, object], None]:
        def handler(_signum: int, _frame: object) -> None:
            print(f"Reçu {sig.name}, fermeture propre en cours…", file=sys.stderr)
            self.stop()

        return handler

    def _build_ui(self) -> None:
        frame = self.tk_mod.Frame(self.root, bg=self.background)
        frame.pack(expand=True, fill=self.tk_mod.BOTH, padx=32, pady=32)

        title_label = self.tk_mod.Label(
            frame,
            text="Interface tactile prête",
            font=("Arial", 28, "bold"),
            bg=self.background,
            fg=self.foreground,
        )
        title_label.pack(pady=(0, 16))

        info_label = self.tk_mod.Label(
            frame,
            text=(
                "Cette fenêtre s'ouvre sur l'écran tactile du Raspberry Pi 5.\n"
                "Appuyez sur Échap pour quitter ou stoppez le service."
            ),
            font=("Arial", 16),
            bg=self.background,
            fg=self.foreground,
            justify=self.tk_mod.CENTER,
        )
        info_label.pack()

        quit_button = self.tk_mod.Button(
            frame,
            text="Quitter proprement",
            font=("Arial", 16, "bold"),
            bg="#1b263b",
            fg=self.foreground,
            activebackground="#415a77",
            activeforeground=self.foreground,
            relief=self.tk_mod.RAISED,
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


@dataclass
class ConsoleApp:
    """Interface console minimale pour machines sans affichage graphique."""

    prompt: str = (
        "Interface console démarrée.\n"
        "- Appuyez sur Q puis Entrée pour quitter proprement.\n"
        "- Ou envoyez Ctrl+C / un signal pour fermer.\n"
    )
    input_stream: TextIO = sys.stdin
    output_stream: TextIO = sys.stdout
    running: bool = False

    def __post_init__(self) -> None:
        self._register_signal_handlers()

    def _register_signal_handlers(self) -> None:
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(sig, self._make_signal_handler(sig))

    def _make_signal_handler(self, sig: signal.Signals) -> Callable[[int, object], None]:
        def handler(_signum: int, _frame: object) -> None:
            print(f"Reçu {sig.name}, fermeture propre en cours…", file=sys.stderr)
            self.stop()

        return handler

    def run(self) -> None:
        self.running = True
        print(self.prompt, file=self.output_stream, end="", flush=True)
        while self.running:
            try:
                self.output_stream.write(">>> ")
                self.output_stream.flush()
                user_input = self.input_stream.readline()
            except (EOFError, KeyboardInterrupt):
                print("Fermeture demandée.", file=self.output_stream, flush=True)
                self.stop()
                continue

            if user_input.strip().lower() in {"q", "quit", "exit"}:
                self.stop()
                break
            print("Tapez Q puis Entrée pour quitter, ou Ctrl+C.", file=self.output_stream, flush=True)

    def stop(self) -> None:
        self.running = False
        print("Arrêt propre de l'interface console.", file=self.output_stream, flush=True)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interface tactile ou console")
    parser.add_argument(
        "--mode",
        choices=("auto", "gui", "console"),
        default="auto",
        help="auto: Tk si dispo, sinon console ; gui: force Tk ; console: texte",
    )
    parser.add_argument(
        "--console-tty",
        default=None,
        help=(
            "TTY à utiliser pour l'interface console (ex. /dev/tty1)."
            " Par défaut, en SSH on cible /dev/tty1 pour afficher sur l'écran"
            " local ; désactivez avec PREFER_SSH_CONSOLE=1."
        ),
    )
    return parser.parse_args(argv)


def _select_console_streams(preferred_tty: Optional[str]) -> tuple[TextIO, TextIO, bool]:
    """Retourne (stdin, stdout, should_close) pour la console.

    - En SSH, on cible /dev/tty1 (ou le TTY fourni) pour afficher sur l'écran
      local, sauf si ``PREFER_SSH_CONSOLE=1`` force la console dans la session
      distante.
    - Si l'ouverture échoue, on se rabat sur les flux standards.
    """

    prefer_ssh_console = os.environ.get("PREFER_SSH_CONSOLE") == "1"
    tty_path = preferred_tty

    if tty_path is None and _is_ssh_session() and not prefer_ssh_console:
        tty_path = "/dev/tty1"

    if tty_path:
        try:
            stream = open(tty_path, "r+")
        except OSError as exc:
            sys.stderr.write(
                f"Impossible d'ouvrir {tty_path} ({exc}); "
                "utilisation de la session SSH pour la console.\n"
            )
        else:
            sys.stderr.write(f"Console redirigée vers {tty_path}.\n")
            return stream, stream, True

    return sys.stdin, sys.stdout, False


def _launch_gui(tk_mod: ModuleType, tcl_error: type) -> None:
    app = TouchscreenApp(tk_mod=tk_mod, tcl_error=tcl_error)
    app.run()


def main(argv: Optional[list[str]] = None) -> None:
    args = _parse_args(argv or sys.argv[1:])

    if args.mode == "console":
        console_stdin, console_stdout, should_close = _select_console_streams(args.console_tty)
        try:
            ConsoleApp(input_stream=console_stdin, output_stream=console_stdout).run()
        finally:
            if should_close:
                console_stdin.close()
        return

    tk_mod, tcl_error = _load_tkinter()
    tk_ready = tk_mod is not None and tcl_error is not None

    if args.mode == "gui" and not tk_ready:
        sys.stderr.write(
            "Tkinter n'est pas disponible. Installez-le avec :\n"
            "  sudo apt update && sudo apt install -y python3-tk\n"
            "Puis relancez le script avec /usr/bin/python3.\n"
        )
        raise SystemExit(1)

    if tk_ready:
        try:
            _launch_gui(tk_mod, tcl_error)
            return
        except DisplayUnavailable:
            if args.mode == "gui":
                raise
            print(
                "Affichage graphique inaccessible ; bascule automatique en mode "
                "console."
            )
    else:
        if args.mode == "gui":
            sys.stderr.write(
                "Tkinter n'est pas disponible ; impossible de lancer le mode "
                "graphique.\n"
            )
            raise SystemExit(1)

    ConsoleApp().run()


if __name__ == "__main__":
    main()
