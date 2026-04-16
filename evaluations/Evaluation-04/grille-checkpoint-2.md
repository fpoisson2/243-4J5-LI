# Grille d'évaluation — Checkpoint 2 (Semaine 14)

**Cours :** 243-4J5-LI – Objets connectés
**Évaluation :** Projet final IdO Hydro-Limoilou — CP2
**Pondération :** **10%** (Capacité 1 : 4% — Capacité 2 : 6%)
**Modalité :** Vérification individuelle en laboratoire au cours de la semaine 14

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

Démontrer l'**intégration logicielle complète** : tous les capteurs assignés publient sur les bons topics, au moins une alarme est fonctionnelle, l'interface tactile du Pi 5 affiche le site sur 3 pages, le serveur central voit le site, et le schéma KiCad du shield est complet (ERC sans erreurs).

---

## Critère 2.1 : Tous les capteurs/actionneurs publient sur les bons topics (3%)

*Capacité 2 : Maîtriser les protocoles de communication IdO*
*Savoir-faire évalués (Plan de cours) : **Implémenter MQTT pour la communication entre appareils** + **Programmer des scripts pour publier/souscrire via MQTT***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Aucun capteur ne publie |
| **1** | 1 seul capteur publie ; topics incohérents avec la convention |
| **2** | Plusieurs capteurs publient mais avec écarts (mauvais sous-topic, payloads non conformes au contrat `contrat-serveur-central.md`) |
| **3** | **Seuil :** **Tous** les capteurs assignés publient sur les bons topics conformes au contrat ; payloads JSON valides avec champs obligatoires (`value`, `unit`, `ts`) ; au moins une LED contrôlable via topic descendant `actuators/led_N` |
| **4** | Topics et payloads strictement conformes ; fréquences de publication respectées (par défaut ≥ 1 message / 5 s pour la télémétrie) ; topic `status` publié périodiquement ; dégradation propre si capteur défaillant (publication d'une valeur null ou message d'erreur) |
| **5** | QoS adapté par topic (0 pour télémétrie haute fréquence, 1 pour alarmes) ; rétention activée pour `status` ; horodatage cohérent entre tous les topics ; pas de doublons de messages |

---

## Critère 2.2 : Alarmes fonctionnelles (2%)

*Capacité 1 : Concevoir et programmer des objets connectés*
*Savoir-faire évalué (Plan de cours) : **Lire, interpréter, traiter et filtrer les données***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Aucune alarme implémentée |
| **1** | Code d'alarme présent mais ne se déclenche jamais |
| **2** | Alarme se déclenche par seuil mais publication absente ou non conforme |
| **3** | **Seuil :** Au moins **une alarme** déclenchable et publiée sur `hydro-limoilou/{site-id}/alarm/{type}` cohérente avec la mise en situation du site (ex. intrusion sur cabinet fluvial, inclinaison sur mât météo, niveau d'eau, choc sur refuge) ; payload conforme au contrat |
| **4** | Plusieurs alarmes (≥ 2) avec niveaux (`info`, `warning`, `critical`) ; hystérésis pour éviter le clignotement ; ack côté tactile ou via topic descendant possible |
| **5** | Système d'alarme complet : règles de déclenchement documentées, journalisation locale, alarme persistante jusqu'à ack, gestion de la priorité quand plusieurs alarmes concurrentes |

---

## Critère 2.3 : Extension de l'interface tactile (3 pages) (1%)

*Capacité 1 : Concevoir et programmer des objets connectés*
*Savoir-faire évalué (Plan de cours) : **Créer une interface utilisateur en temps réel***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Interface tactile non modifiée par rapport au Labo 2 |
| **1** | Une seule des 3 pages amorcée ; affichage figé ; pas de souscription MQTT |
| **2** | 2 pages présentes mais l'une au moins ne se met pas à jour |
| **3** | **Seuil :** Les **3 pages** fonctionnelles et navigables : (a) **Télémétrie temps réel** — affichage des valeurs courantes des capteurs du site, (b) **Alarmes** — liste des alarmes actives + bouton ack, (c) **État du lien** — RSSI/signal + uptime |
| **4** | Mises à jour fluides (< 1 s de latence) ; navigation tactile claire entre pages ; visuels sobres et lisibles plein écran |
| **5** | Interface professionnelle : indicateurs visuels (jauges, codes couleur cohérents), gestion gracieuse des pertes de données (affichage "?" plutôt que valeur stale), plein écran sur l'écran du Pi |

---

## Critère 2.4 : Visibilité du site depuis le serveur central (3%)

*Capacité 2 : Maîtriser les protocoles de communication IdO*
*Savoir-faire évalués (Plan de cours) : **Implémenter une communication sécurisée (TLS/SSL)** + **Configurer un courtier MQTT (Mosquitto)***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Tunnel Cloudflare absent ou broker non exposé |
| **1** | Tunnel présent mais broker inaccessible depuis l'extérieur |
| **2** | Broker accessible mais authentification non configurée ou topics non visibles côté VM |
| **3** | **Seuil :** Le serveur central (VM enseignant) **voit le site** : commande de validation côté VM réussit (souscription au wildcard du site), les topics du site apparaissent dans le dashboard global de la VM. Authentification user/password configurée côté Mosquitto. Accès chiffré via WSS:443 par tunnel Cloudflare |
| **4** | Documentation claire de la procédure de connexion VM ↔ broker (URL, credentials, topics) dans le dépôt ; topics conformes au contrat |
| **5** | Sécurité robuste : ACL côté Mosquitto restreignant l'accès aux topics du site (pas d'accès aux topics des autres étudiants) ; rotation possible des credentials ; monitoring de la session côté VM |

