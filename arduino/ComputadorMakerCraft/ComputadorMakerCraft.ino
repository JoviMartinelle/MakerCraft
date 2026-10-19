// Sketch único do MakerCraft. O jogo grava este arquivo na primeira vez que acha a placa.
// O computador de cada sala manda o programa pela porta. Este sketch executa.
// MAKERCRAFT_READY 1 precisa ser o mesmo número de FirmwareInstaller.VERSION.

const int MAX_LINES = 32;

String lines[MAX_LINES];
int lineCount = 0;
bool recording = false;
bool running = false;
bool repeatProgram = false;
int pc = 0;
int runId = 0;
int activeRun = 0;
int signalLevel = 0;
int skip = 0;
int lastLevel[65];

void clearLevels() {
  for (int i = 0; i < 65; i++) {
    lastLevel[i] = -1;
  }
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(20);
  pinMode(LED_BUILTIN, OUTPUT);
  clearLevels();
}

void loop() {
  readSerial();
  if (running) {
    step();
  }
}

void readSerial() {
  while (Serial.available()) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();
    if (msg.length() == 0) {
      continue;
    }
    if (msg == "PROGRAM_BEGIN") {
      runId++;
      recording = true;
      running = false;
      lineCount = 0;
      continue;
    }
    if (msg == "PROGRAM_END") {
      recording = false;
      startProgram();
      continue;
    }
    if (msg.startsWith("REDSTONE_LEVEL:")) {
      signalLevel = msg.substring(15).toInt();
      continue;
    }
    if (msg == "HELLO_ARDUINO") {
      Serial.println("MAKERCRAFT_READY 1");
      continue;
    }
    if (recording && lineCount < MAX_LINES) {
      lines[lineCount++] = msg;
    }
  }
}

void startProgram() {
  clearLevels();
  repeatProgram = false;
  for (int i = 0; i < lineCount; i++) {
    if (lines[i] == "repetir") {
      repeatProgram = true;
    }
  }
  activeRun = runId;
  running = true;
  pc = 0;
  skip = 0;
}

void step() {
  readSerial();
  if (!running) {
    return;
  }

  if (pc >= lineCount) {
    if (repeatProgram) {
      pc = 0;
      skip = 0;
      delay(20);
    } else {
      running = false;
    }
    return;
  }

  String line = lines[pc++];
  line.trim();
  if (line.length() == 0 || line.startsWith("#") || line == "repetir") {
    return;
  }

  int space = line.indexOf(' ');
  String command = space == -1 ? line : line.substring(0, space);
  String argument = space == -1 ? "" : line.substring(space + 1);
  argument.trim();

  if (command == "quando" && argument == "sinal") {
    skip = signalLevel > 0 ? 0 : 1;
    return;
  }
  if (command == "senao") {
    if (skip == 1) {
      skip = 0;
    } else if (skip == 0) {
      skip = 2;
    }
    return;
  }
  if (command == "fim") {
    skip = 0;
    return;
  }
  if (skip != 0) {
    return;
  }

  if (command == "ligar" || command == "desligar") {
    writeOutput(argument.toInt(), command == "ligar");
  } else if (command == "esperar") {
    waitMs(argument.toInt());
  } else if (command == "led" && argument == "ligado") {
    digitalWrite(LED_BUILTIN, HIGH);
  } else if (command == "led" && argument == "desligado") {
    digitalWrite(LED_BUILTIN, LOW);
  }
}

void writeOutput(int number, bool on) {
  if (number < 1 || number > 64) {
    return;
  }

  int want = on ? 1 : 0;
  if (lastLevel[number] == want) {
    return;
  }

  if (Serial.availableForWrite() < 24) {
    pc--;
    delay(2);
    return;
  }

  lastLevel[number] = want;
  Serial.print("OUTPUT:");
  Serial.print(number);
  Serial.println(on ? ":ON" : ":OFF");
}

void waitMs(int ms) {
  if (ms < 0) {
    ms = 0;
  }
  int myRun = activeRun;
  unsigned long start = millis();
  while ((long)(millis() - start) < ms) {
    readSerial();
    if (activeRun != myRun || !running) {
      return;
    }
    delay(5);
  }
}
