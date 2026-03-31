# Laboratoire 04 - Soudure PCB et introduction aux LLM sur ESP32

## Objectifs

- Souder les composants sur le shield PCB du projet de mi-session
- Tester le shield avec le LilyGO A7670E et le firmware existant
- Effectuer un appel HTTP a une API LLM depuis le T-Beam Supreme
- Afficher la reponse du LLM sur l'ecran OLED integre
- Concevoir un prompt creatif lie a la valeur du potentiometre

## Materiel requis

### Partie 1 — Soudure
- Shield PCB du projet de mi-session (recu cette semaine)
- Composants selon votre assignation (LEDs, boutons, potentiometres, MPU6050)
- Resistances 330 ohms pour les LEDs
- Headers male/femelle pour la connexion au LilyGO
- Fer a souder, etain, flux, tresse a dessouder
- LilyGO T-SIM A7670E
- Multimetre

### Partie 2 — LLM
- LilyGO T-Beam Supreme (ESP32-S3 avec ecran OLED integre)
- Potentiometre 10 kohms
- Fils de connexion
- Cable USB-C
- Ordinateur avec Arduino IDE et GitHub Desktop

---

## Partie 1 : Soudure et test du shield PCB (1h30)

Vous avez concu ce shield en semaine 7 avec KiCad et demontre son fonctionnement sur breadboard. Aujourd'hui, on passe au PCB!

### Lien avec l'evaluation du projet de mi-session

Le shield PCB represente **30%** de la note du projet de mi-session. Le prototype fonctionnel (critere 1.4) vaut **5%**. De plus, le programme embarque (30%) et l'interface Raspberry Pi (20%) dependent d'un shield fonctionnel — un PCB mal soude affecte 80% du projet.

### 1.1 Preparation du poste

1. Verifier que le fer a souder est propre et etame
2. Regler la temperature entre 300 et 350 degres C
3. Sortir votre BOM (liste de materiaux) du projet KiCad
4. Organiser vos composants selon votre assignation personnelle

### 1.2 Ordre de soudure recommande

Souder les composants du plus bas au plus haut :

