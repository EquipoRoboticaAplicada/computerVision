// ==== Pines TB6612 (opción A) ====
const int PIN_STBY = 6;
const int PIN_AIN1 = 7;
const int PIN_AIN2 = 8;
const int PIN_PWMA = 9;   // PWM

// ==== MOSFET (opción B) ====
// const int MOTOR_PWM = 9;  // Usa este mismo pin para gate del MOSFET

// ==== Parámetros ====
int pwmValue = 200;           // 0–255 (ajusta velocidad base)
const unsigned long TIMEOUT_MS = 2000;  // fail-safe
unsigned long lastCmdMs = 0;
bool motorOn = false;

void motor_enableTB6612(bool enable) {
  digitalWrite(PIN_STBY, enable ? HIGH : LOW);
}

void motor_setTB6612(bool on, bool forward = true) {
  motorOn = on;
  if (!on) {
    // Frenado/coast
    analogWrite(PIN_PWMA, 0);
    digitalWrite(PIN_AIN1, LOW);
    digitalWrite(PIN_AIN2, LOW);
    return;
  }
  // Sentido fijo (opcional cambiar con forward)
  digitalWrite(PIN_AIN1, forward ? HIGH : LOW);
  digitalWrite(PIN_AIN2, forward ? LOW  : HIGH);
  analogWrite(PIN_PWMA, pwmValue);
}

void setup() {
  // TB6612
  pinMode(PIN_STBY, OUTPUT);
  pinMode(PIN_AIN1, OUTPUT);
  pinMode(PIN_AIN2, OUTPUT);
  pinMode(PIN_PWMA, OUTPUT);
  motor_enableTB6612(true);
  motor_setTB6612(false);

  // MOSFET (si lo usas, descomenta y maneja en setMotorMOSFET)
//  pinMode(MOTOR_PWM, OUTPUT);
//  analogWrite(MOTOR_PWM, 0);

  Serial.begin(115200);
  while (!Serial) { ; }
  Serial.println("Arduino listo. Comandos: R/Y/B=ON, S=OFF, V###=velocidad (0-255)");
  lastCmdMs = millis();
}

void handleSerial() {
  // Protocolo:
  //  - 'R','Y','B' -> motor ON
  //  - 'S' o '0'   -> motor OFF
  //  - 'V###\\n'   -> set PWM (0-255)
  static String line;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (line.length() > 0) {
        // Procesa línea completa
        char cmd = toupper(line[0]);
        if (cmd == 'R' || cmd == 'Y' || cmd == 'B') {
          motor_setTB6612(true);
          Serial.println("OK ON");
        } else if (cmd == 'S' || cmd == '0') {
          motor_setTB6612(false);
          Serial.println("OK OFF");
        } else if (cmd == 'V') {
          int val = line.substring(1).toInt();
          val = constrain(val, 0, 255);
          pwmValue = val;
          if (motorOn) {
            analogWrite(PIN_PWMA, pwmValue);
          }
          Serial.print("OK V="); Serial.println(pwmValue);
        } else {
          Serial.println("ERR CMD");
        }
        lastCmdMs = millis();
      }
      line = "";
    } else {
      line += c;
      // Seguridad: evita crecer infinito
      if (line.length() > 16) line = "";
    }
  }
}

void loop() {
  handleSerial();

  // Fail-safe: si no hay comandos en TIMEOUT_MS, apaga motor
  if (millis() - lastCmdMs > TIMEOUT_MS) {
    if (motorOn) {
      motor_setTB6612(false);
      Serial.println("TIMEOUT -> OFF");
    }
    lastCmdMs = millis(); // evita spamear
  }

  // (Opcional) monitoreo/telemetría
  // delay(10);
}

/* --- Si usas MOSFET (opción B), puedes reemplazar motor_setTB6612 por esto:
void motor_setMOSFET(bool on) {
  motorOn = on;
  analogWrite(MOTOR_PWM, on ? pwmValue : 0);
}
y en handleSerial() llama motor_setMOSFET() en lugar de motor_setTB6612().
No olvides comentar el bloque de pines TB6612 en setup().
*/
