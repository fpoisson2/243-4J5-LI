# code_labo1

Ce dossier contient un exemple minimal pour lancer une interface tactile sur
l'écran officiel du Raspberry Pi 5. Le script utilise Tkinter (inclus dans la
plupart des images Raspberry Pi OS) et force l'utilisation de l'affichage
principal lorsque l'on démarre la session via SSH.

## Fichiers
- `touchscreen_app.py` : fenêtre plein écran affichant un message simple.

## Démarrage manuel
1. Connectez-vous en SSH.
2. Exécutez le script :
   ```bash
   python3 code_labo1/touchscreen_app.py
   ```
   Si `DISPLAY` n'est pas défini, il sera automatiquement réglé sur `:0` pour
   cibler l'écran du Pi.

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
