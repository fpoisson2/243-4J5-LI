# Grille d'évaluation — Projet final IdO Hydro-Limoilou (récapitulatif)

**Cours :** 243-4J5-LI – Objets connectés
**Évaluation :** Projet final IdO avec PCB et déploiement sur 8 sites
**Pondération totale :** 35% (Capacité 1 : 10% — Capacité 2 : 25%)
**Modalités :** 3 checkpoints hebdomadaires sommatifs (semaines 13, 14, 15)

---

## Distribution des points

Le projet est évalué en **3 checkpoints à pondération croissante**, pour refléter le fait que la dernière semaine cumule le plus de livrables (démo, finalisation PCB, documentation complète) :

| Checkpoint | Semaine | Pondération | Focus principal | Détails |
|------------|:-------:|:-----------:|----------------|---------|
| **CP1** | 13 | **5%** | Intégration matérielle + 1ère publication MQTT + amorce KiCad | [grille-checkpoint-1.md](./grille-checkpoint-1.md) |
| **CP2** | 14 | **10%** | Tous les capteurs publient + alarmes + interface tactile + visibilité VM + schéma KiCad complet | [grille-checkpoint-2.md](./grille-checkpoint-2.md) |
| **CP3** | 15 | **20%** | Démo 3 scénarios + finalisation PCB (DRC + Gerbers) + documentation + site stable côté VM | [grille-checkpoint-3.md](./grille-checkpoint-3.md) |
| | | **35%** | | |

---

## Échelle de notation (commune aux 3 checkpoints)

| Niveau | Description | Équivalence |
|:------:|-------------|:-----------:|
| **0** | Aucun travail remis ou travail non fonctionnel | 0% |
| **1** | Travail incomplet avec lacunes majeures | 40% |
| **2** | Travail partiel, en dessous du seuil | 50% |
| **3** | **Seuil de réussite** — Exigences minimales atteintes | 60% |
| **4** | Travail de bonne qualité, au-delà des attentes | 80% |
| **5** | Travail excellent, niveau optimal atteint | 100% |

---

## Correspondance avec les capacités et les savoir-faire du plan de cours

### Capacité 1 — Concevoir et programmer des objets connectés (10% du projet final)

| Savoir-faire (Plan de cours, section 2.1) | Critères concernés |
|-------------------------------------------|---------------------|
| Assembler les composants matériels | CP1 — 1.1 |
| Concevoir un PCB pour l'interfaçage capteurs/actionneurs | CP1 — 1.3 ; CP2 — 2.5 ; CP3 — 3.2 |
| Lire, interpréter, traiter et filtrer les données | CP2 — 2.2 |
| Créer une interface utilisateur en temps réel | CP2 — 2.3 |
| Documenter le processus de conception | CP3 — 3.3 |

### Capacité 2 — Maîtriser les protocoles de communication IdO (25% du projet final)

| Savoir-faire (Plan de cours, section 2.1) | Critères concernés |
|-------------------------------------------|---------------------|
| Implémenter MQTT pour la communication entre appareils | CP1 — 1.2 ; CP2 — 2.1 |
| Programmer des scripts pour publier/souscrire via MQTT | CP2 — 2.1 |
| Implémenter une communication sécurisée (TLS/SSL) | CP2 — 2.4 |
| Configurer un courtier MQTT (Mosquitto) | CP2 — 2.4 ; CP3 — 3.4 |
| Configurer les paramètres de QoS selon les besoins | CP3 — 3.6 |
| Surveiller et optimiser les performances réseau | CP3 — 3.1, 3.5 |

---

## Tableau récapitulatif des critères

### CP1 — Semaine 13 (5%)

| Critère | Capacité | Savoir-faire | Pondération |
|---------|:--------:|---|:-----------:|
| 1.1 Câblage breadboard conforme à l'assignation | C1 | Assembler les composants matériels | 1% |
| 1.2 Première publication MQTT vers le broker local | C2 | Implémenter MQTT pour la communication entre appareils | 3% |
| 1.3 Amorce du shield KiCad | C1 | Concevoir un PCB pour l'interfaçage capteurs/actionneurs | 1% |
| **Sous-total CP1** | | | **5%** |

