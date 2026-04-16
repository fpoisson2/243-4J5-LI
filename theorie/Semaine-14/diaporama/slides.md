---
theme: seriph
background: https://images.unsplash.com/photo-1518770660439-4636190af475?w=1920
title: 243-4J5-LI - Objets connectés - Semaine 14
info: |
  ## Objets connectés
  Semaine 14 - Projet final Hydro-Limoilou (CP2)

  Cégep Limoilou - Session H26
class: text-center
highlighter: shiki
drawings:
  persist: false
transition: slide-left
mdc: true
download: true
---

# Objets connectés
## 243-4J5-LI

Semaine 14 — Projet final Hydro-Limoilou (CP2)

<div class="pt-12">
  <span class="px-2 py-1 rounded cursor-pointer" hover="bg-white bg-opacity-10">
    Francis Poisson - Cégep Limoilou - H26
  </span>
</div>

---
layout: section
---

# Brève intro
## (15-20 min) — puis labo libre

---

# Objectifs CP2 (10%)

| Critère | Capacité | Pondération |
|---------|:--------:|:-----------:|
| **2.1** Tous les capteurs publient sur les bons topics | C2 | 3% |
| **2.2** Alarmes fonctionnelles | C1 | 2% |
| **2.3** Interface tactile (3 pages) | C1 | 1% |
| **2.4** Visibilité serveur central | C2 | 3% |
| **2.5** Schéma KiCad complet (ERC OK) | C1 | 1% |
| **TOTAL CP2** | | **10%** |

---

# Sur quoi travailler aujourd'hui

<v-clicks>

1. **Compléter la publication MQTT** pour tous les capteurs assignés (topics conformes au contrat)
2. **Implémenter au moins une alarme** cohérente avec votre mise en situation et la publier sur `alarm/{type}`
3. **Étendre l'interface tactile** sur 3 pages : télémétrie, alarmes, état du lien
4. **Configurer Mosquitto** (auth + ACL) et **activer le tunnel Cloudflare**
5. **Transmettre les credentials** du compte `central` à l'enseignant
6. **Compléter le schéma KiCad** (ERC sans erreurs)

</v-clicks>

---

# Rappels rapides

<div class="grid grid-cols-2 gap-4 text-sm">

<div class="p-3 bg-blue-500 bg-opacity-20 rounded-lg">

### Topics à publier

- `hydro-limoilou/poste-XX/telemetry/{capteur}`
- `hydro-limoilou/poste-XX/status` (toutes les 30 s)
- `hydro-limoilou/poste-XX/alarm/{type}`
- `hydro-limoilou/poste-XX/actuators/led_N` (descendant)

</div>

<div class="p-3 bg-orange-500 bg-opacity-20 rounded-lg">

### Trois pages tactiles

- **Télémétrie** : valeurs courantes des capteurs
- **Alarmes** : liste + ack
- **État lien** : RSSI/signal + uptime

</div>

</div>

---

# Validation côté serveur central

L'enseignant valide la visibilité du site avec :

```bash
mosquitto_sub \
  -h prenom-nom.example.com \
  -p 443 \
  -u central -P 'mot-de-passe-fort' \
  -t 'hydro-limoilou/poste-XX/#' -v
```

<v-click>

<div class="mt-3 p-3 bg-green-500 bg-opacity-20 rounded-lg text-sm">

Si la commande retourne les topics en continu, le critère 2.4 est atteint.

</div>

</v-click>

---

# Documents de référence

- `evaluations/Evaluation-04/contrat-serveur-central.md` — topics, payloads, Mosquitto
- `evaluations/Evaluation-04/grille-checkpoint-2.md` — grille détaillée CP2

---
layout: section
---

# Au travail
## Labo libre — l'enseignant circule

---

# Pour la sem. 15 (CP3 — 20%)

<v-clicks>

- Démo en direct des **3 scénarios** (nominal, alarme, perte/reprise)
- **PCB routé** 2 couches, DRC sans erreurs, Gerbers + BOM
- Documentation complète (processus + protocoles)
- Vidéo de démo (≤ 5 min)
- Site reste visible côté VM pendant toute la démo
- Justification des choix de QoS

</v-clicks>

<v-click>

<div class="mt-3 p-3 bg-orange-500 bg-opacity-20 rounded-lg text-sm">

CP3 = le plus lourd. Préparer le routage PCB en parallèle dès aujourd'hui.

</div>

</v-click>
