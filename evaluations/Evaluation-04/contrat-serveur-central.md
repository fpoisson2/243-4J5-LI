# Contrat technique avec le serveur central — Hydro-Limoilou
**Cours :** 243-4J5-LI – Objets connectés
**Évaluation :** Projet final IdO
**Audience :** étudiant·es (publication des données) + enseignant (souscription côté VM)

---

## 1. Objet du contrat

Ce document fixe le **contrat technique** que chaque site doit respecter pour que le **serveur central VM** (géré par l'enseignant) puisse :

1. Se connecter au courtier MQTT du Pi 5 de l'étudiant·e via Cloudflare Tunnel
2. Souscrire aux topics du site avec une convention uniforme
3. Agréger les 8 sites dans un dashboard global

Le respect du contrat conditionne plusieurs critères des grilles d'évaluation (CP1 1.2, CP2 2.1/2.4, CP3 3.4/3.5/3.6).

---

## 2. Identifiant de site

Chaque site est identifié par un `site-id` numéroté de `poste-01` à `poste-08`, attribué par l'enseignant en début de semaine 13.

| # | Voie | site-id | Site (mise en situation) |
|---|------|---------|--------------------------|
| 1 | LoRa | `poste-01` | Tour relais nord |
| 2 | LoRa | `poste-02` | Cabinet de jonction fluvial |
| 3 | LoRa | `poste-03` | Poste de mesure forestier |
| 4 | LoRa | `poste-04` | Mât météo radio |
| 5 | LTE | `poste-05` | Sous-station urbaine |
| 6 | LTE | `poste-06` | Antenne rooftop centre-ville |
| 7 | LTE | `poste-07` | Station de pompage instrumentée |
| 8 | LTE | `poste-08` | Refuge technique de campagne |

---

## 3. Convention de topics

Tous les topics sont préfixés par `hydro-limoilou/{site-id}/`.

```
hydro-limoilou/{site-id}/telemetry/{capteur}     # Mesures périodiques
hydro-limoilou/{site-id}/status                  # État périodique du nœud
hydro-limoilou/{site-id}/alarm/{type}            # Évènements ponctuels
hydro-limoilou/{site-id}/actuators/{nom}         # Commandes descendantes (VM → site)
```

### 3.1 Sous-topics standardisés `telemetry/`

| Module | Sous-topic(s) | Champs payload |
|--------|---------------|----------------|
| DHT22 | `temperature`, `humidity` | `value` (float), `unit` (`"C"`, `"%"`), `ts` (int Unix) |
| BH1750 | `light` | `value` (float), `unit` (`"lux"`), `ts` |
| MPU6050 | `vibration` | `x`, `y`, `z` (float, m/s²), `ts` |
| Potentiomètre | nom selon site (voir §3.2) | `value` (float), `unit`, `ts` |

### 3.2 Sous-topics analogiques (potentiomètres) par site

Le sous-topic du potentiomètre est nommé selon la **mise en situation** du site, pas selon son numéro de pin :

| # | Site | Sous-topic potentiomètre(s) | Unité simulée | Plage |
|---|------|------------------------------|---------------|-------|
| 2 | Cabinet fluvial | `telemetry/water_level` | `cm` | 0 - 200 |
| 3 | Poste forestier | `telemetry/battery_v` | `V` | 10 - 14 |
| 4 | Mât météo | `telemetry/wind_speed` | `km/h` | 0 - 120 |
| 5 | Sous-station | `telemetry/voltage_line`, `telemetry/current_line` | `V`, `A` | 200-260, 0-100 |
| 8 | Refuge technique | `telemetry/fuel_level` | `%` | 0 - 100 |

### 3.3 Topic `status`

Publié toutes les **30 secondes** (rétention activée).

```json
{
  "uptime": 3600,
  "rssi": -67,
  "link": "lora",
  "battery_v": 3.92,
  "ts": 1739500000
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `uptime` | int | Secondes depuis le dernier boot du nœud |
| `rssi` | int | RSSI du dernier paquet reçu (LoRa) ou signal cellulaire (LTE), en dBm |
| `link` | string | `"lora"` ou `"lte"` |
| `battery_v` | float | Tension batterie 18650 (LoRa) ou alim externe (LTE) |
| `ts` | int | Timestamp Unix |

### 3.4 Topics `alarm/{type}`

Publiés **une seule fois** au déclenchement (QoS ≥ 1, rétention non activée).

```json
{
  "level": "warning",
  "value": 12.3,
  "unit": "deg",
  "ts": 1739500000
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `level` | string | `"info"`, `"warning"`, `"critical"` |
| `value` | number | Valeur déclenchante (optionnel) |
| `unit` | string | Unité (optionnel) |
| `ts` | int | Timestamp Unix |

#### Types d'alarme par site (selon mise en situation)

| # | Site | Types d'alarme attendus |
|---|------|-------------------------|
| 1 | Tour relais nord | `vibration` (vent), `motion` |
| 2 | Cabinet fluvial | `water` (niveau), `motion`, `door` |
| 3 | Poste forestier | `battery_low`, `temperature` |
| 4 | Mât météo | `tilt`, `motion` |
| 5 | Sous-station | `motion`, `voltage`, `current` |
| 6 | Antenne rooftop | `tilt`, `light` (anomalie ensoleillement) |
| 7 | Station de pompage | `motion`, `door` |
| 8 | Refuge technique | `tilt` (choc), `fuel_low`, `temperature` |

### 3.5 Topics `actuators/{nom}` (descendants)

La VM peut publier des commandes descendantes pour piloter une LED ou un actionneur côté site.

```
hydro-limoilou/poste-01/actuators/led_1     {"state": "on"}
hydro-limoilou/poste-01/actuators/led_2     {"state": "off"}
```

| Champ | Type | Valeurs |
|-------|------|---------|
| `state` | string | `"on"`, `"off"` |

Au minimum **une LED** par site doit être contrôlable via ce topic (vérifié au CP2).

---

## 4. Fréquences de publication

| Type de topic | Fréquence minimale | Fréquence recommandée |
|---------------|--------------------|------------------------|
| `telemetry/temperature`, `humidity`, `light` | 1 / 30 s | 1 / 10 s |
| `telemetry/vibration` | 1 / 5 s | 1 / 1 s (échantillon brut ou moyenne glissante) |
| `telemetry/{analogique}` | 1 / 10 s | 1 / 2 s |
| `status` | 1 / 60 s | 1 / 30 s |
| `alarm/*` | événementiel | événementiel + ack |

---

## 5. Format de payload (règles communes)

- **Encodage** : UTF-8, JSON valide
- **Champ `ts`** : timestamp Unix en secondes (int), obligatoire pour `telemetry/*`, `alarm/*`, et `status`
- **Champ `value`** : float pour les mesures scalaires, sinon objet (`x`, `y`, `z` pour vibration)
- **Champ `unit`** : string SI courte (`"C"`, `"V"`, `"A"`, `"%"`, `"lux"`, `"km/h"`, etc.)
- **Pas de retours à la ligne** dans le payload
- **Taille recommandée** : ≤ 256 octets par message

### Exemple complet d'une session de publication (poste-01)

```
hydro-limoilou/poste-01/telemetry/temperature   {"value": 22.4, "unit": "C", "ts": 1739500000}
hydro-limoilou/poste-01/telemetry/humidity      {"value": 45.2, "unit": "%", "ts": 1739500000}
hydro-limoilou/poste-01/telemetry/vibration     {"x": 0.02, "y": -0.01, "z": 9.81, "ts": 1739500005}
hydro-limoilou/poste-01/status                  {"uptime": 3600, "rssi": -67, "link": "lora", "battery_v": 3.92, "ts": 1739500030}
hydro-limoilou/poste-01/alarm/vibration         {"level": "warning", "value": 1.45, "unit": "m/s2", "ts": 1739500045}
```

---

## 6. Exposition du courtier (côté étudiant·e)

Chaque Pi 5 doit rendre son courtier Mosquitto accessible au serveur central via **Cloudflare Tunnel** (déjà en place depuis Labos 1-2).

### Exigences

- Port **WSS:443** (chiffré) — exposé par tunnel sous le sous-domaine personnel
- Authentification **user/password** configurée (pas d'accès anonyme)
- ACL côté Mosquitto restreignant les permissions :
  - L'utilisateur central a un accès **lecture** sur `hydro-limoilou/{site-id}/#`
  - L'utilisateur central a un accès **écriture** sur `hydro-limoilou/{site-id}/actuators/#`

### Informations à transmettre à l'enseignant (au CP2)

| Information | Exemple |
|-------------|---------|
| URL de connexion | `wss://etudiant-prenom.example.com:443/mqtt` |
| Username central | `central` |
| Password central | (généré aléatoirement, ≥ 16 caractères) |
| `site-id` | `poste-03` |

À transmettre via le canal sécurisé désigné par l'enseignant (pas en clair sur Moodle).

---

## 7. Côté serveur central (référence)

L'enseignant maintient une VM avec :

- 8 connexions MQTT parallèles (une par site)
- Souscription `hydro-limoilou/+/+/+` (wildcard sur les 8 sites)
- Dashboard agrégé (par exemple Node-RED, Grafana, dashboard Python ou web)
- Validation périodique de la conformité des payloads

### Commande de validation pour un site

```bash
mosquitto_sub -h <url-tunnel-etudiant> -p 443 \
  -u central -P '<password>' \
  -t 'hydro-limoilou/poste-XX/#' -v
```

Cette commande doit retourner les topics et payloads en continu — c'est la base du critère 2.4 (visibilité du site depuis le serveur central).

---

## 8. Procédure de test rapide

Avant chaque checkpoint, exécuter (côté étudiant) :

```bash
# Test 1 : le broker local reçoit-il bien ?
mosquitto_sub -h localhost -t 'hydro-limoilou/poste-XX/#' -v

# Test 2 : le tunnel est-il accessible depuis l'extérieur ?
mosquitto_sub -h etudiant-prenom.example.com -p 443 \
  -u central -P '<password>' \
  -t 'hydro-limoilou/poste-XX/#' -v

# Test 3 : les payloads sont-ils du JSON valide ?
mosquitto_sub -h localhost -t 'hydro-limoilou/poste-XX/+/+' \
  | while read line; do echo "$line" | python3 -m json.tool; done
```

---

**Fin du document — Contrat serveur central**
