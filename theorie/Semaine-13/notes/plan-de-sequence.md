# Plan de séquence - Semaine 13

## Titre
Projet final Hydro-Limoilou — Lancement, intégration matérielle, amorce KiCad (CP1)

## Objectifs de la semaine
- Présenter le contexte fictif Hydro-Limoilou et la convention de topics MQTT
- Attribuer les `site-id` (poste-01 à poste-08) et les capteurs assignés
- Câbler le breadboard avec les modules breakout assignés sur l'hôte (T-Beam SUPREME ou LilyGO A7670G)
- Publier au moins **un capteur** sur le bon topic vers le broker local du Pi 5
- Amorcer le projet KiCad du shield (composants placés, début de connexions)
- Réussir le checkpoint **CP1 (5%)** en fin de semaine

## Contenu théorique

### Présentation du projet final
- Mise en situation Hydro-Limoilou (8 sites de télémétrie RF)
- Architecture cible : 8 sites indépendants + serveur central VM agrégateur
- Distinction des deux voies (LoRa #1-4, LTE #5-8)
- Sélection pédagogique des étudiant·es (remédiation ciblée)

### Convention de topics et contrat technique
- Schéma `hydro-limoilou/{site-id}/{telemetry|status|alarm|actuators}/...`
- Format des payloads JSON (champs `value`, `unit`, `ts`)
- Sous-topics analogiques par site (water_level, battery_v, wind_speed, etc.)
- Lecture du document `contrat-serveur-central.md`

### Câblage breadboard + I2C partagé
- Brochage des hôtes : T-Beam SUPREME (GPIO 17/18 = I2C primaire partagé) vs LilyGO A7670G (broches plus généreuses)
- Adresses I2C des modules (MPU6050 = 0x68, BH1750 = 0x23, BME280 interne = 0x76)
- Règles d'alimentation 3.3 V vs 5 V
- Tests pas-à-pas : un module à la fois

### Workflow KiCad (rappel)
- Création du projet shield-final
- Choix des bibliothèques de symboles et empreintes
- Placement des composants conformément à l'assignation
- Premières connexions d'alimentation et I2C

## Activités

### Théorie (2h)
- Présentation de la mise en situation Hydro-Limoilou (15 min)
- Distribution des assignations + site-id + lecture contrat MQTT (30 min)
- Démonstration du câblage type (T-Beam SUPREME et A7670G) (30 min)
- Rappel du workflow KiCad pour shield (45 min)

### Laboratoire (3h)
- Câblage breadboard avec les modules assignés
- Adaptation du firmware Labo 2 pour publier sur le bon topic
- Vérification via `mosquitto_sub` côté Pi 5
- Création et amorce du projet KiCad du shield
- **Checkpoint CP1 individuel en fin de séance** (vérification par l'enseignant)

## Travaux hors classe
- Compléter le câblage si non terminé en laboratoire
- Adapter le firmware pour publier 2-3 capteurs supplémentaires (vise le niveau 4 du critère 1.2)
- Continuer le schéma KiCad (vise ERC sans erreurs pour la sem. 14)
- Documenter le câblage (photo + notes dans le dépôt Git)

## Évaluation

### Checkpoint 1 (CP1) — Sommatif (5%)
- Critère 1.1 : Câblage breadboard conforme (1%)
- Critère 1.2 : Première publication MQTT (3%)
- Critère 1.3 : Amorce KiCad (1%)

Voir [grille-checkpoint-1.md](../../../evaluations/Evaluation-04/grille-checkpoint-1.md) pour les descripteurs détaillés.

## Ressources
- `evaluations/Evaluation-04/architecture-finale-projet.md` — Mises en situation et assignations
- `evaluations/Evaluation-04/contrat-serveur-central.md` — Topics et payloads
- `evaluations/Evaluation-04/grille-checkpoint-1.md` — Grille détaillée CP1
- Code firmware Labo 2 (à adapter pour les nouveaux topics et capteurs)

## Notes pour l'enseignant
- Préparer les kits par étudiant·e selon les assignations (modules breakout)
- Distribuer les credentials Mosquitto pour le compte `central` (à transmettre au CP2)
- Confirmer l'adresse de la VM agrégateur en début de séance
- Prévoir du matériel de remplacement (modules cassés, dupont supplémentaires)
- Vérifier en fin de séance que chaque étudiant·e a au moins **un message** visible côté broker local
- Adapter le rythme : la moitié de la classe en LoRa, l'autre en LTE — prévoir circulations différenciées