1. **Resistances 330 ohms** pour les LEDs
2. **Condensateurs** (ceramiques d'abord, puis electrolytiques si applicable)
3. **Headers** pour la connexion au LilyGO A7670E
4. **Boutons poussoirs**
5. **LEDs** (attention a la polarite : patte longue = anode +)
6. **Potentiometres**
7. **MPU6050** (attention a l'orientation, verifier le marquage)

### 1.3 Technique de soudure THT

1. Inserer le composant, plier legerement les pattes pour le maintenir
2. Retourner le PCB
3. Appliquer le fer sur la pastille ET la patte simultanement (2-3 secondes)
4. Ajouter l'etain sur la jonction (pas sur le fer)
5. Retirer l'etain, puis le fer
6. Verifier : la soudure doit etre brillante et en forme de cone

### 1.4 Verification des soudures

- Inspecter visuellement chaque soudure
- Verifier l'absence de ponts de soudure entre les pistes
- Tester la continuite avec le multimetre

### 1.5 Test avec le LilyGO A7670E

Branchez le shield sur votre LilyGO A7670E et testez avec le firmware du projet de mi-session :

1. Enficher le shield sur les headers du LilyGO
2. Brancher le cable USB-C et ouvrir le moniteur serie (115200 baud)
3. Televersez votre firmware de mi-session si ce n'est pas deja fait
4. Verifier que chaque composant fonctionne :

| Composant | Verification |
|-----------|-------------|
| LEDs | S'allument via les commandes MQTT |
| Boutons | Changement d'etat visible dans le moniteur serie |
| Potentiometres | Valeurs 0-4095 qui varient dans le moniteur serie |
| MPU6050 | Donnees d'acceleration/gyroscope visibles (I2C) |

> Si un composant ne fonctionne pas, verifiez les soudures correspondantes avec le multimetre avant de chercher un probleme logiciel.

---

## Partie 2 : Introduction aux LLM sur le T-Beam Supreme (1h30)

### Contexte

Les grands modeles de langage (LLM) sont accessibles via des API HTTP. Depuis un ESP32, on peut envoyer une requete HTTP POST contenant un prompt et recevoir une reponse textuelle. L'objectif est de connecter un potentiometre au T-Beam Supreme et d'afficher la reponse du LLM sur l'ecran OLED integre.

### 2.1 Creer le depot Git

1. Ouvrez **GitHub Desktop**
2. **File > New Repository...**
3. Nom : `labo4-llm-esp32`
4. Choisissez un emplacement local sur votre ordinateur
5. Cochez **Initialize this repository with a README**
6. Dans le champ **Git Ignore**, selectionnez `None` (on va le creer manuellement)
7. Cliquez **Create Repository**

### 2.2 Creer le .gitignore

Dans le dossier du depot, creez un fichier `.gitignore` avec un editeur de texte :

```
# Fichiers sensibles
config.h
```

> **Important** : le fichier `config.h` contient vos cles API et mots de passe. Il ne doit **jamais** etre commite.

### 2.3 Structure du projet

Creez les fichiers suivants dans le dossier du depot :

```
labo4-llm-esp32/
├── .gitignore
├── config.example.h      # Template sans secrets
├── config.h               # Vos vrais identifiants (ignore par git)
└── labo4-llm-esp32.ino    # Code principal
```

> Pour ouvrir le projet dans Arduino IDE, ouvrez le fichier `.ino`. Arduino exige que le fichier `.ino` porte le meme nom que son dossier parent.

### 2.4 Fichier config.example.h

Creez ce fichier — c'est le template sans secrets qui sera commite :

```cpp
/*
 * config.example.h - Template de configuration
 * Copier vers config.h et remplir avec vos valeurs.
 */

#pragma once

// =============================================
// CONFIGURATION WIFI
// =============================================

#define WIFI_SECURITY_WPA2_PERSONAL
const char* WIFI_SSID     = "votre-ssid";
const char* WIFI_PASSWORD = "votre-mot-de-passe";

// =============================================
// CONFIGURATION LLM
// =============================================

// --- Étape 1 : endpoint du cours ---
const char* OPENWEBUI_URL = "https://chat.ve2fpd.com/api/chat/completions";
const char* API_KEY        = "cle-fournie-en-classe";
const char* MODEL_NAME     = "assistant-iot-v2";

// --- Étape 2 : votre propre compte Groq ---
// const char* OPENWEBUI_URL = "https://api.groq.com/openai/v1/chat/completions";
// const char* API_KEY        = "votre-cle-api-groq";
// const char* MODEL_NAME     = "meta-llama/llama-4-scout-17b-16e-instruct";

// =============================================
// SYSTEM PROMPT - À PERSONNALISER!
// =============================================

const char* SYSTEM_PROMPT =
  "Tu es un entraineur de CrossFit intense et motivant. "
  "Le potentiometre represente le niveau d'effort de l'athlete "
  "de 0 (echauffement tranquille) a 4095 (effort maximal absolu). "
  "REGLE ABSOLUE: ta reponse doit faire MAXIMUM 50 caracteres. "
  "Une seule phrase ultra courte. Pas de ponctuation superflue.";
```

### 2.5 Fichier config.h

Copiez `config.example.h` vers `config.h` et remplissez vos vraies valeurs :

- Votre SSID et mot de passe WiFi
- La cle API fournie par l'enseignant (pour le endpoint du cours)

### 2.6 Installer les bibliotheques

Dans Arduino IDE, allez dans **Outils > Gerer les bibliotheques** et installez :

- **ArduinoJson** par Benoit Blanchon
- **Adafruit SSD1306** par Adafruit (acceptez les dependances)

### 2.7 Code principal — labo4-llm-esp32.ino

Copiez le code suivant dans votre fichier `.ino`.

```cpp
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include "config.h"

// ====== ECRAN OLED (integre au T-Beam Supreme) ======
#define OLED_SDA  17
#define OLED_SCL  18
#define OLED_RST  -1
#define OLED_ADDR 0x3C
#define SCREEN_W  128
#define SCREEN_H  64

Adafruit_SSD1306 display(SCREEN_W, SCREEN_H, &Wire, OLED_RST);

// ====== BROCHE DU POTENTIOMETRE ======
// >>> MODIFIEZ cette valeur selon votre branchement <<<
const int POT_PIN = 36;

// ====== INTERVALLE ENTRE LES APPELS ======
const unsigned long INTERVALLE_APPEL = 5000; // 5 secondes

// ====== VARIABLES GLOBALES ======
WiFiClientSecure wifiClient;
unsigned long dernierAppel = 0;

// ------------------------------------------------------------
// afficherOLED(ligne1, ligne2) — Affiche du texte sur l'OLED
// ------------------------------------------------------------
void afficherOLED(String ligne1, String ligne2) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  // Ligne 1 en haut (petite)
  display.setCursor(0, 0);
  display.println(ligne1);

  // Ligne 2 au centre (plus grande)
  display.setTextSize(1);
  display.setCursor(0, 20);
  display.println(ligne2);

  display.display();
}

// ------------------------------------------------------------
// connexionWiFi() — Se connecte au reseau WiFi
// ------------------------------------------------------------
void connexionWiFi() {
  Serial.print("Connexion WiFi a ");
  Serial.println(WIFI_SSID);
  afficherOLED("WiFi...", WIFI_SSID);

  WiFi.disconnect(true);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("Connecte! IP: ");
  Serial.println(WiFi.localIP());
  afficherOLED("WiFi OK", WiFi.localIP().toString());
}

// ------------------------------------------------------------
// appelLLM(valeurPot) — Envoie la valeur du pot au LLM
//                        et retourne la reponse textuelle
// ------------------------------------------------------------
String appelLLM(int valeurPot) {
  // Desactiver la verification des certificats SSL (demo seulement)
  wifiClient.setInsecure();

  HTTPClient http;
  http.begin(wifiClient, OPENWEBUI_URL);

  // Headers HTTP : JSON + token d'authentification Bearer
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " + String(API_KEY));

  // Corps de la requete — format compatible OpenAI
  // "system" = le contexte (votre scenario)
  // "user" = la valeur du potentiometre
  JsonDocument doc;
  doc["model"] = MODEL_NAME;
  doc["max_tokens"] = 60;
  doc["temperature"] = 0.8;

  JsonArray messages = doc["messages"].to<JsonArray>();

  JsonObject sysMsg = messages.add<JsonObject>();
  sysMsg["role"] = "system";
  sysMsg["content"] = SYSTEM_PROMPT;

  JsonObject userMsg = messages.add<JsonObject>();
  userMsg["role"] = "user";
  userMsg["content"] = "Valeur du potentiometre : " + String(valeurPot);

  String body;
  serializeJson(doc, body);

  Serial.println("[LLM] Envoi...");
  afficherOLED("Pot: " + String(valeurPot), "Envoi au LLM...");

  // Envoi du POST
  int httpCode = http.POST(body);

  String resultat = "";

  if (httpCode == 200) {
    String reponse = http.getString();
    JsonDocument repDoc;
    DeserializationError err = deserializeJson(repDoc, reponse);

    if (!err) {
      // La reponse se trouve dans choices[0].message.content
      const char* texte = repDoc["choices"][0]["message"]["content"];
      if (texte) {
        resultat = String(texte);
      } else {
        resultat = "[Pas de contenu]";
      }
    } else {
      resultat = "[Erreur JSON]";
    }
  } else {
    resultat = "[HTTP " + String(httpCode) + "]";
    Serial.println(http.getString());
  }

  http.end();
  return resultat;
}

// ------------------------------------------------------------
// setup()
// ------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println();
  Serial.println("=== Labo 4 - LLM sur T-Beam Supreme ===");

  // Initialiser l'OLED
  Wire.begin(OLED_SDA, OLED_SCL);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("[OLED] Echec d'initialisation!");
  }
  afficherOLED("Labo 4", "Demarrage...");

  // Potentiometre
  pinMode(POT_PIN, INPUT);

  // WiFi
  connexionWiFi();
  delay(1000);

  afficherOLED("Pret!", "Tournez le pot...");
  Serial.println("=== Pret! Tournez le potentiometre ===");
}

// ------------------------------------------------------------
// loop()
// ------------------------------------------------------------
void loop() {
  // Reconnexion WiFi si necessaire
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Reconnexion...");
    connexionWiFi();
  }

  // Lire le potentiometre (0 a 4095)
  int valeurPot = analogRead(POT_PIN);

  // Appeler le LLM a intervalle regulier
  unsigned long maintenant = millis();
  if (maintenant - dernierAppel >= INTERVALLE_APPEL) {
    dernierAppel = maintenant;

    String reponse = appelLLM(valeurPot);

    // Afficher sur le moniteur serie
    Serial.print("[LLM] Pot=");
    Serial.print(valeurPot);
    Serial.print(" -> ");
    Serial.println(reponse);

    // Afficher sur l'OLED
    afficherOLED("Pot: " + String(valeurPot), reponse);
  }

  delay(100);
}
```

### 2.8 Ce que vous devez modifier

Avant de televerser, adaptez ces trois elements dans le code et dans `config.h` :

1. **`POT_PIN`** (dans le `.ino`) : La broche analogique ou vous avez branche votre potentiometre sur le T-Beam Supreme.

2. **`SYSTEM_PROMPT`** (dans `config.h`) : Inventez votre propre mise en situation! L'exemple est un entraineur de CrossFit — remplacez-le par votre idee. Quelques exemples :

| Scenario | Pot a 0 | Pot a 4095 |
|----------|---------|------------|
| Entraineur sportif | Encouragement maximal | Felicitations |
| Meteo emotionnelle | Tempete, il faut motiver | Soleil, tout va bien |
| Chef cuisinier | Plat rate, conseils | Chef etoile, compliments |
| Professeur | Etudiant perdu, simplifier | Expert, donner des defis |

3. **Longueur de la reponse** : L'ecran OLED est petit! Pensez a contraindre le LLM dans votre prompt pour que sa reponse tienne a l'ecran.

### 2.9 Test avec le endpoint du cours

L'enseignant vous fournira la cle API pour le endpoint du cours (`chat.ve2fpd.com`) avec le modele `assistant-iot-v2`.

1. Dans Arduino IDE, selectionnez la carte **LilyGo T-Beam Supreme** (ou ESP32S3 Dev Module)
2. Televersez le code
3. Ouvrez le moniteur serie (115200 baud)
4. Tournez le potentiometre — la reponse du LLM s'affiche sur l'OLED et dans le moniteur serie
5. Ajustez votre prompt pour que les reponses soient pertinentes et tiennent sur l'ecran

### 2.10 Passer a Groq — votre propre compte

Une fois que ca fonctionne avec le endpoint du cours, creez votre propre compte sur Groq :

1. Allez sur **https://console.groq.com**
2. Creez un compte (connexion avec Google ou GitHub)
3. Allez dans **API Keys** et creez une nouvelle cle
4. Dans `config.h`, commentez les lignes du endpoint du cours et decommentez les lignes Groq :

```cpp
// --- Endpoint du cours (commenter) ---
// const char* OPENWEBUI_URL   = "https://chat.ve2fpd.com/api/chat/completions";
// const char* API_KEY    = "cle-fournie-en-classe";
// const char* MODEL_NAME = "assistant-iot-v2";

// --- Votre compte Groq (decommenter) ---
const char* OPENWEBUI_URL   = "https://api.groq.com/openai/v1/chat/completions";
const char* API_KEY    = "gsk_votre_cle_ici";
const char* MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct";
```

5. Televersez et verifiez que ca fonctionne aussi avec Groq

### 2.11 Commit avec GitHub Desktop

1. Ouvrez **GitHub Desktop** — vous devriez voir vos fichiers modifies
2. Verifiez que `config.h` **n'apparait pas** dans la liste (il est ignore par `.gitignore`)
3. Cochez les fichiers : `.gitignore`, `config.example.h`, `labo4-llm-esp32.ino`
4. Message de commit : `Premier commit - appel LLM depuis ESP32`
5. Cliquez **Commit to main**

---

## Questions d'analyse

1. Pourquoi est-il important de ne pas commiter le fichier `config.h`?
2. Quelle est la difference entre `max_tokens` et `temperature` dans les parametres de l'API?
3. Pourquoi utilise-t-on `setInsecure()` et quelles sont les implications en production?
4. Comment pourriez-vous optimiser le nombre d'appels API pour economiser les tokens?

---

## Pour aller plus loin

- Utiliser d'autres capteurs (boutons, MPU6050) pour enrichir le contexte envoye au LLM
- Implementer un cache pour eviter les appels repetitifs avec la meme valeur
- Essayer differents modeles sur Groq et comparer les reponses
