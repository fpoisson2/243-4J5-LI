# Plan de séquence - Semaine 09

## Titre
Soudure PCB et introduction aux LLM sur ESP32

## Objectifs de la semaine
- Assembler les composants sur le PCB conçu en semaine 7
- Créer un dépôt Git structuré pour un projet Arduino
- Effectuer un appel HTTP à une API LLM depuis un ESP32
- Concevoir un prompt créatif lié à une valeur analogique

## Contenu théorique (bref, contextuel)

### Soudure THT
- Ordre de soudure : du plus bas au plus haut
- Technique : fer sur pastille et patte, étain sur la jonction
- Vérification : inspection visuelle, test de continuité

### LLM et API HTTP
- Qu'est-ce qu'un LLM (grand modèle de langage)
- Format d'API compatible OpenAI (requête POST, messages, réponse JSON)
- Groq : API gratuite pour accéder à des LLM rapides

## Activités

### Partie 1 : Soudure du PCB (1h30)
- Soudure des composants THT sur le PCB
- Vérification et test de continuité
- Validation du fonctionnement de base

### Partie 2 : Introduction aux LLM sur ESP32 (1h30)
- Création du dépôt Git avec .gitignore
- Création du compte Groq et obtention de la clé API
- Conception du scénario créatif (potentiomètre → prompt)
- Écriture du code Arduino (WiFi + HTTP POST + parsing JSON)
- Test et validation avec le moniteur série
- Commit propre (sans secrets)

## Travaux hors classe
- Terminer le code si non complété en classe
- Expérimenter avec différents prompts et modèles
- Explorer l'ajout d'un écran OLED pour afficher les réponses

## Évaluation
- **Évaluation sommative:** TP Intégration LLM et automatisation (20%)
  - Flux capteurs → traitement → action (15% Capacité 1)
  - Configuration et communication (5% Capacité 2)

## Ressources
- Documentation Groq : console.groq.com
- Documentation ArduinoJson
- Exemples HTTPClient pour ESP32

## Notes pour l'enseignant
- Les PCB ont été reçus, les distribuer en début de séance
- Prévoir du matériel de soudure de remplacement (étain, flux)
- Avoir quelques potentiomètres supplémentaires
- Vérifier la disponibilité du réseau WiFi dans le local
