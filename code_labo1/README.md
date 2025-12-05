# code_labo1

Ce dossier contient un exemple minimal pour lancer une interface tactile sur
l'écran officiel du Raspberry Pi 5. Le script utilise Tkinter (inclus dans la
plupart des images Raspberry Pi OS) et force l'utilisation de l'affichage
principal lorsque l'on démarre la session via SSH.

## Fichiers
- `touchscreen_app.py` :
  - mode graphique (Tk) pour écran tactile ;
  - mode console (texte) pour machines sans affichage graphique (ex. Ubuntu
    24.04 headless).

## Prérequis
- Python 3 depuis l'OS installé (par exemple `/usr/bin/python3`).
- Pour le **mode graphique** :
  - Raspberry Pi OS : `sudo apt update && sudo apt install -y python3-tk`
  - Ubuntu 24.04 : `sudo apt install -y python3-tk`
  (Tkinter ne s'installe pas via `pip`, il doit provenir des paquets système.)
- Mode console : aucun paquet graphique nécessaire.
- Optionnel : un environnement virtuel basé sur Python 3 pour isoler les dépendances :
  ```bash
  sudo apt install -y python3-venv
  python3 -m venv venv
  source venv/bin/activate
  ```

## Démarrage manuel
Choisissez le mode adapté via `--mode` :
- `auto` (défaut) : tente le graphique, sinon bascule en console. Si l'écran
  graphique est éteint ou inaccessible, la bascule se fait automatiquement
  sans planter.
- `gui` : force Tk (échoue si Tkinter n'est pas disponible ou si l'affichage
  est inaccessible).
- `console` : interface texte uniquement.

Exemples :
- Mode auto (utile en SSH) :
  ```bash
  python3 code_labo1/touchscreen_app.py
  ```
  Si `DISPLAY` n'est pas défini, il sera automatiquement réglé sur `:0` pour
  cibler l'écran du Pi.
- Forcer le mode console (Ubuntu headless ou si vous voulez un prompt texte
  directement sur la console reliée à l'écran sans X/Wayland) :
  ```bash
  python3 code_labo1/touchscreen_app.py --mode console
  ```
- Forcer le mode graphique (Pi avec écran actif) :
  ```bash
  python3 code_labo1/touchscreen_app.py --mode gui
  ```
  - Si vous obtenez « couldn't connect to display ":0" », vérifiez qu'une
    session graphique est bien ouverte sur le Raspberry Pi (le bureau ou
    `startx`). Depuis SSH, assurez-vous aussi que l'utilisateur a accès au
    fichier Xauthority, par exemple :
    ```bash
    export DISPLAY=:0
    export XAUTHORITY=/home/pi/.Xauthority
    python3 code_labo1/touchscreen_app.py --mode gui
    ```

### Arrêt propre
- Mode graphique : `Ctrl+C` dans le terminal, touche **Échap** ou bouton
  « Quitter proprement ».
- Mode console : tapez `q` + Entrée ou `Ctrl+C`.
- Les signaux `SIGTERM`, `SIGINT` et `SIGHUP` sont gérés dans les deux modes
  pour garantir un redémarrage sain lors des prochains lancements.

### Faut-il créer un fichier `~/.xinitrc` ?
- **Si l'environnement graphique du Pi est déjà lancé** (bureau ouvert ou
  session autologin sur l'écran), vous n'avez rien à créer : exportez
  simplement `DISPLAY` et, si besoin, `XAUTHORITY` comme indiqué ci-dessus.
- **Si vous démarrez le Pi sans environnement graphique** (par exemple en
  mode console uniquement) et que vous souhaitez lancer l'interface via
  `startx`, un fichier `~/.xinitrc` peut être utile pour démarrer une session
  X minimale qui ouvre uniquement l'application. Exemple de fichier
  `~/.xinitrc` pour l'utilisateur `pi` :
  ```bash
  #!/usr/bin/env bash
  export DISPLAY=:0
  export XAUTHORITY=/home/pi/.Xauthority
  /usr/bin/python3 /home/pi/code_labo1/touchscreen_app.py
  ```
  Rendre le fichier exécutable puis lancer la session graphique minimaliste :
  ```bash
  chmod +x ~/.xinitrc
  startx
  ```
  Avec cette approche, `startx` ouvrira directement l'application sur
  l'écran, même si vous êtes connecté en SSH, sans nécessiter d'autre bureau.

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

## Forcer le démarrage sur l'interface graphique (sans lancer le code)
Si vous voulez simplement que le Raspberry Pi arrive systématiquement sur le
bureau graphique (interface Pixel) au démarrage — sans lancer l'application
Python — activez le mode graphique par défaut :

1. Vérifiez que l'environnement de bureau est installé (sur une image Lite,
   installez par exemple `sudo apt install -y raspberrypi-ui-mods lightdm`).
2. Activez la cible graphique et l'affichage de connexion LightDM :
   ```bash
   sudo systemctl set-default graphical.target
   sudo systemctl enable --now lightdm
   ```
3. (Optionnel) Pour ouvrir une session automatiquement sur l'utilisateur `pi`
   :
   - Lancez `sudo raspi-config`, menu **System Options > Boot / Auto Login >
     Desktop Autologin** ; ou
   - Éditez `/etc/lightdm/lightdm.conf` pour activer `autologin-user=pi` dans la
     section `[Seat:*]`.

Ainsi, le Pi bootera toujours sur l'interface graphique ; vous pourrez ensuite
exécuter `touchscreen_app.py` manuellement ou via systemd comme décrit ci-dessus.