---

## Critère 2.5 : Schéma KiCad complet, ERC sans erreurs (1%)

*Capacité 1 : Concevoir et programmer des objets connectés*
*Savoir-faire évalué (Plan de cours) : **Concevoir un PCB pour l'interfaçage capteurs/actionneurs***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Schéma absent ou inutilisable |
| **1** | Schéma incomplet ; nombreuses erreurs ERC non traitées |
| **2** | Schéma globalement complet mais avec erreurs ERC majeures (alim manquante, broches en l'air, conflits de noms) |
| **3** | **Seuil :** Schéma complet, tous les modules connectés conformément au câblage breadboard, **ERC sans erreurs** (warnings tolérés s'ils sont justifiés et documentés) |
| **4** | Schéma organisé en blocs fonctionnels (alim, capteurs I2C, capteurs digital, actionneurs), labels hiérarchiques utilisés, decoupling capacitors ajoutés sur les rails d'alim |
| **5** | Schéma de qualité professionnelle : annotations claires (références alphanumériques cohérentes), conventions de nommage respectées, documentation intégrée (texte explicatif sur le schéma) |

---

## Tableau récapitulatif CP2

| Critère | Capacité | Pondération | Note /5 | Points |
|---------|:--------:|:-----------:|:-------:|:------:|
| 2.1 Tous les capteurs publient | C2 | 3% | /5 | |
| 2.2 Alarmes fonctionnelles | C1 | 2% | /5 | |
| 2.3 Interface tactile (3 pages) | C1 | 1% | /5 | |
| 2.4 Visibilité serveur central | C2 | 3% | /5 | |
| 2.5 Schéma KiCad complet (ERC OK) | C1 | 1% | /5 | |
| **TOTAL CP2** | | **10%** | | **/10** |

---

## Calcul des points

Pour chaque critère :

$$\text{Points} = \frac{\text{Note sur 5}}{5} \times \text{Pondération du critère}$$

---

## Livrables attendus à la fin de la semaine 14

- [ ] Tous les capteurs et actionneurs assignés publient sur les bons topics (vérifié via `mosquitto_sub`)
- [ ] Au moins une alarme déclenchable et publiée
- [ ] Interface tactile étendue avec les 3 pages opérationnelles
- [ ] Tunnel Cloudflare actif, site visible côté serveur central VM
- [ ] Schéma KiCad complet, ERC sans erreurs (rapport ERC commité)

---

**Fin du document — Grille CP2**
