# Plan de séquence - Semaine 11

## Titre
Liaison LoRa point à point et intégration LLM (IDE Arduino)

## Objectifs de la semaine
- Coder un émetteur LoRa qui lit un potentiomètre et envoie la valeur via RadioLib
- Coder un récepteur LoRa qui se connecte au WiFi et appelle un LLM
- Contrôler une DEL selon la réponse du LLM
- Appliquer les bonnes pratiques de sécurité (config.h ignoré par git)

## Contenu théorique

### Librairie RadioLib
- Communication LoRa directe sans Meshtastic
- Configuration du SX1262 (fréquence, SF, BW, CR)
- Émission et réception de messages
- Lecture des métriques (RSSI, SNR)

### Émetteur LoRa
- Lecture du potentiomètre (ADC)
- Construction d'un message JSON (ArduinoJson)
- Envoi via radio.transmit()
- Écoute de la réponse LoRa du récepteur (décision du LLM)
- DEL action : contrôlée par la décision du LLM (on/off)
- Affichage OLED de la trame et de la décision reçue

### Récepteur LoRa + WiFi + LLM
- Réception des messages (radio.receive())
- DEL status : clignote à chaque réception / appel LLM
- Connexion WiFi depuis le T-Beam
- Appel HTTP POST à l'API LLM (format compatible OpenAI)
- **Structured output obligatoire** via `response_format` / `json_schema` (schéma défini par l'étudiant)
- Parsing de la réponse JSON
- Renvoi de la décision à l'émetteur via radio.transmit()
- Affichage OLED du message reçu, RSSI/SNR et réponse LLM

### Sécurité
- Fichier config.h pour les secrets (même approche que le labo 4)
- config.example.h commité (sans valeurs réelles)
- .gitignore obligatoire
- Pénalités pour clés exposées

## Activités

### Théorie (1h)
- Architecture du TP (émetteur/récepteur)
- Configuration de RadioLib
- Code de l'émetteur et du récepteur
- Appel LLM depuis l'ESP32 (rappel du labo 4)

### Laboratoire (2h)
1. Émetteur (~45 min)
   - Initialiser RadioLib (SX1262) et l'OLED
   - Lire le potentiomètre et envoyer via LoRa
   - Afficher la trame sur l'OLED
   - Écouter la réponse LoRa du récepteur
   - DEL action : on/off selon la décision du LLM
2. Récepteur (~1h15)
   - Initialiser RadioLib + OLED + WiFi
   - Recevoir les messages LoRa (DEL status clignote)
   - Appeler l'API LLM
   - Renvoyer la décision via LoRa
   - Afficher message reçu, RSSI/SNR et réponse LLM sur l'OLED

## Travaux hors classe
- Finaliser le pipeline (ajout MQTT, gestion d'erreurs)
- Optimiser le prompt système
- Préparer la documentation (README.md)
- Se préparer pour la remise de la semaine 12

## Évaluation
- TP évalué (20%) — début cette semaine, remise semaine 12

## Ressources
- RadioLib : github.com/jgromes/RadioLib
- API Groq : console.groq.com
- ArduinoJson : arduinojson.org

## Notes pour l'enseignant
- Vérifier que les pins SX1262 sont corrects pour le T-Beam Supreme
- Avoir le réseau WiFi accessible depuis les T-Beam
- Distribuer les credentials WiFi aux étudiants
- Remettre le firmware Arduino sur les T-Beam (flash par-dessus Meshtastic)
