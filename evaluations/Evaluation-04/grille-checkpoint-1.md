# Grille d'évaluation — Checkpoint 1 (Semaine 13)

**Cours :** 243-4J5-LI – Objets connectés
**Évaluation :** Projet final IdO Hydro-Limoilou — CP1
**Pondération :** **5%** (Capacité 1 : 2% — Capacité 2 : 3%)
**Modalité :** Vérification individuelle en laboratoire au cours de la semaine 13

---

## Échelle de notation

| Niveau | Description | Équivalence |
|:------:|-------------|:-----------:|
| **0** | Aucun travail remis ou travail non fonctionnel | 0% |
| **1** | Travail incomplet avec lacunes majeures | 40% |
| **2** | Travail partiel, en dessous du seuil | 50% |
| **3** | **Seuil de réussite** — Exigences minimales atteintes | 60% |
| **4** | Travail de bonne qualité, au-delà des attentes | 80% |
| **5** | Travail excellent, niveau optimal atteint | 100% |

---

## Objectif du checkpoint

Démontrer la **mise en route matérielle** du site : le breadboard est câblé conformément à l'assignation, le firmware initial publie au moins une mesure sur le bon topic MQTT, et le projet KiCad du shield est amorcé.

---

## Critère 1.1 : Câblage breadboard conforme à l'assignation (1%)

*Capacité 1 : Concevoir et programmer des objets connectés*
*Savoir-faire évalué (Plan de cours) : **Assembler les composants matériels***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Aucun câblage présenté ; modules absents |
| **1** | Câblage incomplet ; plusieurs modules absents ou inversés ; alimentation incorrecte (5 V au lieu de 3.3 V, GND manquant) |
| **2** | Câblage partiel ; 1-2 modules manquants ou mal raccordés ; risques de court-circuit visibles |
| **3** | **Seuil :** Tous les modules de l'assignation présents et correctement câblés (alim 3.3 V, GND, signaux). Pour les sites LoRa, le bus I2C primaire (GPIO 17/18) du T-Beam SUPREME est partagé sans conflit d'adresse. Aucun risque de court-circuit. |
| **4** | Câblage propre, organisé sur breadboard ; étiquetage clair des fils ou des rails ; longueurs de fils maîtrisées |
| **5** | Câblage exemplaire : code couleur respecté (rouge = +3.3 V, noir = GND, etc.), fils calibrés, photo documentaire dans le dépôt, schéma de câblage à jour |

---

## Critère 1.2 : Première publication MQTT vers le broker local (3%)

*Capacité 2 : Maîtriser les protocoles de communication IdO*
*Savoir-faire évalué (Plan de cours) : **Implémenter MQTT pour la communication entre appareils***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Aucune publication ; aucun message reçu sur le broker |
| **1** | Publication tentée mais sans atteindre le broker (mauvaise URL/port/credentials, échec de connexion WiFi/LTE) |
| **2** | Publication fonctionne mais topic non conforme à la convention `hydro-limoilou/{site-id}/...` (par ex. `test/data`) |
| **3** | **Seuil :** Au moins **un capteur** de l'assignation publie sur le bon topic conforme au contrat (ex. `hydro-limoilou/poste-03/telemetry/temperature`). Vérification réussie via `mosquitto_sub -t 'hydro-limoilou/poste-XX/#'` côté Pi 5. Payload JSON valide avec au minimum un champ `value`. |
| **4** | 2-3 capteurs publient ; payload contient `value`, `unit`, `ts` (timestamp Unix) ; fréquence de publication contrôlée (≥ 1 message / 10 s) |
| **5** | Tous les capteurs publient déjà ; QoS adapté ; gestion de la reconnexion automatique en cas de perte de lien ; logging série propre côté firmware |

---

## Critère 1.3 : Amorce du shield KiCad (1%)

*Capacité 1 : Concevoir et programmer des objets connectés*
*Savoir-faire évalué (Plan de cours) : **Concevoir un PCB pour l'interfaçage capteurs/actionneurs***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Aucun projet KiCad créé ou fichier inutilisable |
| **1** | Projet créé mais vide ou avec mauvaises bibliothèques |
| **2** | Composants placés mais aucune connexion ; symboles absents pour des modules clés |
| **3** | **Seuil :** Tous les composants de l'assignation placés dans le schéma ; au moins les connexions d'alimentation (3.3 V/GND) et I2C (SDA/SCL pour les capteurs concernés) établies ; symboles corrects pour l'hôte (T-Beam SUPREME ou A7670G) |
| **4** | Schéma cohérent avec connexions complètes ; labels de signaux présents ; ERC partiel (peu d'erreurs restantes) |
| **5** | Schéma quasi-fini : ERC sans erreurs, organisation claire en blocs fonctionnels, conventions de nommage respectées |

---

## Tableau récapitulatif CP1

| Critère | Capacité | Pondération | Note /5 | Points |
|---------|:--------:|:-----------:|:-------:|:------:|
| 1.1 Câblage breadboard | C1 | 1% | /5 | |
| 1.2 Première publication MQTT | C2 | 3% | /5 | |
| 1.3 Amorce KiCad | C1 | 1% | /5 | |
| **TOTAL CP1** | | **5%** | | **/5** |

---

## Calcul des points

Pour chaque critère :

$$\text{Points} = \frac{\text{Note sur 5}}{5} \times \text{Pondération du critère}$$

---

## Livrables attendus à la fin de la semaine 13

- [ ] Breadboard câblé avec tous les modules assignés (visuel + photo dans le dépôt)
- [ ] Code firmware initial (au moins 1 capteur publie) commité dans le dépôt Git
- [ ] Projet KiCad amorcé (composants placés, début de connexions)
- [ ] Vérification réussie de la publication via `mosquitto_sub` (capture d'écran ou log dans le dépôt)

---

**Fin du document — Grille CP1**
