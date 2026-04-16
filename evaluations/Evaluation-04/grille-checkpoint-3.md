# Grille d'évaluation — Checkpoint 3 (Semaine 15)

**Cours :** 243-4J5-LI – Objets connectés
**Évaluation :** Projet final IdO Hydro-Limoilou — CP3 (démo finale)
**Pondération :** **20%** (Capacité 1 : 4% — Capacité 2 : 16%)
**Modalité :** Démonstration en direct + remise des livrables, semaine 15

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

Démontrer la **maturité du système complet** : démonstration en direct des 3 scénarios (nominal, alarme, perte/reprise de lien), finalisation du PCB (DRC, Gerbers, BOM), documentation complète, stabilité observable du site sur le serveur central pendant toute la démo.

## Re-vérification des éléments des CP précédents

À la démonstration finale, l'enseignant **revérifie le bon fonctionnement** des éléments validés aux CP1 (câblage, première publication MQTT, amorce KiCad) et CP2 (tous les capteurs publient, alarmes, interface tactile, visibilité VM, schéma KiCad complet).

**Les notes des CP1 et CP2 ne sont pas révisées** — la démo finale ne peut pas faire perdre de points sur les checkpoints antérieurs. En revanche, si un élément validé à un CP précédent ne fonctionne plus à la démo, cela peut empêcher de démontrer un scénario du CP3 (par exemple, si l'alarme du CP2 ne déclenche plus, le scénario 2 du critère 3.1 ne peut pas être complété, ce qui affecte la note du CP3).

En clair : **CP1 + CP2 sont des prérequis fonctionnels** au CP3, mais ne sont pas re-évalués.

---

## Critère 3.1 : Démonstration des 3 scénarios (7%)

*Capacité 2 : Maîtriser les protocoles de communication IdO*
*Savoir-faire évalué (Plan de cours) : **Surveiller et optimiser les performances réseau***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Aucune démonstration ou démonstration non fonctionnelle |
| **1** | Seul le scénario nominal partiellement démontré ; alarme et perte de lien échouent |
| **2** | Scénario nominal OK mais alarme ou perte de lien échoue |
| **3** | **Seuil :** Les **3 scénarios** sont démontrés en direct : (a) **nominal** — publication continue + dashboard VM voit le site, (b) **alarme** — déclenchement physique (porte ouverte, choc, intrusion, etc.) → topic alarm publié → affichage tactile + dashboard VM, (c) **perte/reprise de lien** — coupure WiFi/LTE puis reconnexion + republication automatique |
| **4** | Démonstration fluide ; explication technique claire à chaque étape ; mesures (latence, RSSI/SNR ou signal LTE) commentées en direct |
| **5** | Démonstration maîtrisée : préparation visible (script de démo écrit), gestion sereine des imprévus, comparaison entre comportement observé et attentes documentées |

---

## Critère 3.2 : PCB finalisé (DRC + Gerbers + BOM) (3%)

*Capacité 1 : Concevoir et programmer des objets connectés*
*Savoir-faire évalué (Plan de cours) : **Concevoir un PCB pour l'interfaçage capteurs/actionneurs***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Aucun PCB conçu ou fichier KiCad inutilisable |
| **1** | Routage commencé mais incomplet ; nombreuses traces manquantes |
| **2** | Routage globalement complet mais erreurs DRC majeures (clearances violées, traces non connectées, plan de masse manquant) |
| **3** | **Seuil :** PCB 2 couches routé conformément au schéma ; **DRC sans erreurs** ; plan de masse présent ; **Gerbers et BOM** générés et présents dans le dépôt |
| **4** | Routage soigné (largeurs de traces adaptées au courant, vias raisonnables, composants regroupés logiquement) ; dimensions du shield compatibles avec l'hôte (T-Beam SUPREME ou A7670G) ; sérigraphie présente avec références |
| **5** | Routage de qualité professionnelle : sérigraphie complète (références + valeurs + indicateurs de polarité), tous les composants identifiés, fichiers prêts pour fabrication directe (gerber view sans surprise), 3D render plausible |

---

## Critère 3.3 : Documentation du processus de conception (1%)

*Capacité 1 : Concevoir et programmer des objets connectés*
*Savoir-faire évalué (Plan de cours) : **Documenter le processus de conception***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Aucune documentation remise |
| **1** | Documentation très sommaire (< 1 page) ; aucune description du site ni du câblage |
| **2** | Documentation partielle ; description du site présente mais schéma de câblage absent ou code non documenté |
| **3** | **Seuil :** Documentation complète comprenant : description du site et de la mise en situation Hydro-Limoilou, schéma de câblage breadboard (photo annotée ou schéma KiCad export PDF), description des choix techniques (capteurs assignés, justification des seuils d'alarme), README.md à jour. Qualité du français conforme aux exigences (PIEA art. 6.6) |
| **4** | Documentation soignée avec captures d'écran, schémas, troubleshooting (problèmes rencontrés et solutions) |
| **5** | Documentation exemplaire : structure claire et navigable, README.md aux normes, journal de bord du développement, leçons apprises |

---

## Critère 3.4 : Documentation des protocoles et topics (3%)

*Capacité 2 : Maîtriser les protocoles de communication IdO*
*Savoir-faire évalué (Plan de cours) : **Configurer un courtier MQTT (Mosquitto)***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Aucune documentation des protocoles |
| **1** | Topics listés sommairement, pas de payload exemplaire |
| **2** | Liste des topics présente mais payloads non documentés ou incohérents avec ce qui est publié |
| **3** | **Seuil :** Documentation complète du contrat MQTT du site : liste exhaustive des topics utilisés, exemples de payloads JSON pour chaque topic (telemetry + status + alarm + actuators), procédure de démo pas-à-pas, configuration Mosquitto (utilisateur, ACL, port, TLS) |
| **4** | Documentation enrichie : fréquences de publication par topic, niveaux de QoS justifiés, exemples de souscription (`mosquitto_sub` côté VM) |
| **5** | Documentation complète conforme à un standard professionnel : diagramme de séquence MQTT, conventions de nommage justifiées, recommandations de monitoring |

---

## Critère 3.5 : Site reste visible côté VM pendant toute la démo (3%)

*Capacité 2 : Maîtriser les protocoles de communication IdO*
*Savoir-faire évalué (Plan de cours) : **Surveiller et optimiser les performances réseau***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Site invisible côté VM pendant la démo |
| **1** | Site visible par intermittence ; nombreuses pertes de connexion non gérées |
| **2** | Site visible mais publications irrégulières ; reconnexions visibles dans le dashboard mais lentes |
| **3** | **Seuil :** Le site reste publié côté VM **pendant toute la durée de la démo** (incluant la séquence de perte/reprise volontaire du critère 3.1) ; topic `status` régulier ; reprise automatique observée et confirmée par le dashboard |
| **4** | Aucune interruption non planifiée pendant la démo ; status horodaté cohérent ; latence faible (< 2 s) constante |
| **5** | Stabilité parfaite ; métriques de qualité (RSSI/SNR ou signal LTE) constantes ; comportement reproductible en cas de relance |

---

## Critère 3.6 : QoS et fiabilité MQTT (3%)

*Capacité 2 : Maîtriser les protocoles de communication IdO*
*Savoir-faire évalué (Plan de cours) : **Configurer les paramètres de QoS selon les besoins***

| Niveau | Descripteur |
|:------:|-------------|
| **0** | Aucun paramètre QoS configuré ; messages perdus non détectés |
| **1** | QoS = 0 partout sans réflexion ; perte de messages d'alarme observée |
| **2** | QoS configuré mais incohérent (par ex. QoS 2 pour de la télémétrie haute fréquence) |
| **3** | **Seuil :** Choix de QoS justifiés et documentés : **QoS 0** pour la télémétrie (tolérance à la perte, débit privilégié), **QoS 1 ou 2** pour les alarmes (livraison garantie). Reconnexion automatique avec republication des messages persistants. Comportement observable et démontrable |
| **4** | Politique de QoS différenciée par topic, justification écrite dans la doc ; mécanisme de retransmission ou de file d'attente côté firmware |
| **5** | QoS optimisé selon usage et contraintes réseau ; mesures de performances (taux de livraison, latence) présentées ; recommandations de tuning documentées |

---

## Tableau récapitulatif CP3

| Critère | Capacité | Pondération | Note /5 | Points |
|---------|:--------:|:-----------:|:-------:|:------:|
| 3.1 Démo 3 scénarios | C2 | 7% | /5 | |
| 3.2 PCB finalisé (DRC + Gerbers) | C1 | 3% | /5 | |
| 3.3 Doc processus de conception | C1 | 1% | /5 | |
| 3.4 Doc protocoles et topics | C2 | 3% | /5 | |
| 3.5 Site visible côté VM pendant démo | C2 | 3% | /5 | |
| 3.6 QoS et fiabilité MQTT | C2 | 3% | /5 | |
| **TOTAL CP3** | | **20%** | | **/20** |

---

## Calcul des points

Pour chaque critère :

$$\text{Points} = \frac{\text{Note sur 5}}{5} \times \text{Pondération du critère}$$

---

## Livrables attendus à la fin de la semaine 15

- [ ] Démo en direct des 3 scénarios (nominal / alarme / perte-reprise)
- [ ] PCB routé 2 couches dans KiCad, DRC sans erreurs
- [ ] Gerbers + BOM générés et commités dans le dépôt
- [ ] Documentation complète du processus de conception (Markdown dans le dépôt)
- [ ] Documentation complète des topics et protocoles MQTT
- [ ] Vidéo de démo (≤ 5 min) présentant les 3 scénarios
- [ ] Site reste visible côté serveur central VM pendant toute la démo
- [ ] Justification écrite des choix de QoS

---

**Fin du document — Grille CP3**
