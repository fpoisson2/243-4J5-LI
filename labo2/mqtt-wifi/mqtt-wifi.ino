// Communication MQTT via WiFi pour LilyGO A7670G
// Labo 2 - Section 2 : Communication MQTT via WiFi
// Ce programme remplace la communication série par MQTT via WiFi.

#include <WiFi.h>
#include <PubSubClient.h>

// Configuration WiFi - À PERSONNALISER
const char* ssid = "VOTRE_SSID";
const char* password = "VOTRE_PASSWORD";

// Configuration MQTT - À PERSONNALISER
const char* mqtt_server = "192.168.1.9";  // IP de votre Raspberry Pi
const int mqtt_port = 1883;
const char* mqtt_client_id = "lilygo-esp32";

// Topics MQTT
const char* topic_command = "iot/led/command";      // Commandes vers LilyGO
const char* topic_status = "iot/led/status";        // Status depuis LilyGO
const char* topic_lwt = "iot/lilygo/status";        // Last Will

// Pins LED - À adapter selon votre circuit
#define LED_RED 25
#define LED_GREEN 26

// Clients
WiFiClient espClient;
PubSubClient mqttClient(espClient);

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Configuration LEDs
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  digitalWrite(LED_RED, LOW);
  digitalWrite(LED_GREEN, LOW);

  Serial.println("=========================");
  Serial.println("LilyGO - MQTT via WiFi");
  Serial.println("=========================");

  // Connexion WiFi
  connectWiFi();

  // Configuration MQTT
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(mqttCallback);

  // Connexion MQTT
  connectMQTT();
}

void loop() {
  // Maintenir la connexion MQTT
  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();

  // Heartbeat toutes les 10 secondes
  static unsigned long lastHeartbeat = 0;
  if (millis() - lastHeartbeat > 10000) {
    mqttClient.publish(topic_lwt, "online", true);  // Retained
    lastHeartbeat = millis();
  }
}

void connectWiFi() {
  Serial.print("Connexion WiFi à: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi connecté!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println("\n✗ Échec connexion WiFi");
    Serial.println("Redémarrage dans 5s...");
    delay(5000);
    ESP.restart();
  }
}

void connectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Connexion MQTT au broker ");
    Serial.print(mqtt_server);
    Serial.print(":");
    Serial.print(mqtt_port);
    Serial.print("...");

    // Connexion avec Last Will
    if (mqttClient.connect(mqtt_client_id, topic_lwt, 1, true, "offline")) {
      Serial.println(" ✓ Connecté!");

      // S'abonner aux commandes
      mqttClient.subscribe(topic_command, 1);  // QoS 1
      Serial.print("Abonné au topic: ");
      Serial.println(topic_command);

      // Publier le status online
      mqttClient.publish(topic_lwt, "online", true);  // Retained
      mqttClient.publish(topic_status, "{\"status\":\"ready\",\"leds\":{\"red\":\"off\",\"green\":\"off\"}}");

    } else {
      Serial.print(" ✗ Échec, rc=");
      Serial.println(mqttClient.state());
      Serial.println("Nouvelle tentative dans 5s...");
      delay(5000);
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Convertir payload en String
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.print("Message reçu [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

  // Traiter les commandes
  if (String(topic) == topic_command) {
    handleCommand(message);
  }
}

void handleCommand(String command) {
  command.trim();
  command.toLowerCase();

  if (command == "red") {
    digitalWrite(LED_RED, HIGH);
    digitalWrite(LED_GREEN, LOW);
    mqttClient.publish(topic_status, "{\"led\":\"red\",\"state\":\"on\"}");
    Serial.println("→ LED ROUGE allumée");

  } else if (command == "green") {
    digitalWrite(LED_RED, LOW);
    digitalWrite(LED_GREEN, HIGH);
    mqttClient.publish(topic_status, "{\"led\":\"green\",\"state\":\"on\"}");
    Serial.println("→ LED VERTE allumée");

  } else if (command == "off") {
    digitalWrite(LED_RED, LOW);
    digitalWrite(LED_GREEN, LOW);
    mqttClient.publish(topic_status, "{\"led\":\"all\",\"state\":\"off\"}");
    Serial.println("→ LEDs éteintes");

  } else {
    Serial.print("✗ Commande inconnue: ");
    Serial.println(command);
    mqttClient.publish(topic_status, "{\"error\":\"unknown_command\"}");
  }
}
