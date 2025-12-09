// Test du modem A7670G
// Labo 2 - Section 3 : Activation du modem LTE
// Vérifie la SIM, le signal et l'enregistrement réseau

#define MODEM_TX 27
#define MODEM_RX 26
#define MODEM_PWRKEY 4
#define MODEM_DTR 32
#define MODEM_RI 33
#define MODEM_FLIGHT 25
#define MODEM_STATUS 34

HardwareSerial SerialAT(1);  // UART1 pour le modem

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("=========================");
  Serial.println("Test Modem A7670G");
  Serial.println("=========================");

  // Configuration pins
  pinMode(MODEM_PWRKEY, OUTPUT);
  pinMode(MODEM_FLIGHT, OUTPUT);
  digitalWrite(MODEM_FLIGHT, HIGH);  // Mode normal

  // Initialiser communication série avec modem
  SerialAT.begin(115200, SERIAL_8N1, MODEM_RX, MODEM_TX);

  Serial.println("Démarrage du modem...");
  powerOnModem();

  delay(5000);  // Laisser le modem s'initialiser

  // Tests
  testModem();
}

void loop() {
  // Relayer les commandes AT manuelles
  if (Serial.available()) {
    SerialAT.write(Serial.read());
  }
  if (SerialAT.available()) {
    Serial.write(SerialAT.read());
  }
}

void powerOnModem() {
  // Séquence de démarrage
  digitalWrite(MODEM_PWRKEY, HIGH);
  delay(100);
  digitalWrite(MODEM_PWRKEY, LOW);
  delay(1000);
  digitalWrite(MODEM_PWRKEY, HIGH);

  Serial.println("✓ Séquence power ON envoyée");
}

void testModem() {
  Serial.println("\n--- Tests de communication ---");

  // Test 1: Communication basique
  Serial.print("Test AT... ");
  sendAT("AT");
  delay(500);

  // Test 2: Identité du modem
  Serial.print("\nInfo modem: ");
  sendAT("ATI");
  delay(500);

  // Test 3: Vérifier SIM
  Serial.print("\nTest SIM: ");
  sendAT("AT+CPIN?");
  delay(500);

  // Test 4: Qualité signal
  Serial.print("\nQualité signal: ");
  sendAT("AT+CSQ");
  delay(500);

  // Test 5: Enregistrement réseau
  Serial.print("\nEnregistrement réseau: ");
  sendAT("AT+CREG?");
  delay(500);

  // Test 6: Opérateur
  Serial.print("\nOpérateur: ");
  sendAT("AT+COPS?");
  delay(1000);

  Serial.println("\n--- Tests terminés ---");
  Serial.println("Vous pouvez maintenant envoyer des commandes AT manuellement.");
}

void sendAT(const char* cmd) {
  SerialAT.println(cmd);
  delay(100);

  // Lire réponse
  unsigned long timeout = millis() + 2000;
  while (millis() < timeout) {
    if (SerialAT.available()) {
      String response = SerialAT.readString();
      Serial.println(response);
      return;
    }
  }
  Serial.println("✗ Timeout");
}
