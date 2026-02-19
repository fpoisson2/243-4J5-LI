#!/bin/bash
# Script pour lancer l'interface tactile sur l'écran distant
# Usage: sudo ./launch_ui.sh

echo "Démarrage de l'interface tactile de contrôle LED..."
echo "Basculement vers TTY1..."

# Basculer vers TTY1
chvt 1

# Lancer l'interface sur TTY1
# On définit TERM=linux pour que curses s'initialise correctement sur la console
SCRIPT_DIR=$(dirname "$(realpath "$0")")
setsid sh -c "export TERM=linux; exec </dev/tty1 >/dev/tty1 2>&1 python3 $SCRIPT_DIR/touch_ui_led.py"
