---
theme: seriph
background: https://images.unsplash.com/photo-1518770660439-4636190af475?w=1920
title: 243-4J5-LI - Objets connectés - Semaine 12
info: |
  ## Objets connectés
  Semaine 12 - MQTT, finalisation et remise du TP

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

Semaine 12 - MQTT, finalisation et remise du TP

<div class="pt-12">
  <span class="px-2 py-1 rounded cursor-pointer" hover="bg-white bg-opacity-10">
    Francis Poisson - Cégep Limoilou - H26
  </span>
</div>

---
layout: section
---

# Rappel du TP
## Où en sommes-nous?

---

# État des lieux

### Ce qui devrait être fait

<v-click>

### Semaine 11 (fait)

- Émetteur : potentiomètre → LoRa (RadioLib)
- Récepteur : réception LoRa → WiFi → appel LLM
- DEL contrôlée par la réponse du LLM
- RSSI/SNR affichés dans le moniteur série

</v-click>

<v-click>

### Aujourd'hui (semaine 12)

- Ajouter la **publication MQTT** sur le récepteur
- **Gestion des erreurs** (retry LLM, reconnexion WiFi)
- **Documentation** (README.md)
- **Remise du TP**

</v-click>

---
layout: section
---

# Partie 1
## Ajouter MQTT au récepteur

---

# Librairie PubSubClient

### Client MQTT pour Arduino

<v-click>

### Installation

1. IDE Arduino → Gestionnaire de bibliothèques
2. Chercher **PubSubClient**
3. Installer la dernière version

</v-click>

<v-click>

### Connexion au broker

```cpp
#include <PubSubClient.h>

WiFiClient espClient;
PubSubClient mqtt(espClient);

void setupMQTT() {
  mqtt.setServer(MQTT_BROKER, 1883);

  while (!mqtt.connected()) {
    Serial.print("Connexion MQTT...");
    if (mqtt.connect("lora-receiver")) {
      Serial.println(" OK!");
    } else {
      Serial.println(" échec, retry dans 5s");
      delay(5000);
    }
  }
}
```

</v-click>

---

# Publier les données et l'analyse

### Envoyer sur le broker MQTT

```cpp
void processMessage(String received) {
  float rssi = radio.getRSSI();
  float snr = radio.getSNR();

  // Publier les données brutes
  JsonDocument raw;
  raw["pot"] = received.toInt();
  raw["rssi"] = rssi;
  raw["snr"] = snr;
  String rawJson;
  serializeJson(raw, rawJson);
  mqtt.publish("lora/donnees", rawJson.c_str());

  // Appeler le LLM
  String llmResponse = callLLM(received, rssi, snr);
  // ... parser la réponse

  // Publier l'analyse
  mqtt.publish("lora/analyses", llmResponse.c_str());

  // Contrôler la DEL
  String action = doc["action"] | "none";
  if (action == "on") {
    digitalWrite(LED_PIN, HIGH);
    mqtt.publish("lora/actions", "led_on");
  } else if (action == "off") {
    digitalWrite(LED_PIN, LOW);
    mqtt.publish("lora/actions", "led_off");
  }
}
```

---

# Topics MQTT

### Structure de publication

<v-click>

| Topic | Contenu | Fréquence |
|-------|---------|-----------|
| `lora/donnees` | Valeur du pot + RSSI + SNR | Chaque réception |
| `lora/analyses` | Réponse JSON du LLM | Chaque analyse |
| `lora/actions` | Action exécutée (led_on/off) | Quand action |
| `lora/erreurs` | Messages d'erreur | Si problème |

</v-click>

<v-click>

### Vérifier avec mosquitto_sub

```bash
# Sur le PC ou le Raspberry Pi
mosquitto_sub -h adresse.du.broker -t "lora/#" -v
```

</v-click>

<v-click>

<div class="mt-2 p-2 bg-green-500 bg-opacity-20 rounded-lg text-center text-sm">

Si les messages apparaissent dans `mosquitto_sub` : le pipeline **bout en bout** fonctionne!

</div>

</v-click>

---
layout: section
---

# Partie 2
## Robustesse et gestion des erreurs

---

# Gestion des erreurs

### Rendre le système fiable

<v-click>

