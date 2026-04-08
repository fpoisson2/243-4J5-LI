# Plan de séquence - Semaine 12

## Titre
MQTT, finalisation et remise du TP LoRa-LLM

## Objectifs de la semaine
- Ajouter la publication MQTT au récepteur (PubSubClient)
- Implémenter la gestion robuste des erreurs (retry LLM, reconnexion WiFi/MQTT)
- Compléter la documentation du projet
- Remettre le TP évalué

## Contenu théorique

### Publication MQTT depuis Arduino
- Librairie PubSubClient
- Connexion au broker
- Publication sur des topics structurés (lora/donnees, lora/analyses, lora/actions)
- Vérification avec mosquitto_sub

### Robustesse
- Reconnexion automatique WiFi et MQTT
- Retry avec backoff sur les appels LLM
- Fallback local si le LLM est indisponible
- mqtt.loop() pour maintenir la connexion

### Documentation et remise
- Structure du README.md
- Checklist de sécurité
- Vérification de l'historique git

## Activités

### Théorie (30 min)
- Rappel de l'architecture et des critères d'évaluation
- Publication MQTT depuis Arduino
- Gestion des erreurs et fallback

### Laboratoire (2h30)
1. MQTT (~1h)
   - Installer PubSubClient
   - Connecter au broker MQTT
   - Publier les données brutes et les analyses
   - Vérifier avec mosquitto_sub
2. Robustesse (~30 min)
   - Ajouter la reconnexion automatique
   - Implémenter le retry LLM
   - Tester le fallback
3. Documentation et remise (~1h)
   - README.md complet
   - Vérifier .gitignore et l'historique git
   - config.example.h à jour
   - Commit final et push

## Évaluation
- **TP évalué (20%)** — remise en fin de séance
- Configuration API (25%), Prompt Engineering (25%), Pipeline (30%), Documentation (20%)

## Notes pour l'enseignant
- Avoir le broker MQTT fonctionnel et accessible
- Garder du temps individuel pour aider les étudiants en difficulté
- Vérifier les remises sur GitHub en fin de séance
- Vérifier l'absence de secrets dans les dépôts