### CP2 — Semaine 14 (10%)

| Critère | Capacité | Savoir-faire | Pondération |
|---------|:--------:|---|:-----------:|
| 2.1 Tous les capteurs publient sur les bons topics | C2 | Implémenter MQTT + programmer scripts publier/souscrire | 3% |
| 2.2 Alarmes fonctionnelles | C1 | Lire, interpréter, traiter et filtrer les données | 2% |
| 2.3 Extension de l'interface tactile (3 pages) | C1 | Créer une interface utilisateur en temps réel | 1% |
| 2.4 Visibilité du site depuis le serveur central | C2 | Implémenter une communication sécurisée (TLS/SSL) + configurer Mosquitto | 3% |
| 2.5 Schéma KiCad complet (ERC sans erreurs) | C1 | Concevoir un PCB pour l'interfaçage capteurs/actionneurs | 1% |
| **Sous-total CP2** | | | **10%** |

### CP3 — Semaine 15 (20%)

| Critère | Capacité | Savoir-faire | Pondération |
|---------|:--------:|---|:-----------:|
| 3.1 Démonstration des 3 scénarios | C2 | Surveiller et optimiser les performances réseau | 7% |
| 3.2 PCB finalisé (DRC + Gerbers + BOM) | C1 | Concevoir un PCB pour l'interfaçage capteurs/actionneurs | 3% |
| 3.3 Documentation du processus de conception | C1 | Documenter le processus de conception | 1% |
| 3.4 Documentation des protocoles et topics | C2 | Configurer un courtier MQTT (Mosquitto) | 3% |
| 3.5 Site reste visible côté VM pendant la démo | C2 | Surveiller et optimiser les performances réseau | 3% |
| 3.6 QoS et fiabilité MQTT | C2 | Configurer les paramètres de QoS selon les besoins | 3% |
| **Sous-total CP3** | | | **20%** |

| **TOTAL projet** | | | **35%** |

---

## Calcul de la note finale

Pour chaque critère :

$$\text{Points} = \frac{\text{Note sur 5}}{5} \times \text{Pondération du critère}$$

La note finale du projet est la somme des points pour les 14 critères répartis sur les 3 checkpoints (max 30%).

---

## Politique de remise tardive

Conformément à l'article 12.3 de la PIEA : **10% de pénalité par jour de retard** sur le checkpoint manqué (week-ends inclus), refusé après 5 jours.

Un checkpoint manqué (note 0) ne ferme pas l'accès aux suivants : la progression est jugée à chaque semaine, et la note finale globale reflète le jugement de l'enseignant sur l'atteinte des capacités.

## Re-vérification au CP3

À la démonstration finale (CP3), l'enseignant **revérifie le bon fonctionnement** des éléments validés aux CP1 et CP2 (câblage, publication MQTT, alarmes, interface tactile, visibilité VM, schéma KiCad). **Les notes des CP1 et CP2 ne sont pas révisées** — la démo finale ne peut pas faire perdre de points sur les checkpoints antérieurs.

En revanche, **CP1 + CP2 sont des prérequis fonctionnels** au CP3 : si un élément validé antérieurement ne fonctionne plus à la démo, certains scénarios du CP3 deviennent infaisables, ce qui affecte la note du CP3 lui-même.

---

## Documents associés

- [grille-checkpoint-1.md](./grille-checkpoint-1.md) — Grille détaillée CP1 (sem. 13)
- [grille-checkpoint-2.md](./grille-checkpoint-2.md) — Grille détaillée CP2 (sem. 14)
- [grille-checkpoint-3.md](./grille-checkpoint-3.md) — Grille détaillée CP3 (sem. 15)
- [architecture-finale-projet.md](./architecture-finale-projet.md) — Architecture, mises en situation et assignations
- [contrat-serveur-central.md](./contrat-serveur-central.md) — Contrat technique avec le serveur central VM

---

**Fin du document — Récapitulatif Grille Projet final**
