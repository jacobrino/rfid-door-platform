// #include <WiFi.h>
// #include <HTTPClient.h>
// #include <ArduinoJson.h>

// const char* WIFI_SSID = "VOTRE_WIFI";
// const char* WIFI_PASSWORD = "VOTRE_MDP_WIFI";

// const char* SERVER_URL = "http://192.168.1.50:8000/api/esp32/access/echo";
// const char* DEVICE_CODE = "ESP32_MAIN_DOOR";
// const char* API_TOKEN = "token_main_door_123";

// // const int LED_GREEN_PIN = 2; // Exemple si tu veux plus tard piloter une LED

// unsigned long lastEchoAt = 0;
// const unsigned long ECHO_INTERVAL_MS = 10000; // toutes les 10 secondes

// void setup() {
//   Serial.begin(115200);

//   // pinMode(LED_GREEN_PIN, OUTPUT);
//   // digitalWrite(LED_GREEN_PIN, LOW);

//   WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
//   Serial.print("Connexion WiFi");

//   while (WiFi.status() != WL_CONNECTED) {
//     delay(500);
//     Serial.print(".");
//   }

//   Serial.println();
//   Serial.println("WiFi connecté");
// }

// void loop() {
//   unsigned long now = millis();

//   if (now - lastEchoAt >= ECHO_INTERVAL_MS) {
//     lastEchoAt = now;
//     sendEcho();
//   }
// }

// void sendEcho() {
//   if (WiFi.status() != WL_CONNECTED) {
//     Serial.println("WiFi non connecté");
//     // digitalWrite(LED_GREEN_PIN, LOW);
//     return;
//   }

//   HTTPClient http;
//   http.begin(SERVER_URL);
//   http.addHeader("Content-Type", "application/json");
//   http.addHeader("X-API-Token", API_TOKEN);

//   String payload = String("{\"device_code\":\"") + DEVICE_CODE + "\"}";

//   int httpCode = http.POST(payload);

//   if (httpCode > 0) {
//     String response = http.getString();
//     Serial.println("Réponse serveur :");
//     Serial.println(response);

//     if (httpCode == 200) {
//       // digitalWrite(LED_GREEN_PIN, HIGH); // LED verte ON si echo OK
//     } else {
//       // digitalWrite(LED_GREEN_PIN, LOW);  // LED OFF si serveur répond erreur
//     }
//   } else {
//     Serial.print("Erreur HTTP: ");
//     Serial.println(http.errorToString(httpCode));
//     // digitalWrite(LED_GREEN_PIN, LOW); // LED OFF si échec de communication
//   }

//   http.end();
// }