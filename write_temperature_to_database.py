#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import psycopg2
import time
import uuid

W1_DEVICES_PATH = "/sys/bus/w1/devices/"

DATABASE_HOST = "localhost"
DATABASE_NAME = "klimatrack"
DATABASE_USER = "klimatrack"
DATABASE_PASSWORD = "sec"

def read_temperature() -> float:
    """
    Reads the temperature from the DS18B20 sensor.
    Returns the temperature in Celsius.
    """
    sensor_file = glob.glob(W1_DEVICES_PATH + "28*")[0] + "/w1_slave"
    
    with open(sensor_file, "r") as file:
        lines = file.readlines()
        
    if not lines:
        raise RuntimeError("Der Sensor konnte nicht gefunden werden.")
    
    if "YES" not in lines[0]:
        raise RuntimeError("Der Sensor ist nicht bereit.")
    
    temperature_data = lines[1].split("t=")[-1]
    temperature = float(temperature_data) / 1000.0
    
    return temperature

def save_to_database(temperature: float) -> None:
    """
    Saves the temperature to a PostgreSQL database.
    """
    connection = psycopg2.connect(
        host=DATABASE_HOST,
        database=DATABASE_NAME,
        user=DATABASE_USER,
        password=DATABASE_PASSWORD
    )
    cursor = connection.cursor()
    
    cursor.execute("INSERT INTO temperatur_aufzeichnungen (aufzeichnung_id, aufzeichnung_wert, aufzeichnung_zeitpunkt) VALUES (%s, %s, NOW())", (str(uuid.uuid4()), temperature))
    connection.commit()
    
    cursor.close()
    connection.close()
    
def main() -> None:
    """
    Every 5 seconds, it reads the temperature and saves it to the database.
    """
    while True:
        try:
            while True:
                temperature = read_temperature()
                save_to_database(temperature)
                time.sleep(5)
        except KeyboardInterrupt:
            pass
        except Exception as ex:
                print(f"Fehler beim Lesen der Temperatur oder Speichern in der Datenbank: {ex}")
    
if __name__ == "__main__":
    main()
