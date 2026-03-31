---
theme: seriph
background: https://images.unsplash.com/photo-1518770660439-4636190af475?w=1920
title: 243-4J5-LI - Objets connectés - Semaine 9
info: |
  ## Objets connectés
  Semaine 9 - Soudure PCB et introduction aux LLM sur ESP32

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

Semaine 9 - Soudure PCB et introduction aux LLM

<div class="pt-12">
  <span class="px-2 py-1 rounded cursor-pointer" hover="bg-white bg-opacity-10">
    Francis Poisson - Cégep Limoilou - H26
  </span>
</div>

---
layout: section
---

# Aujourd'hui
## Deux activités

---

# Plan de la séance

<div class="grid grid-cols-2 gap-8 mt-8">

<div class="p-4 bg-orange-500 bg-opacity-20 rounded-lg">

### Partie 1 — Soudure PCB (1h30)

<v-clicks>

- Vos PCB sont arrivés!
- Soudure des composants THT
- Vérification et test de continuité

</v-clicks>

</div>

<div class="p-4 bg-blue-500 bg-opacity-20 rounded-lg">

### Partie 2 — LLM sur T-Beam Supreme (1h30)

<v-clicks>

- Créer un dépôt Git (GitHub Desktop)
- Appel HTTP vers un LLM depuis l'ESP32
- Affichage de la réponse sur l'écran OLED
- Scénario créatif avec potentiomètre
- Compte Groq (API LLM gratuite)

</v-clicks>

</div>

</div>

---
layout: section
---

# Partie 1
## Soudure du PCB

---

# Vos PCB sont là

### Rappel de la conception (semaine 7)

<v-clicks>

- Schéma et routage dans KiCad
- Fabrication envoyée chez JLCPCB
- Aujourd'hui : on assemble!

</v-clicks>

<v-click>

<div class="mt-4 p-2 bg-orange-500 bg-opacity-20 rounded-lg text-center text-sm">

**Objectif** : PCB fonctionnel à la fin de la période.

</div>

</v-click>

---

# Ordre de soudure

### Du plus bas au plus haut

<v-clicks>

1. **Résistances** — identifier les valeurs (code couleur ou multimètre)
2. **Condensateurs céramiques** — pas de polarité
3. **Condensateurs électrolytiques** — bande = négatif
4. **Connecteurs** — headers, borniers
5. **Composants actifs** — CI, régulateurs (attention à l'orientation)

</v-clicks>

<v-click>

<div class="mt-4 p-2 bg-red-500 bg-opacity-20 rounded-lg text-center text-sm">

**Température du fer** : 300-350 °C — fer sur pastille ET patte, étain sur la jonction.

</div>

</v-click>

---

# Vérification

### Avant de passer à la partie 2

<v-clicks>

- Inspection visuelle de chaque soudure (brillante, forme de cône)
- Pas de ponts entre les pistes
- Test de continuité au multimètre
- Brancher et vérifier le fonctionnement de base

</v-clicks>

---
layout: section
---

# Partie 2
## Introduction aux LLM sur ESP32

---

# C'est quoi un LLM?

### Grand modèle de langage

<v-clicks>

- Modèle d'IA entraîné sur du texte (GPT, Claude, Llama, etc.)
- Accessible via une **API HTTP** : on envoie un prompt, on reçoit du texte
- Fonctionne partout où on peut faire un POST HTTPS — y compris un ESP32

</v-clicks>

<v-click>

```
ESP32 → POST HTTPS → API LLM → Réponse texte → Écran OLED
```

</v-click>

<v-click>

<div class="mt-4 p-2 bg-blue-500 bg-opacity-20 rounded-lg text-center text-sm">

**Aujourd'hui** : potentiomètre → LLM → réponse sur l'écran OLED du T-Beam Supreme.

</div>

</v-click>

---

# API compatible OpenAI

### Format standard

<div class="grid grid-cols-2 gap-4">

<div>

<v-click>

### Requête (POST)

```json
{
  "model": "nom-du-modele",
  "messages": [
    {
      "role": "system",
      "content": "Tu es un ..."
    },
    {
      "role": "user",
      "content": "Valeur: 2048"
    }
  ],
  "max_tokens": 60
}
```

</v-click>

</div>

<div>

<v-click>

### Réponse

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Lâche pas!"
      }
    }
  ]
}
```

</v-click>

</div>

</div>

<v-click>

<div class="mt-4 p-2 bg-green-500 bg-opacity-20 rounded-lg text-center text-sm">

Groq, OpenAI, Anthropic, Ollama — tous utilisent ce même format.

</div>

</v-click>

---

# Groq — API gratuite

### Créer un compte

<v-clicks>

1. Aller sur **console.groq.com**
2. Créer un compte (Google ou GitHub)
3. Section **API Keys** — créer une clé
4. Copier la clé dans votre fichier `config.h`

</v-clicks>

<v-click>

### Modèle recommandé

```
meta-llama/llama-4-scout-17b-16e-instruct
```

Rapide, capable, gratuit pour l'usage éducatif.

</v-click>

---

# Le défi créatif

### Potentiomètre → LLM → Réponse contextuelle

<v-click>

La valeur du potentiomètre (0 à 4095) influence le **prompt utilisateur** envoyé au LLM.

</v-click>

<v-click>

| Scénario | Pot à 0 | Pot à 4095 |
|----------|---------|------------|
| Entraîneur sportif | Encouragement maximal | Félicitations |
| Météo émotionnelle | Tempête, motiver | Soleil, tout va bien |
| Chef cuisinier | Plat raté, conseils | Chef étoilé, compliments |
| Professeur | Étudiant perdu, simplifier | Expert, donner des défis |

</v-click>

<v-click>

<div class="mt-4 p-2 bg-purple-500 bg-opacity-20 rounded-lg text-center text-sm">

**Contrainte** : la réponse doit tenir sur l'écran OLED! Soyez créatifs!

</div>

</v-click>

---

# Structure du projet

### Dépôt Git propre

```
labo4-llm-esp32/
├── .gitignore            # config.h ignoré!
├── config.example.h      # Template sans secrets
├── config.h              # Vos vrais identifiants (jamais commité)
└── labo4-llm-esp32.ino   # Code principal
```

<v-click>

<div class="mt-4 p-2 bg-red-500 bg-opacity-20 rounded-lg text-center text-sm">

**Règle absolue** : `config.h` contient vos clés API — il ne doit **jamais** être commité.

</div>

</v-click>

---

# À vous de jouer

### Ce que vous devez faire

<v-clicks>

1. Souder le shield PCB et le tester avec le A7670E
2. Créer le dépôt Git avec GitHub Desktop
3. Copier le code fourni et les fichiers config
4. Personnaliser votre scénario créatif (prompt système)
5. Tester avec le endpoint du cours sur le T-Beam Supreme
6. Créer un compte Groq et tester avec votre propre clé
7. Commit propre dans GitHub Desktop (sans `config.h`!)

</v-clicks>

---
layout: center
class: text-center
---

# Questions?

<div class="text-xl mt-8">
On soude, puis on code!
</div>

---
layout: end
---

# Merci!

243-4J5-LI - Objets connectés

Semaine 9
