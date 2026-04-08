# Plan de séquence - Semaine 10

## Titre
Meshtastic en pratique - Firmware, téléphones et tests de portée

## Objectifs de la semaine
- Flasher le firmware Meshtastic sur les T-Beam SUPREME
- Connecter l'application Meshtastic aux téléphones des étudiants
- Configurer le réseau mesh de la classe (canal, preset, rôles)
- Effectuer des tests de portée terrain et interpréter les métriques radio (RSSI, SNR)
- Explorer les fonctionnalités : messagerie, GPS, télémétrie, traceroute

## Contenu théorique

### Rappel LoRa et Meshtastic (bref)
- Rappel des concepts vus en semaine 8 (modulation CSS, SF/BW/CR)
- Pas de re-enseignement complet, juste un rafraîchissement

### Mise en route du firmware
- Procédure de flash via Web Flasher (flasher.meshtastic.org)
- Vérification du flash (écran OLED, Bluetooth, GPS)
- Dépannage des problèmes de flash courants

### Connexion au téléphone
- Installation de l'application Meshtastic (Android/iOS)
- Appairage Bluetooth avec le T-Beam
- Navigation dans l'interface de l'application (messages, carte, noeuds)

### Configuration du réseau de classe
- Paramètres essentiels (nom, région US, rôle CLIENT)
- Configuration du canal partagé (nom, preset MEDIUM_FAST)
- Distribution de la clé via QR code
- Presets Meshtastic et compromis portée/débit

### Métriques radio
- RSSI (Received Signal Strength Indicator) : échelle et interprétation
- SNR (Signal-to-Noise Ratio) : signification et seuils
- Visualisation des métriques dans l'application (onglet Noeuds)

### Tests de portée
- Méthodologie : équipes de 2, un fixe, un mobile
- Données à collecter (distance, RSSI, SNR, hops, environnement)
- Facteurs favorables et défavorables à la portée
- Règles empiriques par environnement

### Fonctionnalités avancées
- Rôles des noeuds (CLIENT, ROUTER, REPEATER, TRACKER, SENSOR)
- Télémétrie (batterie, utilisation radio)
- Position GPS et carte
- Fonctionnalité Traceroute

### Préparation du TP évalué (semaines 11-12)
- Aperçu de l'architecture : LoRa → Gateway WiFi → LLM → MQTT
- Exemples d'usage concrets

## Activités

### Théorie (1h)
- Rappel rapide LoRa/Meshtastic
- Procédure de flash et configuration
- Métriques radio (RSSI, SNR)
- Méthodologie des tests de portée

### Laboratoire (2h)
1. Flash du firmware Meshtastic sur les T-Beam (~15 min)
2. Installation de l'app et connexion Bluetooth (~15 min)
3. Configuration du canal de classe et test de communication (~15 min)
4. Tests de portée terrain en équipes de 2 (~45 min)
   - Test intérieur (couloirs, étages)
   - Test extérieur (s'éloigner progressivement)
   - Collecte des données (RSSI, SNR, distance)
5. Retour en classe et discussion des résultats (~15 min)
6. Exploration des fonctionnalités (traceroute, GPS, rôles) (~15 min)

## Travaux hors classe
- S'assurer que le firmware Meshtastic est fonctionnel
- Créer un compte API LLM (Groq, OpenAI ou Anthropic) si pas déjà fait
- Revoir les résultats de tests de portée
- Se familiariser avec les rôles de noeuds (CLIENT vs ROUTER)

## Évaluation
- Formatif : vérification du firmware fonctionnel et de la connexion téléphone
- Les tests de portée alimentent le TP évalué des semaines 11-12

## Ressources
- Web Flasher : flasher.meshtastic.org
- Application Meshtastic (Android/iOS)
- Interface web : client.meshtastic.org
- Documentation Meshtastic : meshtastic.org/docs

## Notes pour l'enseignant
- Préparer le QR code du canal de classe à l'avance
- Avoir quelques T-Beam de rechange en cas de problème de flash
- Vérifier que les antennes LoRa sont disponibles et en bon état
- Prévoir une sortie extérieure pour les tests de portée (~45 min)
- Avoir le pilote USB (CP210x ou CH340) sur une clé USB en cas de besoin
- Météo : vérifier avant le cours, prévoir un plan B intérieur si nécessaire
