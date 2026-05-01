
// #include <WiFi.h>
// #include <HTTPClient.h>
// #include <ArduinoJson.h>
// #include <SPI.h>
// #include <MFRC522.h>
// #include <ESP32Servo.h>

// // ======== WIFI ========
// const char* WIFI_SSID = "OPPO";
// const char* WIFI_PASSWORD = "12345678";

// // ======== API ========
// const char* API_URL = "https://rfid-door-platform.onrender.com/api/esp32/access/check";
// const char* BEARER_TOKEN = "q34y0ylyq4Ad3viJQRtYPmjjRmVyrI9OA45E3q1mLhU";
// #define BUZZER_PIN 13
// // ======== RFID ========
// #define SS_PIN 5
// #define RST_PIN 22
// MFRC522 rfid(SS_PIN, RST_PIN);

// // ======== SERVO ========
// #define SERVO_PIN 12
// Servo myServo;

// // ======== DONNEES ========
// String device_code = "ESP01";

// // ======== LOGIQUE ANTI-BOUCLE ========
// bool messageApprocheAffiche = false;
// bool traitementEnCours = false;


// // ===== WIFI =====
// void connectWiFi() {
//   Serial.print("Connexion au WiFi");
//   WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

//   while (WiFi.status() != WL_CONNECTED) {
//     delay(500);
//     Serial.print(".");
//   }

//   Serial.println();
//   Serial.println("WiFi connecté");
//   Serial.print("IP ESP32: ");
//   Serial.println(WiFi.localIP());
// }


// // ===== ENVOI API =====
// void sendAccessCheck(String deviceCode, String rfidUid) {

//   if (WiFi.status() != WL_CONNECTED) {
//     Serial.println("WiFi non connecté");
//     bipErreur();
//     return;
//   }

//   HTTPClient http;
//   http.begin(API_URL);

//   // Headers
//   http.addHeader("Content-Type", "application/json");
//   http.addHeader("Authorization", "Bearer " + String(BEARER_TOKEN));

//   // JSON
//   StaticJsonDocument<200> requestDoc;
//   requestDoc["device_code"] = deviceCode;
//   requestDoc["uid"] = rfidUid;

//   String requestBody;
//   serializeJson(requestDoc, requestBody);

//   Serial.println("Envoi requête :");
//   Serial.println(requestBody);

//   int httpResponseCode = http.POST(requestBody);

//   if (httpResponseCode > 0) {

//     String response = http.getString();

//     Serial.print("Code HTTP: ");
//     Serial.println(httpResponseCode);

//     Serial.println("Réponse serveur:");
//     Serial.println(response);

//     // ===== PARSER JSON =====
//     StaticJsonDocument<300> responseDoc;
//     DeserializationError error = deserializeJson(responseDoc, response);

//     if (error) {
//       Serial.println("Erreur parsing JSON");
//       bipErreur();
//       http.end();
//       return;
//     }

//     String decision = responseDoc["decision"];
//     bool doorOpened = responseDoc["door_opened"];
//     String reason = responseDoc["reason"];

//     Serial.print("Decision: ");
//     Serial.println(decision);

//     Serial.print("Door opened: ");
//     Serial.println(doorOpened);

//     Serial.print("Reason: ");
//     Serial.println(reason);

//     // ===== ACTION =====
//     if (decision == "granted" && doorOpened == true) {
//       bipSucces();
//       openDoor();
//     } else {
//       Serial.println("Accès refusé");
//       bipErreur();
//     }

//   } else {
//     Serial.print("Erreur HTTP: ");
//     bipErreur();
//     Serial.println(httpResponseCode);
//   }

//   http.end();
// }


// // ===== RFID =====
// String readUID() {

//   if (!rfid.PICC_IsNewCardPresent()) return "";
//   if (!rfid.PICC_ReadCardSerial()) return "";

//   String uid = "";

//   for (byte i = 0; i < rfid.uid.size; i++) {
//     uid += String(rfid.uid.uidByte[i], HEX);
//   }

//   uid.toLowerCase();

//   rfid.PICC_HaltA();
//   rfid.PCD_StopCrypto1();

//   return uid;
// }


// // ===== ATTENDRE QUE LA CARTE SOIT RETIREE =====
// void attendreRetraitCarte() {
//   Serial.println("Retire la carte rfid");

//   while (true) {
//     byte bufferATQA[2];
//     byte bufferSize = sizeof(bufferATQA);

//     MFRC522::StatusCode status = rfid.PICC_WakeupA(bufferATQA, &bufferSize);

//     if (status != MFRC522::STATUS_OK) {
//       break;
//     }

//     rfid.PICC_HaltA();
//     rfid.PCD_StopCrypto1();

//     delay(300);
//   }

//   delay(500);
// }


// // ===== PORTE =====
// void openDoor() {
//   Serial.println("Ouverture porte");
//   myServo.write(90);
//   delay(3000);
//   myServo.write(0);
// }

// // ===== BUZZER : UN SEUL BIP =====
// void bipSucces() {
//   digitalWrite(BUZZER_PIN, HIGH);
//   delay(150);
//   digitalWrite(BUZZER_PIN, LOW);
// }
// //Saisir, Message envoyé à 17:45 par Jacob : // ===== BUZZER : UN SEUL BIP ===== void bipSimple() { digitalWrite(BUZZER_PIN, HIGH); delay(150); digitalWrite(BUZZER_PIN, LOW); }
// // ===== BUZZER : ERREUR 3 BIPS =====
// void bipErreur() {
//   for (int i = 0; i < 3; i++) {
//     digitalWrite(BUZZER_PIN, HIGH);
//     delay(200);
//     digitalWrite(BUZZER_PIN, LOW);
//     delay(100);
//   }
// }
// // ===== SETUP =====
// void setup() {
//   Serial.begin(115200);
//   pinMode(BUZZER_PIN, OUTPUT);
//   digitalWrite(BUZZER_PIN, LOW);
//   SPI.begin();
//   rfid.PCD_Init();

//   myServo.attach(SERVO_PIN);
//   myServo.write(0);

//   connectWiFi();
  
// }


// // ===== LOOP =====
// void loop() {

//   if (!messageApprocheAffiche && !traitementEnCours) {
//     Serial.println("Approche une carte rfid : ");
//     messageApprocheAffiche = true;
//   }

//   String uid = readUID();

//   if (uid != "") {
//     traitementEnCours = true;

//     Serial.println("UID scanné : " + uid);

//     sendAccessCheck(device_code, uid);

//     attendreRetraitCarte();

//     traitementEnCours = false;
//     messageApprocheAffiche = false;
//   }
// }