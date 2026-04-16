# Plan de séquence - Semaine 15

## Titre
Projet final Hydro-Limoilou — Tests, finalisation PCB, démo et remise (CP3)

## Objectifs de la semaine
- Tester la robustesse du système avec **3 scénarios** : nominal, alarme, perte/reprise de lien
- Finaliser le routage PCB du shield dans KiCad (DRC sans erreurs, Gerbers, BOM)
- Compléter la documentation du projet (processus de conception + topics + protocoles)
- Produire une vidéo de démonstration (≤ 5 min)
- Démontrer le système complet en direct devant l'enseignant
- Réussir le checkpoint final **CP3 (20%)** — démo + livrables

## Format de la semaine
**Pas de bloc théorique** — l'enseignant fait une **brève intro de 15-20 minutes** en début de séance pour rappeler le déroulement de la démo et les livrables attendus. Le reste du temps (≈ 4 h 30) est en **labo / démo individuelle**.

## Activités

### Brève intro (15-20 min)
- Rappel des 3 scénarios à démontrer
- Rappel des livrables (KiCad complet, Gerbers, BOM, code Git, doc, vidéo)
- Rappel de la clause de re-vérification (CP1 + CP2 vérifiés mais pas re-notés au CP3)
- Annonce de l'horaire de passage des démos individuelles

### Labo — finalisation et préparation de la démo (≈ 2 h 30)
Travail individuel sur les postes :
- Compléter le routage PCB (DRC sans erreurs)
- Générer Gerbers et BOM
- Compléter README + documentation des topics
- Tourner la vidéo de démo (≤ 5 min)
- Préparer le script de la démo (3 scénarios)

L'enseignant circule pour débloquer.

### Démos individuelles (≈ 2 h)
Passage individuel devant l'enseignant (≈ 15 min par étudiant·e) :
1. Préparation : système démarré, dashboard VM ouvert
2. Présentation rapide du site et de la mise en situation (3 min)
3. Démonstration des 3 scénarios (10 min)
4. Remise des livrables (lien Git)
5. Rétroaction immédiate (2 min)

Évaluation CP3 immédiatement après chaque démo.

## Travaux hors classe
- Aucun (fin de session)

## Évaluation

### Checkpoint 3 (CP3) — Sommatif (20%)
- Critère 3.1 : Démo 3 scénarios (7%)
- Critère 3.2 : PCB finalisé (DRC + Gerbers + BOM) (3%)
- Critère 3.3 : Documentation processus de conception (1%)
- Critère 3.4 : Documentation protocoles et topics (3%)
- Critère 3.5 : Site visible côté VM pendant toute la démo (3%)
- Critère 3.6 : QoS et fiabilité MQTT (3%)

Voir [grille-checkpoint-3.md](../../../evaluations/Evaluation-04/grille-checkpoint-3.md) pour les descripteurs détaillés.

### Note finale du projet (cumul des 3 checkpoints)
- CP1 (sem. 13) : 5%
- CP2 (sem. 14) : 10%
- CP3 (sem. 15) : 20%
- **Total : 35%** (Capacité 1 : 10% — Capacité 2 : 25%)

## Ressources
- `evaluations/Evaluation-04/grille-checkpoint-3.md` — Grille détaillée CP3
- `evaluations/Evaluation-04/grille-projet-final.md` — Récapitulatif global
- `evaluations/Evaluation-04/contrat-serveur-central.md` — Topics (référence finale)
- Documentation KiCad (DRC, génération Gerbers/BOM)

## Notes pour l'enseignant
- Préparer un horaire de passage pour les démos individuelles (≈ 15 min × 8 étudiant·es = 2 h)
- Garder un tableau de bord de la VM ouvert pendant toutes les démos pour valider 3.5
- Consigner les notes au fur et à mesure dans la grille
- Prévoir 5 min de rétroaction immédiate après chaque démo
- Faire un bilan global du cours en fin de séance
- Organiser le retour du matériel prêté (T-Beam, A7670G, modules breakout, Pi 5 si applicable)
