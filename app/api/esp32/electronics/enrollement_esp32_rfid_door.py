#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>

// =======================
// Configuration Wi-Fi
// =======================
const char* WIFI_SSID = "OPPO";
const char* WIFI_PASSWORD = "12345678";

// =======================
// Configuration API
// =======================
const char* API_URL = "https://rfid-door-platform.onrender.com/api/esp32/enrollment/scan";
const char* API_TOKEN = "NCaXVNzgHGl0Ru8q-0CfhoOYaR7KM9oXaxwiestnnGU";

// =======================
// Configuration RFID
// Comme dans ton code
// =======================
#define SS_PIN 5
#define RST_PIN 22

MFRC522 rfid(SS_PIN, RST_PIN);

// =======================
// Données appareil
// =======================
String deviceCode = "";
// default 28443886E694

// =======================
// Anti double scan
// =======================
String lastUid = "";
unsigned long lastScanTime = 0;
const unsigned long cooldown = 2000; // 2 secondes

// =======================
// Récupération Serial ESP32
// Équivalent du serial Raspberry Pi
// =======================
String getEsp32Serial()
{
  uint64_t chipId = ESP.getEfuseMac();

  char serial[17];
  snprintf(
    serial,
    sizeof(serial),
    "%04X%08X",
    (uint16_t)(chipId >> 32),
    (uint32_t)chipId
  );

  return String(serial);
}

// =======================
// Connexion Wi-Fi
// =======================
void connectWifi()
{
  Serial.print("Connexion au WiFi");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connecté");
  Serial.print("Adresse IP ESP32 : ");
  Serial.println(WiFi.localIP());
}

// =======================
// Envoi UID vers API
// =======================
bool sendUidToApi(String uidHex)
{
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi déconnecté. Reconnexion...");
    connectWifi();
  }

  HTTPClient http;
  http.begin(API_URL);

  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Token", API_TOKEN);

  StaticJsonDocument<200> requestDoc;
  requestDoc["device_code"] = deviceCode;
  requestDoc["uid"] = uidHex;

  String requestBody;
  serializeJson(requestDoc, requestBody);

  Serial.println("Payload JSON :");
  Serial.println(requestBody);

  int httpResponseCode = http.POST(requestBody);

  Serial.print("Code HTTP : ");
  Serial.println(httpResponseCode);

  if (httpResponseCode <= 0) {
    Serial.print("Erreur HTTP : ");
    Serial.println(http.errorToString(httpResponseCode));
    http.end();
    return false;
  }

  String response = http.getString();

  Serial.println("Réponse brute :");
  Serial.println(response);

  StaticJsonDocument<512> responseDoc;
  DeserializationError error = deserializeJson(responseDoc, response);

  if (error) {
    Serial.print("Réponse non JSON : ");
    Serial.println(error.c_str());
    http.end();
    return false;
  }

  Serial.println("Réponse JSON reçue.");

  bool success = responseDoc["success"] | false;

  if (success) {
    Serial.println("Scan envoyé avec succès.");
  } else {
    Serial.println("Échec côté serveur.");
  }

  http.end();

  return success;
}

// =======================
// Lecture UID RFID
// =======================
String readUID()
{
  if (!rfid.PICC_IsNewCardPresent()) {
    return "";
  }

  if (!rfid.PICC_ReadCardSerial()) {
    return "";
  }

  Serial.println("Carte détectée");

  Serial.print("UID brut : ");
  for (byte i = 0; i < rfid.uid.size; i++) {
    Serial.print(rfid.uid.uidByte[i], HEX);
    Serial.print(" ");
  }
  Serial.println();

  String uidHex = "";

  // Comme dans ton code Python :
  // on garde seulement les 4 premiers octets utiles
  byte uidLength = rfid.uid.size;

  if (uidLength > 4) {
    uidLength = 4;
  }

  for (byte i = 0; i < uidLength; i++) {
    if (rfid.uid.uidByte[i] < 0x10) {
      uidHex += "0";
    }

    uidHex += String(rfid.uid.uidByte[i], HEX);
  }

  uidHex.toUpperCase();

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  return uidHex;
}

// =======================
// Setup
// =======================
void setup()
{
  Serial.begin(115200);
  delay(1000);

  deviceCode = getEsp32Serial();

  Serial.print("Serial ESP32 : ");
  Serial.println(deviceCode);

  connectWifi();

  SPI.begin();
  rfid.PCD_Init();

  Serial.println("Lecteur RFID initialisé.");
  Serial.println("Approche une carte RFID...");
}

// =======================
// Loop
// =======================
void loop()
{
  String uidHex = readUID();

  if (uidHex != "") {
    unsigned long now = millis();

    if (uidHex == lastUid && (now - lastScanTime) < cooldown) {
      Serial.println("Même carte ignorée temporairement.");
      delay(500);
      return;
    }

    Serial.print("UID utile : ");
    Serial.println(uidHex);

    Serial.println("Envoi au serveur...");

    bool ok = sendUidToApi(uidHex);

    if (ok) {
      Serial.println("Résultat : succès");
    } else {
      Serial.println("Résultat : échec");
    }

    Serial.println("----------------------");

    lastUid = uidHex;
    lastScanTime = now;

    delay(1000);
  }

  delay(100);
}