---
theme: seriph
background: https://images.unsplash.com/photo-1518770660439-4636190af475?w=1920
title: 243-4J5-LI - Objets connectés - Semaine 15
info: |
  ## Objets connectés
  Semaine 15 - Projet final Hydro-Limoilou (CP3)

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

Semaine 15 — Projet final Hydro-Limoilou (CP3)

<div class="pt-12">
  <span class="px-2 py-1 rounded cursor-pointer" hover="bg-white bg-opacity-10">
    Francis Poisson - Cégep Limoilou - H26
  </span>
</div>

---
layout: section
---

# Brève intro
## (15-20 min) — puis labo + démos individuelles

---

# Objectifs CP3 (20%)

| Critère | Capacité | Pondération |
|---------|:--------:|:-----------:|
| **3.1** Démo 3 scénarios | C2 | 7% |
| **3.2** PCB finalisé (DRC + Gerbers + BOM) | C1 | 3% |
| **3.3** Documentation processus | C1 | 1% |
| **3.4** Documentation protocoles | C2 | 3% |
| **3.5** Site visible côté VM pendant démo | C2 | 3% |
| **3.6** QoS et fiabilité MQTT | C2 | 3% |
| **TOTAL CP3** | | **20%** |

---

# Les 3 scénarios à démontrer

<v-clicks>

1. **Nominal** — publication continue + dashboard VM voit le site
2. **Alarme** — déclenchement physique → topic alarm publié → affichage tactile + dashboard VM
3. **Perte/reprise de lien** — coupure WiFi/LTE puis reconnexion + republication automatique

</v-clicks>

---

# Re-vérification CP1 + CP2

<div class="p-3 bg-blue-500 bg-opacity-20 rounded-lg">

À la démo, l'enseignant **revérifie le bon fonctionnement** des éléments validés aux CP1 et CP2 (câblage, publications, alarmes, interface tactile, visibilité VM, schéma KiCad).

**Les notes des CP1 et CP2 ne sont PAS révisées.**

CP1 + CP2 sont des **prérequis fonctionnels** au CP3 — si quelque chose ne fonctionne plus, certains scénarios deviennent infaisables et la note CP3 en pâtit.

</div>

---

# Sur quoi travailler aujourd'hui

<v-clicks>

1. **Préparer la démo** : script écrit, système prêt, dashboard VM ouvert
2. **Finaliser le routage PCB** dans KiCad (DRC sans erreurs)
3. **Générer Gerbers + BOM** et commiter dans le dépôt
4. **Compléter la documentation** (README, contrat topics, justification QoS)
5. **Tourner la vidéo de démo** (≤ 5 min, structure : intro / architecture / 3 scénarios / conclusion)

</v-clicks>

---

# Livrables à remettre

<v-clicks>

- [ ] Code firmware (Arduino/ESP32) dans le dépôt Git
- [ ] Code interface tactile (Python) dans le dépôt Git
- [ ] Schéma KiCad complet
- [ ] PCB layout (DRC OK)
- [ ] Gerbers + BOM
- [ ] README.md complet
- [ ] Documentation des topics et protocoles
- [ ] Vidéo de démo (≤ 5 min)

</v-clicks>

---

# Déroulement des démos individuelles

<v-clicks>

1. Présentation rapide du site et de la mise en situation (3 min)
2. Démonstration des **3 scénarios** (10 min)
3. Remise des livrables (lien Git)
4. Rétroaction immédiate (2 min)

</v-clicks>

<v-click>

<div class="mt-3 p-3 bg-orange-500 bg-opacity-20 rounded-lg text-sm">

≈ 15 min par étudiant·e — voir l'horaire de passage affiché.

</div>

</v-click>

---

# Récapitulatif du projet final

| Checkpoint | Pondération | Cumul |
|------------|:-----------:|:-----:|
| CP1 (sem. 13) | 5% | 5% |
| CP2 (sem. 14) | 10% | 15% |
| **CP3 (sem. 15)** | **20%** | **35%** |

---
layout: section
---

# Bonne fin de session
