# code_labo1

Ce dossier contient un exemple minimal pour lancer une interface tactile sur
l'écran officiel du Raspberry Pi 5. Le script utilise Tkinter (inclus dans la
plupart des images Raspberry Pi OS) et force l'utilisation de l'affichage
principal lorsque l'on démarre la session via SSH.

## Fichiers
- `touchscreen_app.py` : fenêtre plein écran affichant un message simple.

## Prérequis
- Python 3 installé depuis l'image Raspberry Pi OS (par exemple `/usr/bin/python3`).
- Tkinter côté système :
  ```bash
  sudo apt update && sudo apt install -y python3-tk
  ```
  (Tkinter ne s'installe pas via `pip`, il doit provenir des paquets Debian.)
- Optionnel : un environnement virtuel basé sur Python 3 pour isoler les dépendances :
  ```bash
  sudo apt install -y python3-venv
  python3 -m venv venv
  source venv/bin/activate
  ```

## Démarrage manuel
1. Connectez-vous en SSH.
2. Exécutez le script :
   ```bash
   python3 code_labo1/touchscreen_app.py
   ```
   Si `DISPLAY` n'est pas défini, il sera automatiquement réglé sur `:0` pour
   cibler l'écran du Pi.
   - Si vous obtenez « couldn't connect to display ":0" », vérifiez qu'une
     session graphique est bien ouverte sur le Raspberry Pi (le bureau ou
     `startx`). Depuis SSH, assurez-vous aussi que l'utilisateur a accès au
     fichier Xauthority, par exemple :
     ```bash
     export DISPLAY=:0
     export XAUTHORITY=/home/pi/.Xauthority
     python3 code_labo1/touchscreen_app.py
     ```

### Arrêt propre
- Utilisez `Ctrl+C` dans le terminal ou appuyez sur la touche **Échap** ou sur
  le bouton « Quitter proprement ».
- Les signaux `SIGTERM`, `SIGINT` et `SIGHUP` sont gérés pour fermer la boucle
  Tkinter sans laisser de processus bloqué, ce qui garantit un redémarrage
  sain du service lors des prochains lancements.

## Lancement au boot (via systemd)
Pour que l'interface démarre automatiquement, créez un service systemd minimal
sur le Raspberry Pi :

```ini
[Unit]
Description=UI tactile labo1
After=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStart=/usr/bin/python3 /home/pi/code_labo1/touchscreen_app.py
Restart=on-failure

[Install]
WantedBy=graphical.target
```

Rechargez systemd puis activez le service :
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ui-tactile.service
```

Adaptez les chemins si le dossier `code_labo1` se trouve ailleurs.
