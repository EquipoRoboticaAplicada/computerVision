// --- Arduino + L298N: control desde Raspberry por Serial ---
// Protocolo:
//   'R','Y','B' -> motor ON (sentido fijo)
//   'S' o '0'   -> motor OFF
//   'V###'      -> velocidad PWM 0..255 (p. ej. V180)
//
// Cableado L298N (canal A):
//   ENA -> D9  (PWM)     |   IN1 -> D7
//   IN2 -> D8            |   Motor en OUT1/OUT2
//   +Vmotor (6-12 V) al pin 12V del L298N; GND común con Arduino
//
// Nota: si tu módulo tiene jumper en ENA, retíralo para usar PWM por D9.

// Pines L298N (canal A)
const int PIN_ENA = 9;   // PWM
const int PIN_IN1 = 7;
const int PIN_IN2 = 8;

// Parámetros
int pwmValue = 200;                // Velocidad base 0..255
const unsigned long TIMEOUT_MS = 2000;  // Fail-safe
unsigned long lastCmdMs = 0;
bool motorOn = false;

void motor_initL298N() {
  pinMode(PIN_ENA, OUTPUT);
  pinMode(PIN_IN1, OUTPUT);
  pinMode(PIN_IN2, OUTPUT);

  // Estado seguro al arrancar: apagado/coast
  analogWrite(PIN_ENA, 0);
  digitalWrite(PIN_IN1, LOW);
  digitalWrite(PIN_IN2, LOW);
}

void motor_setL298N(bool on, bool forward = true) {
  motorOn = on;
  if (!on) {
    // Apagado (coast): entradas en LOW, PWM=0
    analogWrite(PIN_ENA, 0);
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, LOW);
    return;
  }
  // Sentido fijo (puedes invertir cambiando forward)
  if (forward) {
    digitalWrite(PIN_IN1, HIGH);
    digitalWrite(PIN_IN2, LOW);
  } else {
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, HIGH);
  }
  analogWrite(PIN_ENA, pwmValue);
}

void setup() {
  motor_initL298N();

  Serial.begin(115200);
  while (!Serial) { ; }
  Serial.println("L298N listo. Comandos: R/Y/B=ON, S=OFF, V###=velocidad (0-255)");
  lastCmdMs = millis();
}

void handleSerial() {
  // Lectura por líneas: 'R','Y','B','S','0','V###'
  static String line;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (line.length() > 0) {
        char cmd = toupper(line[0]);
        if (cmd == 'R' || cmd == 'Y' || cmd == 'B') {
          motor_setL298N(true /*on*/);
          Serial.println("OK ON");
        } else if (cmd == 'S' || cmd == '0') {
          motor_setL298N(false /*off*/);
          Serial.println("OK OFF");
        } else if (cmd == 'V') {
          int val = line.substring(1).toInt();
          val = constrain(val, 0, 255);
          pwmValue = val;
          if (motorOn) analogWrite(PIN_ENA, pwmValue);
          Serial.print("OK V="); Serial.println(pwmValue);
        } else {
          Serial.println("ERR CMD");
        }
        lastCmdMs = millis();
      }
      line = "";
    } else {
      line += c;
      if (line.length() > 16) line = ""; // evita desbordes
    }
  }
}

void loop() {
  handleSerial();

  // Fail-safe: si no llegan comandos en TIMEOUT_MS, apaga motor
  if (millis() - lastCmdMs > TIMEOUT_MS) {
    if (motorOn) {
      motor_setL298N(false);
      Serial.println("TIMEOUT -> OFF");
    }
    lastCmdMs = millis(); // evita spameo
  }
}
