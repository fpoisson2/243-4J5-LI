// Test screen for Lilygo 7670e (ESP32)
// Sends component states via Serial, receives LED commands from Pi

// --- Pin definitions ---
#define LED_RED    21
#define LED_GREEN  22
#define LED_BLUE   23
#define POT1       39
#define POT2       36
#define BUTTON1    19
#define BUTTON2    18

// --- State ---
#define SEND_INTERVAL 20   // ms between status updates
unsigned long lastSend = 0;
bool ledR = false, ledG = false, ledB = false;

void setup() {
  Serial.begin(115200);

  pinMode(LED_RED,   OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_BLUE,  OUTPUT);

  digitalWrite(LED_RED,   LOW);
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_BLUE,  LOW);

  pinMode(BUTTON1, INPUT_PULLUP);
  pinMode(BUTTON2, INPUT_PULLUP);
}

void loop() {
  // --- Receive LED toggle commands from Pi ---
  if (Serial.available()) {
    char cmd = Serial.read();
    switch (cmd) {
      case 'R': ledR = !ledR; digitalWrite(LED_RED,   ledR); break;
      case 'G': ledG = !ledG; digitalWrite(LED_GREEN, ledG); break;
      case 'B': ledB = !ledB; digitalWrite(LED_BLUE,  ledB); break;
    }
  }

  // --- Send status line: S,btn1,btn2,pot1,pot2,ledR,ledG,ledB ---
  unsigned long now = millis();
  if (now - lastSend >= SEND_INTERVAL) {
    lastSend = now;

    bool b1 = (digitalRead(BUTTON1) == LOW);
    bool b2 = (digitalRead(BUTTON2) == LOW);
    int  p1 = analogRead(POT1);
    int  p2 = analogRead(POT2);

    // CSV format: S,btn1,btn2,pot1,pot2,ledR,ledG,ledB
    Serial.print("S,");
    Serial.print(b1); Serial.print(',');
    Serial.print(b2); Serial.print(',');
    Serial.print(p1); Serial.print(',');
    Serial.print(p2); Serial.print(',');
    Serial.print(ledR); Serial.print(',');
    Serial.print(ledG); Serial.print(',');
    Serial.println(ledB);
  }

  delay(2);
}
