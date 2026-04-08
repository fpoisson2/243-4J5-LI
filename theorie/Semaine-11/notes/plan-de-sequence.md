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
- DEL de status à l'émission

### Récepteur LoRa + WiFi + LLM
- Réception des messages (radio.receive())
- Connexion WiFi depuis le T-Beam
- Appel HTTP POST à l'API Groq (format compatible OpenAI)
- Parsing de la réponse JSON
- Contrôle de la DEL selon l'action du LLM

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
   - Initialiser RadioLib (SX1262)
   - Lire le potentiomètre
   - Envoyer la valeur via LoRa
   - DEL qui clignote à l'envoi
2. Récepteur (~1h15)
   - Initialiser RadioLib (même configuration)
   - Recevoir les messages LoRa
   - Connecter au WiFi
   - Appeler l'API Groq
   - Contrôler la DEL selon la réponse LLM
   - Afficher RSSI/SNR dans le moniteur série

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
