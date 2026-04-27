# Plan de séquence - Semaine 14

## Titre
Projet final Hydro-Limoilou — Intégration logicielle complète (CP2)

## Objectifs de la semaine
- Finaliser la publication MQTT pour **tous** les capteurs et actionneurs assignés
- Implémenter au moins **une alarme** déclenchable cohérente avec la mise en situation
- Étendre l'interface tactile du Pi 5 sur **3 pages** (télémétrie, alarmes, état lien)
- Exposer le broker via Cloudflare Tunnel pour rendre le site **visible côté serveur central VM**
- Compléter le **schéma KiCad** du shield (ERC sans erreurs)
- Réussir le checkpoint **CP2 (10%)** en fin de semaine

## Format de la semaine
**Pas de bloc théorique** — l'enseignant fait une **brève intro de 15-20 minutes** en début de séance pour rappeler les objectifs CP2 et résoudre rapidement les questions issues de la sem. 13. Le reste du temps (≈ 4 h 30) est en **labo libre** sur les postes individuels.

## Activités

### Brève intro (15-20 min)
- Tour de table rapide : où en est chaque étudiant après le CP1
- Rappel des 5 critères du CP2 et de leurs livrables
- Rappel de la procédure de transmission des credentials Mosquitto à l'enseignant
- Réponse aux questions éventuelles

### Labo libre (≈ 4 h 30)
Travail individuel sur les postes. Ordre suggéré :
1. Compléter la publication MQTT pour tous les capteurs
2. Implémenter une alarme + publication sur `alarm/{type}`
3. Étendre l'interface tactile (3 pages)
4. Configurer Mosquitto (auth + ACL) et activer le tunnel Cloudflare
5. Transmettre les credentials du compte `central` à l'enseignant
6. Compléter le schéma KiCad (ERC sans erreurs)

L'enseignant circule pour soutenir, débloquer et valider individuellement.

### Checkpoint CP2 individuel (en fin de séance)
Vérification critère par critère devant l'étudiant.

## Travaux hors classe
- Préparer le scénario de la démo (3 scénarios à présenter en sem. 15)
- Commencer la documentation (README, contrat topics, photos)
- Démarrer le routage PCB (placement composants)

## Évaluation

### Checkpoint 2 (CP2) — Sommatif (10%)
- Critère 2.1 : Tous les capteurs publient sur les bons topics (3%)
- Critère 2.2 : Alarmes fonctionnelles (2%)
- Critère 2.3 : Interface tactile (3 pages) (1%)
- Critère 2.4 : Visibilité du site depuis le serveur central (3%)
- Critère 2.5 : Schéma KiCad complet (ERC sans erreurs) (1%)

Voir [grille-checkpoint-2.md](../../../evaluations/Evaluation-04/grille-checkpoint-2.md) pour les descripteurs détaillés.

## Ressources
- `evaluations/Evaluation-04/contrat-serveur-central.md` — Référence des topics
- `evaluations/Evaluation-04/grille-checkpoint-2.md` — Grille détaillée CP2
- Code Labo 2 (interface tactile à étendre)
- Documentation Mosquitto (ACL, mosquitto_passwd)
- Documentation paho-mqtt (Python)

## Notes pour l'enseignant
- Préparer un script de validation côté VM pour tester rapidement chaque site
- Disposer d'une liste pré-formatée pour collecter les credentials de chaque étudiant
- Vérifier que chaque site est visible côté VM **avant** la fin de la séance (pour donner la note CP2 immédiatement)
- Anticiper les difficultés sur la voie LoRa (deux T-Beam à coordonner) : prévoir 50% du temps de circulation pour ces étudiants
- Pour les étudiants en retard sur le CP1, encourager le rattrapage en début de séance
