# Liste de pièces — Projet final Hydro-Limoilou

**Cours :** 243-4J5-LI – Objets connectés
**Évaluation :** Projet final IdO (semaines 13-15)
**Cohorte :** 8 étudiant·es (4 voie LoRa + 4 voie LTE)

---

## 1. Décompte par étudiant·e (modules assignés)

| # | DHT22 | MPU6050 | BH1750 | HC-SR501 | Pot | Bouton | LED |
|:-:|:-----:|:-------:|:------:|:--------:|:---:|:------:|:---:|
| 1 (LoRa) | 1 | 1 | 0 | 0 | 0 | 2 | 2 |
| 2 (LoRa) | 0 | 0 | 1 | 1 | 1 | 1 | 1 |
| 3 (LoRa) | 1 | 0 | 1 | 0 | 1 | 1 | 1 |
| 4 (LoRa) | 0 | 1 | 0 | 1 | 1 | 1 | 2 |
| 5 (LTE) | 1 | 0 | 0 | 1 | 2 | 0 | 2 |
| 6 (LTE) | 0 | 1 | 1 | 0 | 0 | 2 | 2 |
| 7 (LTE) | 1 | 0 | 1 | 1 | 0 | 0 | 2 |
| 8 (LTE) | 1 | 1 | 0 | 0 | 1 | 2 | 1 |
| **TOTAL fonctionnel** | **5** | **4** | **4** | **4** | **6** | **9** | **13** |

---

## 2. Hôtes (microcontrôleurs)

Probablement **déjà inventoriés** depuis les Labos précédents — vérifier le stock avant de commander.

| Composant | Fonctionnel | Rechange | **Total** | Notes |
|-----------|:-----------:|:--------:|:---------:|-------|
| **LilyGO T-Beam SUPREME** (ESP32-S3 + LoRa SX1262 + GPS) | 8 (= 4 étudiant·es × 2) | 2 | **10** | Voie LoRa : 1 nœud distant + 1 gateway WiFi par étudiant·e |
| **LilyGO A7670G** (ESP32 + LTE Cat-1 + GPS) | 4 | 1 | **5** | Voie LTE : 1 par étudiant·e (réutilisé du mid-session) |

---

## 3. Modules breakout (capteurs)

Marge de rechange ≈ 40% (composants fragiles, fils dupont peu fiables, casses fréquentes).

| Module | Référence courante | Fonctionnel | Rechange | **Total** | Fournisseur suggéré |
|--------|---------------------|:-----------:|:--------:|:---------:|---------------------|
| **DHT22** (température + humidité) | AM2302 sur PCB | 5 | 3 | **8** | AliExpress, Amazon, DigiKey |
| **MPU6050** (accéléromètre + gyro I2C) | GY-521 | 4 | 3 | **7** | AliExpress, Amazon |
| **BH1750** (luminosité I2C) | GY-302 | 4 | 3 | **7** | AliExpress, Amazon |
| **HC-SR501** (PIR détecteur de mouvement) | HC-SR501 standard | 4 | 3 | **7** | AliExpress, Amazon |

---

## 4. Composants discrets

Marge de rechange élevée : ces composants sont consommables et faciles à perdre/casser.

| Composant | Fonctionnel | Rechange | **Total** | Notes |
|-----------|:-----------:|:--------:|:---------:|-------|
| **Potentiomètre** 10 kΩ linéaire (3 broches, format breadboard) | 6 | 6 | **12** | Privilégier modèles avec axe et boîtier solide |
| **Bouton-poussoir** 4 broches type tactile (12 mm × 12 mm) | 9 | 11 | **20** | Achat en lot (sachets de 25-50) souvent économique |
| **LED** 5 mm assorties (rouge, vert, jaune, bleu) | 13 | 17 | **30** | Acheter un kit assorti (≈ 100 LEDs pour ~10 $) |
| **Résistance** 220 Ω à 330 Ω (pour LEDs) | 13 | 37 | **50** | Sachet de 100 ou kit assortiment |

---

## 5. Accessoires de prototypage

| Accessoire | Fonctionnel | Rechange | **Total** | Notes |
|------------|:-----------:|:--------:|:---------:|-------|
| **Breadboard** 830 points (full-size) | 8 | 2 | **10** | 1 par étudiant·e ; éviter les modèles bas de gamme (mauvais contacts) |
| **Set fils dupont** mâle-mâle (40 fils, 20 cm) | 8 | 2 | **10** | Pack de 40 |
| **Set fils dupont** mâle-femelle (40 fils, 20 cm) | 8 | 2 | **10** | Pack de 40 — utile pour les modules breakout |
| **Set fils dupont** femelle-femelle (40 fils, 20 cm) | 8 | 2 | **10** | Pack de 40 |

