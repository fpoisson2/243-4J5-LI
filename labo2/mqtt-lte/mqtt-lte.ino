// Communication MQTT via LTE pour LilyGO A7670G
// Labo 2 - Section 4 : Communication MQTT via LTE
// Publie des messages MQTT via le réseau cellulaire

#define TINY_GSM_MODEM_SIM7600  // Compatible avec A7670G
#include <TinyGsmClient.h>
#include <PubSubClient.h>

// Pins modem
#define MODEM_TX 27
#define MODEM_RX 26
#define MODEM_PWRKEY 4
#define MODEM_DTR 32
#define MODEM_RI 33
#define MODEM_FLIGHT 25

// Pins LED - À adapter selon votre circuit
#define LED_RED 12
#define LED_GREEN 13

// Configuration réseau cellulaire - À PERSONNALISER selon votre opérateur
// Rogers: "internet.com"
// Bell: "inet.bell.ca"
// Telus: "sp.telus.com"
// Fido: "internet.fido.ca"
const char* apn = "internet.com";
const char* gprsUser = "";
const char* gprsPass = "";

// Configuration MQTT - À PERSONNALISER
const char* mqtt_server = "mqtt.edxo.ca";  // Ou broker public: test.mosquitto.org
const int mqtt_port = 1883;
const char* mqtt_client_id = "lilygo-lte";

// Topics MQTT
const char* topic_command = "iot/led/command";
const char* topic_status = "iot/led/status";
const char* topic_lwt = "iot/lilygo/status";
const char* topic_network = "iot/lilygo/network";

// Clients
HardwareSerial SerialAT(1);
TinyGsm modem(SerialAT);
TinyGsmClient gsmClient(modem);
PubSubClient mqttClient(gsmClient);

void setup() {
  Serial.begin(115200);
  delay(2000);

  // Configuration LEDs
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  digitalWrite(LED_RED, LOW);
  digitalWrite(LED_GREEN, LOW);

  // Configuration modem pins
  pinMode(MODEM_PWRKEY, OUTPUT);
  pinMode(MODEM_FLIGHT, OUTPUT);
  digitalWrite(MODEM_FLIGHT, HIGH);

  Serial.println("=========================");
  Serial.println("LilyGO - MQTT via LTE");
  Serial.println("=========================");

  // Initialiser modem
  SerialAT.begin(115200, SERIAL_8N1, MODEM_RX, MODEM_TX);

  Serial.println("Démarrage modem...");
  powerOnModem();
  delay(3000);

  // Connexion réseau cellulaire
  connectCellular();

  // Configuration MQTT
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setKeepAlive(60);

  // Connexion MQTT
  connectMQTT();
}

void loop() {
  // Maintenir connexions
  if (!modem.isNetworkConnected()) {
    Serial.println("✗ Réseau cellulaire perdu, reconnexion...");
    connectCellular();
  }

  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();

  // Heartbeat toutes les 30 secondes
  static unsigned long lastHeartbeat = 0;
  if (millis() - lastHeartbeat > 30000) {
    publishNetworkInfo();
    mqttClient.publish(topic_lwt, "online", true);
    lastHeartbeat = millis();
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
  Serial.println("Initialisation du modem...");

  if (!modem.restart()) {
    Serial.println("✗ Échec restart modem");
    delay(5000);
    ESP.restart();
  }

  String modemInfo = modem.getModemInfo();
  Serial.print("Modem: ");
  Serial.println(modemInfo);

  // Attendre enregistrement réseau
  Serial.print("Attente réseau cellulaire");
  if (!modem.waitForNetwork(60000L)) {
    Serial.println("\n✗ Échec enregistrement réseau");
    delay(5000);
    ESP.restart();
  }
  Serial.println(" ✓");

  // Connexion GPRS
  Serial.print("Connexion GPRS");
  if (!modem.gprsConnect(apn, gprsUser, gprsPass)) {
    Serial.println(" ✗ Échec");
    delay(5000);
    ESP.restart();
  }
  Serial.println(" ✓");

  // Afficher info réseau
  printNetworkInfo();
}

void printNetworkInfo() {
  Serial.println("\n--- Info réseau ---");

  int csq = modem.getSignalQuality();
  Serial.print("Signal (CSQ): ");
  Serial.println(csq);

  String cop = modem.getOperator();
  Serial.print("Opérateur: ");
  Serial.println(cop);

  IPAddress ip = modem.localIP();
  Serial.print("IP locale: ");
  Serial.println(ip);

  Serial.println("-------------------\n");
}

void publishNetworkInfo() {
  int csq = modem.getSignalQuality();
  String cop = modem.getOperator();
  IPAddress ip = modem.localIP();

  String payload = "{";
  payload += "\"signal\":" + String(csq) + ",";
  payload += "\"operator\":\"" + cop + "\",";
  payload += "\"ip\":\"" + ip.toString() + "\"";
  payload += "}";

  mqttClient.publish(topic_network, payload.c_str());
}

void connectMQTT() {
  int attempts = 0;
  while (!mqttClient.connected() && attempts < 3) {
    Serial.print("Connexion MQTT à ");
    Serial.print(mqtt_server);
    Serial.print("...");

    if (mqttClient.connect(mqtt_client_id, topic_lwt, 1, true, "offline")) {
      Serial.println(" ✓");

      mqttClient.subscribe(topic_command, 1);
      mqttClient.publish(topic_lwt, "online", true);
      mqttClient.publish(topic_status, "{\"status\":\"ready\",\"connection\":\"lte\"}");

      publishNetworkInfo();

    } else {
      Serial.print(" ✗ rc=");
      Serial.println(mqttClient.state());
      attempts++;
      delay(5000);
    }
  }

  if (!mqttClient.connected()) {
    Serial.println("Échec connexion MQTT, redémarrage...");
    delay(5000);
    ESP.restart();
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
    mqttClient.publish(topic_status, "{\"led\":\"red\",\"state\":\"on\"}");
    Serial.println("→ LED ROUGE");

  } else if (command == "green") {
    digitalWrite(LED_RED, LOW);
    digitalWrite(LED_GREEN, HIGH);
    mqttClient.publish(topic_status, "{\"led\":\"green\",\"state\":\"on\"}");
    Serial.println("→ LED VERTE");

  } else if (command == "off") {
    digitalWrite(LED_RED, LOW);
    digitalWrite(LED_GREEN, LOW);
    mqttClient.publish(topic_status, "{\"led\":\"all\",\"state\":\"off\"}");
    Serial.println("→ LEDs OFF");

  } else if (command == "status") {
    publishNetworkInfo();

  } else {
    mqttClient.publish(topic_status, "{\"error\":\"unknown_command\"}");
  }
}
