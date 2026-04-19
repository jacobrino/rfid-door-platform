#!/usr/bin/env python3

import time
import requests
import RPi.GPIO as GPIO
from mfrc522 import MFRC522

API_URL = "http://192.168.0.250:8000/api/esp32/enrollment/scan"
API_TOKEN = "NCaXVNzgHGl0Ru8q-0CfhoOYaR7KM9oXaxwiestnnGU"



#Serial		: 00000000ecd41059
def get_raspberry_serial():
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Serial"):
                    return line.strip().split(":")[1].strip()
    except Exception:
        return None

serial = get_raspberry_serial()
print("Serial Raspberry Pi :", serial)


GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

reader = MFRC522()

print("Approche une carte RFID...")

def send_uid_to_api(uid_hex):
    payload = {
        "device_code": serial,
        "uid": uid_hex
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Token": API_TOKEN
    }

    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        print(f"Code HTTP : {response.status_code}")

        try:
            data = response.json()
        except ValueError:
            print("Réponse non JSON :", response.text)
            return False

        print("Réponse JSON :", data)

        success = data.get("success", False)

        if success:
            print("Scan envoyé avec succès.")
        else:
            print("Échec côté serveur.")

        return success

    except requests.RequestException as e:
        print("Erreur HTTP :", e)
        return False


try:
    last_uid = None
    last_scan_time = 0
    cooldown = 2  # secondes anti double scan

    while True:
        status, tag_type = reader.MFRC522_Request(reader.PICC_REQIDL)

        if status == reader.MI_OK:
            print("Carte détectée")

            status, uid = reader.MFRC522_Anticoll()

            if status == reader.MI_OK:
                print("UID brut :", uid)

                # On enlève le dernier octet (BCC)
                uid_clean = uid[:4]
                uid_hex = "".join(f"{x:02X}" for x in uid_clean)

                now = time.time()

                if uid_hex == last_uid and (now - last_scan_time) < cooldown:
                    print("Même carte ignorée temporairement.")
                    time.sleep(0.5)
                    continue

                print("UID utile :", uid_hex)
                print("Envoi au serveur...")

                ok = send_uid_to_api(uid_hex)

                if ok:
                    print("Résultat : succès")
                else:
                    print("Résultat : échec")

                print("----------------------")

                last_uid = uid_hex
                last_scan_time = now
                time.sleep(1)

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nArrêt.")

finally:
    GPIO.cleanup()