---

## 6. Alimentation et radio

| Composant | Fonctionnel | Rechange | **Total** | Notes |
|-----------|:-----------:|:--------:|:---------:|-------|
| **Batterie 18650** (≥ 2500 mAh, protégée) | 8 | 4 | **12** | Pour T-Beam SUPREME (1 par carte) ; vérifier polarité avant insertion |
| **Câble USB-C** (programmation/alim) | 12 | 3 | **15** | T-Beam SUPREME + A7670G utilisent USB-C |
| **Antenne LoRa 915 MHz** (SMA) | 8 | 2 | **10** | Souvent incluse avec le T-Beam ; vérifier gain (≥ 2 dBi) |
| **Antenne LTE** (SMA, multibande 700-2700 MHz) | 4 | 1 | **5** | Souvent incluse avec le A7670G |
| **Antenne GPS** (active, SMA) | 12 | 2 | **14** | Pour T-Beam (8) et A7670G (4) |
| **Carte SIM IoT/M2M** ou prépayée | 4 | 1 | **5** | Voie LTE — vérifier compatibilité bandes A7670G (LTE Cat-1 B2/B4/B12) |

---

## 7. Infrastructure individuelle (déjà en place depuis Labos 1-2)

| Composant | Quantité | Notes |
|-----------|:--------:|-------|
| Raspberry Pi 5 + alim + carte microSD | 8 | Déjà déployé |
| Écran tactile compatible Pi 5 | 8 | Déjà déployé |
| Domaine Cloudflare personnel | 8 | Déjà configuré |

---

## 8. Récapitulatif des achats à faire (estimé)

Hypothèse : les hôtes (T-Beam SUPREME, A7670G) et l'infrastructure Pi 5 sont **déjà disponibles** depuis les labos antérieurs. Les achats neufs concernent principalement les modules breakout et consommables.

| Catégorie | Quantité | Coût unitaire estimé (CAD) | Coût total estimé |
|-----------|:--------:|:--------------------------:|:-----------------:|
| DHT22 | 8 | 5 $ | 40 $ |
| MPU6050 (GY-521) | 7 | 3 $ | 21 $ |
| BH1750 (GY-302) | 7 | 3 $ | 21 $ |
| HC-SR501 | 7 | 3 $ | 21 $ |
| Potentiomètre 10 kΩ | 12 | 1 $ | 12 $ |
| Boutons tactiles (lot 50) | 1 lot | 8 $ | 8 $ |
| LEDs assorties (kit 100) | 1 kit | 10 $ | 10 $ |
| Résistances (assortiment) | 1 kit | 10 $ | 10 $ |
| Breadboards (10) | 10 | 6 $ | 60 $ |
| Fils dupont (3 packs × 10) | 30 | 5 $ | 150 $ |
| Batteries 18650 (rechange) | 4 | 8 $ | 32 $ |
| Câbles USB-C (rechange) | 3 | 5 $ | 15 $ |
| **TOTAL approximatif** | | | **≈ 400 $** |

> Les coûts sont indicatifs ; ajuster selon fournisseur (AliExpress moins cher mais lead time long, Amazon/DigiKey plus rapides).

---

## 9. Vérifications à faire avant la commande

- [ ] Inventorier les T-Beam SUPREME et A7670G existants (suffisant pour 10 + 5 unités ?)
- [ ] Vérifier l'état des batteries 18650 disponibles (cycle, capacité résiduelle)
- [ ] Vérifier la disponibilité de cartes SIM IoT chez le fournisseur retenu
- [ ] Confirmer avec le département la procédure d'achat (bon de commande, fournisseurs autorisés)
- [ ] Anticiper les délais de livraison (AliExpress 4-6 semaines ; Amazon/DigiKey 1-2 semaines)
- [ ] Prévoir les achats au moins **3 semaines avant la sem. 13**

---

## 10. Optionnel / améliorations futures

| Composant | Justification |
|-----------|---------------|
| Boîtiers 3D pour shield + hôte | Présentation finale plus professionnelle |
| Multimètre supplémentaire | Dépannage électrique en labo |
| Analyseur logique USB | Diagnostic I2C / UART |
| Sondes de tension/courant supplémentaires | Validation alimentation |

---

**Fin du document — Liste de pièces**
