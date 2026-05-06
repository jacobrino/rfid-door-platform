#include <LCD_I2C.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>
#include <Wire.h>

// ======== WIFI ======== 
const char* WIFI_SSID = "OPPO";
const char* WIFI_PASSWORD = "12345678";

// ======== LED ========
#define ledRed 2
#define ledGreen 4

// ======== I2C ========
#define SDA 25
#define SCL 26
LCD_I2C lcd(0x27,20,4);

// ======== API ========
const char* API_URL = "https://rfid-door-platform.onrender.com/api/esp32/access/check";
const char* BEARER_TOKEN = "q34y0ylyq4Ad3viJQRtYPmjjRmVyrI9OA45E3q1mLhU";

// ======== BUZZER ========
#define BUZZER_PIN 13

// ======== RFID ========
#define SS_PIN 5
#define RST_PIN 22
MFRC522 rfid(SS_PIN, RST_PIN);

// ======== SERVO ========
#define SERVO_PIN 12
Servo myServo;

// ======== DONNEES ========
String device_code = "ESP01";

// ======== LOGIQUE ========
bool messageApprocheAffiche = false;
bool traitementEnCours = false;


// ======== LCD ========
void lcdApproche() {
  lcd.clear();
  lcd.setCursor(0,1);
  lcd.print("Approchez carte");
}

void lcdSucces() {
  lcd.clear();
  lcd.setCursor(0,1);
  lcd.print("Acces autorise");
}

void lcdErreur() {
  lcd.clear();
  lcd.setCursor(0,1);
  lcd.print("Acces refuse");
}


// ===== WIFI =====
void connectWiFi() {
  Serial.print("Connexion au WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connecté");
  Serial.println(WiFi.localIP());
}


// ===== ENVOI API =====
void sendAccessCheck(String deviceCode, String rfidUid) {

  if (WiFi.status() != WL_CONNECTED) {
    lcdErreur();
    bipErreur();
    return;
  }

  HTTPClient http;
  http.begin(API_URL);

  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " + String(BEARER_TOKEN));

  StaticJsonDocument<200> requestDoc;
  requestDoc["device_code"] = deviceCode;
  requestDoc["uid"] = rfidUid;

  String requestBody;
  serializeJson(requestDoc, requestBody);

  int httpResponseCode = http.POST(requestBody);

  if (httpResponseCode > 0) {

    String response = http.getString();

    StaticJsonDocument<300> responseDoc;
    DeserializationError error = deserializeJson(responseDoc, response);

    if (error) {
      lcdErreur();
      bipErreur();
      http.end();
      return;
    }

    String decision = responseDoc["decision"];
    bool doorOpened = responseDoc["door_opened"];

    if (decision == "granted" && doorOpened == true) {
      lcdSucces();
      bipSucces();
      openDoor();
    } else {
      lcdErreur();
      bipErreur();
    }

  } else {
    lcdErreur();
    bipErreur();
  }

  http.end();

  delay(2000);
  lcdApproche();
}


// ===== RFID =====
String readUID() {

  if (!rfid.PICC_IsNewCardPresent()) return "";
  if (!rfid.PICC_ReadCardSerial()) return "";

  String uid = "";

  for (byte i = 0; i < rfid.uid.size; i++) {
    uid += String(rfid.uid.uidByte[i], HEX);
  }

  uid.toLowerCase();

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  return uid;
}


// ===== ATTENTE RETRAIT =====
void attendreRetraitCarte() {

  while (true) {
    byte bufferATQA[2];
    byte bufferSize = sizeof(bufferATQA);

    MFRC522::StatusCode status = rfid.PICC_WakeupA(bufferATQA, &bufferSize);

    if (status != MFRC522::STATUS_OK) break;

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
    delay(300);
  }

  delay(500);
}


// ===== PORTE =====
void openDoor() {
  myServo.write(90);
  delay(3000);
  myServo.write(0);
}


// ===== BUZZER =====
void bipSucces() {
  digitalWrite(BUZZER_PIN, HIGH);
  digitalWrite(ledGreen, HIGH);
  delay(150);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(ledGreen, LOW);
}

void bipErreur() {
  for (int i = 0; i < 3; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    digitalWrite(ledRed, HIGH);
    delay(200);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(ledRed, LOW);
    delay(100);
  }
}


// ===== SETUP =====
void setup() {
  Serial.begin(115200);

  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(ledRed, OUTPUT);
  pinMode(ledGreen, OUTPUT);

  Wire.begin(SDA, SCL);
  lcd.begin();
  lcd.backlight();

  lcdApproche();

  SPI.begin();
  rfid.PCD_Init();

  myServo.attach(SERVO_PIN);
  myServo.write(0);

  connectWiFi();
}


// ===== LOOP =====
void loop() {

  if (!messageApprocheAffiche && !traitementEnCours) {
    lcdApproche();
    messageApprocheAffiche = true;
  }

  String uid = readUID();

  if (uid != "") {
    traitementEnCours = true;

    Serial.println("UID : " + uid);

    sendAccessCheck(device_code, uid);

    attendreRetraitCarte();

    traitementEnCours = false;
    messageApprocheAffiche = false;
  }
}