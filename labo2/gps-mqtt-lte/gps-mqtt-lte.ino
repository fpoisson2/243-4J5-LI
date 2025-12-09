// GPS + MQTT via LTE pour LilyGO A7670G
// Labo 2 - Section 5 : Intégration GPS
// Récupère la position GPS et l'envoie via MQTT sur LTE

#define TINY_GSM_MODEM_SIM7600
#include <TinyGsmClient.h>
#include <PubSubClient.h>
#include <TinyGPSPlus.h>

// Pins modem
#define MODEM_TX 27
#define MODEM_RX 26
#define MODEM_PWRKEY 4
#define MODEM_FLIGHT 25

// Pins LED - À adapter selon votre circuit
#define LED_RED 12
#define LED_GREEN 13

// Configuration - À PERSONNALISER
const char* apn = "internet.com";
const char* mqtt_server = "mqtt.edxo.ca";
const int mqtt_port = 1883;
const char* mqtt_client_id = "lilygo-gps-lte";

// Topics
const char* topic_command = "iot/led/command";
const char* topic_status = "iot/led/status";
const char* topic_gps = "iot/gps/location";
const char* topic_lwt = "iot/lilygo/status";

// Clients
HardwareSerial SerialAT(1);
TinyGsm modem(SerialAT);
TinyGsmClient gsmClient(modem);
PubSubClient mqttClient(gsmClient);
TinyGPSPlus gps;

// GPS tracking
unsigned long lastGPSPublish = 0;
const unsigned long GPS_PUBLISH_INTERVAL = 10000;  // Publier GPS toutes les 10s

void setup() {
  Serial.begin(115200);
  delay(2000);

  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(MODEM_PWRKEY, OUTPUT);
  pinMode(MODEM_FLIGHT, OUTPUT);
  digitalWrite(MODEM_FLIGHT, HIGH);

  Serial.println("=========================");
  Serial.println("LilyGO - GPS + MQTT LTE");
  Serial.println("=========================");

  SerialAT.begin(115200, SERIAL_8N1, MODEM_RX, MODEM_TX);

  powerOnModem();
  delay(3000);

  connectCellular();
  enableGPS();

  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setKeepAlive(60);

  connectMQTT();
}

void loop() {
  // Maintenir connexions
  if (!modem.isNetworkConnected()) {
    connectCellular();
  }
  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();

  // Lire données GPS
  readGPS();

  // Publier position GPS périodiquement
  if (millis() - lastGPSPublish > GPS_PUBLISH_INTERVAL) {
    if (gps.location.isValid()) {
      publishGPS();
    } else {
      Serial.println("GPS: En attente de fix...");
      mqttClient.publish(topic_gps, "{\"status\":\"no_fix\"}");
    }
    lastGPSPublish = millis();
  }
}

void powerOnModem() {
  digitalWrite(MODEM_PWRKEY, HIGH);
  delay(100);
  digitalWrite(MODEM_PWRKEY, LOW);
  delay(1000);
  digitalWrite(MODEM_PWRKEY, HIGH);
}

void connectCellular() {
  Serial.println("Connexion réseau cellulaire...");

  if (!modem.restart()) {
    Serial.println("✗ Échec restart");
    delay(5000);
    ESP.restart();
  }

  if (!modem.waitForNetwork(60000L)) {
    Serial.println("✗ Pas de réseau");
    delay(5000);
    ESP.restart();
  }

  if (!modem.gprsConnect(apn, "", "")) {
    Serial.println("✗ Échec GPRS");
    delay(5000);
    ESP.restart();
  }

  Serial.println("✓ Réseau cellulaire connecté");
  Serial.print("IP: ");
  Serial.println(modem.localIP());
}

void enableGPS() {
  Serial.println("Activation GPS...");

  // Activer GPS
  SerialAT.println("AT+CGPS=1,1");
  delay(200);

  // Lire réponse
  while (SerialAT.available()) {
    Serial.write(SerialAT.read());
  }

  Serial.println("✓ GPS activé (acquisition en cours...)");
  Serial.println("Patientez 30s-2min pour le premier fix GPS");
}

void readGPS() {
  // Demander position GPS
  SerialAT.println("AT+CGPSINFO");
  delay(100);

  // Lire et parser réponse NMEA
  while (SerialAT.available()) {
    char c = SerialAT.read();
    gps.encode(c);
  }
}

void publishGPS() {
  String payload = "{";
  payload += "\"latitude\":" + String(gps.location.lat(), 6) + ",";
  payload += "\"longitude\":" + String(gps.location.lng(), 6) + ",";
  payload += "\"altitude\":" + String(gps.altitude.meters(), 1) + ",";
  payload += "\"speed\":" + String(gps.speed.kmph(), 1) + ",";
  payload += "\"satellites\":" + String(gps.satellites.value()) + ",";
  payload += "\"hdop\":" + String(gps.hdop.value() / 100.0, 2) + ",";
  payload += "\"timestamp\":\"" + getGPSTimestamp() + "\"";
  payload += "}";

  mqttClient.publish(topic_gps, payload.c_str());

  Serial.println("GPS publié:");
  Serial.print("  Lat: ");
  Serial.println(gps.location.lat(), 6);
  Serial.print("  Lon: ");
  Serial.println(gps.location.lng(), 6);
  Serial.print("  Alt: ");
  Serial.print(gps.altitude.meters());
  Serial.println(" m");
  Serial.print("  Satellites: ");
  Serial.println(gps.satellites.value());
}

String getGPSTimestamp() {
  if (!gps.time.isValid() || !gps.date.isValid()) {
    return "invalid";
  }

  char timestamp[32];
  snprintf(timestamp, sizeof(timestamp), "%04d-%02d-%02dT%02d:%02d:%02dZ",
           gps.date.year(), gps.date.month(), gps.date.day(),
           gps.time.hour(), gps.time.minute(), gps.time.second());

  return String(timestamp);
}

void connectMQTT() {
  Serial.print("Connexion MQTT...");
  if (mqttClient.connect(mqtt_client_id, topic_lwt, 1, true, "offline")) {
    Serial.println(" ✓");
    mqttClient.subscribe(topic_command, 1);
    mqttClient.publish(topic_lwt, "online", true);
  } else {
    Serial.print(" ✗ rc=");
    Serial.println(mqttClient.state());
    delay(5000);
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.print("MQTT [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

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
    mqttClient.publish(topic_status, "{\"led\":\"red\"}");
  } else if (command == "green") {
    digitalWrite(LED_RED, LOW);
    digitalWrite(LED_GREEN, HIGH);
    mqttClient.publish(topic_status, "{\"led\":\"green\"}");
  } else if (command == "off") {
    digitalWrite(LED_RED, LOW);
    digitalWrite(LED_GREEN, LOW);
    mqttClient.publish(topic_status, "{\"led\":\"off\"}");
  } else if (command == "gps") {
    if (gps.location.isValid()) {
      publishGPS();
    } else {
      mqttClient.publish(topic_gps, "{\"status\":\"no_fix\"}");
    }
  }
}