```cpp
void loop() {
  // Reconnecter WiFi si nécessaire
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi perdu, reconnexion...");
    setupWiFi();
  }

  // Reconnecter MQTT si nécessaire
  if (!mqtt.connected()) {
    setupMQTT();
  }
  mqtt.loop();  // Maintenir la connexion MQTT

  // Recevoir LoRa
  String received;
  int state = radio.receive(received);

  if (state == RADIOLIB_ERR_NONE) {
    processMessage(received);
  }
}
```

</v-click>

---

# Retry sur l'appel LLM

### L'API peut échouer temporairement

```cpp
String callLLMWithRetry(String data, float rssi, float snr) {
  for (int attempt = 0; attempt < 3; attempt++) {
    String response = callLLM(data, rssi, snr);

    if (response.length() > 0) {
      return response;  // Succès
    }

    Serial.println("LLM tentative " + String(attempt + 1) +
                   "/3 échouée");
    delay(1000 * (attempt + 1));  // 1s, 2s, 3s
  }

  // Fallback : réponse par défaut
  Serial.println("LLM indisponible, fallback local");
  return "{\"status\":\"normal\",\"action\":\"none\"}";
}
```

<v-click>

<div class="mt-4 p-2 bg-orange-500 bg-opacity-20 rounded-lg text-center text-sm">

Le **fallback** garantit que le système continue de fonctionner même sans le LLM.

</div>

</v-click>

---
layout: section
---

# Partie 3
## Documentation et remise

---

# Critères d'évaluation

### Ce qui sera noté

<div class="grid grid-cols-2 gap-4 text-sm">

<div>

<v-click>

### Configuration API (25%)

- Clé API sécurisée (config.h)
- Appels API fonctionnels
- Gestion des erreurs
- Aucune clé dans le code!

</v-click>

<v-click>

### Prompt Engineering (25%)

- Prompt système clair et efficace
- Rôle d'analyste IoT défini
- Format de réponse JSON
- Résultats cohérents

</v-click>

</div>

<div>

<v-click>

### Pipeline (30%)

- Émetteur LoRa fonctionnel
- Récepteur avec analyse LLM
- Publication MQTT des résultats
- DEL contrôlée par le LLM
- Fallback si LLM indisponible

</v-click>

<v-click>

### Documentation (20%)

- README complet
- Architecture documentée
- Code lisible et structuré
- Qualité du français

</v-click>

</div>

</div>

---

# Pénalités de sécurité

### Le barème est strict

<v-click>

| Infraction | Pénalité |
|-----------|----------|
| Clé API dans le code source | **-20 points** |
| Clé API dans l'historique git | **-15 points** |
| Fichier config.h commité | **-10 points** |
| Pas de .gitignore | **-5 points** |

</v-click>

<v-click>

### Comment vérifier

```bash
# Chercher des clés dans l'historique git
git log --all -p | grep -i "api_key\|gsk_\|secret"

# Vérifier que config.h est ignoré
git status  # config.h ne doit PAS apparaître
```

</v-click>

---

# Checklist de remise

### Vérifications finales

<div class="grid grid-cols-2 gap-4 text-sm">

<div>

<v-click>

### Fonctionnel

- [ ] Émetteur envoie le potentiomètre via LoRa
- [ ] Récepteur reçoit et affiche RSSI/SNR
- [ ] Appel LLM fonctionne
- [ ] DEL réagit à l'analyse
- [ ] Données publiées sur MQTT
- [ ] Fallback si LLM indisponible

</v-click>

</div>

<div>

<v-click>

### Sécurité et documentation

- [ ] config.h ignoré par git
- [ ] config.example.h commité
- [ ] Aucun secret dans l'historique
- [ ] README.md complet
- [ ] Code commenté si nécessaire

</v-click>

</div>

</div>

---

# Plan de la séance

### 3 heures pour finaliser

<v-clicks>

1. **Heure 1** : Ajouter MQTT au récepteur, tester avec `mosquitto_sub`
2. **Heure 2** : Gestion des erreurs, fallback, tests complets
3. **Heure 3** : Documentation (README.md), vérification sécurité, remise

</v-clicks>

<v-click>

<div class="mt-4 p-2 bg-red-500 bg-opacity-20 rounded-lg text-center text-sm">

Commit final et push sur GitHub **avant la fin de la séance**.

</div>

</v-click>

---
layout: center
class: text-center
---

# Questions?

<div class="text-xl mt-8">
Dernière ligne droite — finalisez et remettez!
</div>

---
layout: end
---

# Merci!

243-4J5-LI - Objets connectés

Semaine 12
