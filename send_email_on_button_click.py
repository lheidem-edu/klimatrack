#!/usr/bin/env python
# -*- coding: utf-8 -*-

from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import io
from typing import List, Tuple
import RPi.GPIO as gpio
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import psycopg2
import smtplib
import time

gpio.setmode(gpio.BCM)
gpio.setup(17, gpio.IN, pull_up_down=gpio.PUD_UP)

DATABASE_HOST = "localhost"
DATABASE_NAME = "klimatrack"
DATABASE_USER = "klimatrack"
DATABASE_PASSWORD = "sec"

SMTP_HOST = "mail.lheidem.net"
SMTP_PORT = 465
SMTP_USER = "systemnachricht@lheidem.net"
SMTP_PASSWORD = "random"

SMTP_FROM_ADDRESS = "systemnachricht@lheidem.net"
SMTP_TO_ADDRESS = "kontakt@lheidem.net"

def send_email(subject: str, body: str, temperature_data: List[Tuple[float, str]] = None) -> None:
    """
    Sends an email with the given subject and body.
    If temperature_data is provided, a chart is attached.
    """
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        
        message = MIMEMultipart('related')
        message["From"] = SMTP_FROM_ADDRESS
        message["To"] = SMTP_TO_ADDRESS
        message["Subject"] = subject
        
        if temperature_data:
            current_date = time.strftime('%d.%m.%Y')
            current_time = time.strftime('%H:%M:%S')
            
            temperature_count = len(temperature_data)
            temperatures = [data[0] for data in temperature_data]
            min_temperature = min(temperatures)
            max_temperature = max(temperatures)
            avg_temperature = sum(temperatures) / len(temperatures)
            temperature_variance = sum((x - avg_temperature) ** 2 for x in temperatures) / len(temperatures)
            temperature_stddev = temperature_variance ** 0.5
            temperature_range = max_temperature - min_temperature
            
            html_body = f"""
            <html>
              <head>
                <style>
                  body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333333;
                    max-width: 800px;
                    margin: 0 auto;
                  }}
                  .header {{
                    background-color: #0078D7;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                  }}
                  .content {{
                    padding: 20px;
                    background-color: #f9f9f9;
                    border: 1px solid #dddddd;
                  }}
                  .chart-container {{
                    margin: 20px 0;
                    text-align: center;
                  }}
                  table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                  }}
                  th, td {{
                    text-align: left;
                    padding: 12px 15px;
                    border-bottom: 1px solid #dddddd;
                  }}
                  th {{
                    background-color: #f2f2f2;
                  }}
                  .footer {{
                    font-size: 12px;
                    color: #777777;
                    text-align: center;
                    margin-top: 20px;
                    padding-top: 10px;
                    border-top: 1px solid #dddddd;
                  }}
                </style>
              </head>
              <body>
                <div class="header">
                  <h1>Temperaturbericht</h1>
                  <p>Automatisch generiert am {current_date} um {current_time}</p>
                </div>
                <div class="content">
                  <p>Hallo Luca,</p>
                  <p>hier ist ein Überblick der Temperaturdaten der letzten 24 Stunden:</p>
                  
                  <table>
                    <tr>
                      <th>Kennzahl</th>
                      <th>Wert</th>
                    </tr>
                    <tr>
                      <td>Anzahl der Aufzeichnungen</td>
                      <td>{temperature_count}</td>
                    </tr>
                    <tr>
                      <td>Minimaltemperatur</td>
                      <td><strong>{min_temperature:.2f} °C</strong></td>
                    </tr>
                    <tr>
                      <td>Maximaltemperatur</td>
                      <td><strong>{max_temperature:.2f} °C</strong></td>
                    </tr>
                    <tr>
                      <td>Durchschnittstemperatur</td>
                      <td><strong>{avg_temperature:.2f} °C</strong></td>
                    </tr>
                    <tr>
                      <td>Standardabweichung</td>
                      <td>{temperature_stddev:.2f} °C</td>
                    </tr>
                    <tr>
                      <td>Temperaturbereich</td>
                      <td>{temperature_range:.2f} °C</td>
                    </tr>
                  </table>
                  
                  <div class="chart-container">
                    <h2>Grafische Darstellung</h2>
                    <img src="cid:temperature_chart" width="100%" alt="Temperaturverlauf der letzten 24 Stunden" style="max-width:800px; border:1px solid #ddd; border-radius:4px;">
                  </div>
                  
                  <p>Mit freundlichen Grüßen,<br>
                  Temperatur-Sensor</p>
                </div>
                <div class="footer">
                  <p>Diese E-Mail wurde automatisch generiert. Bitte antworten Sie nicht auf diese Nachricht.</p>
                </div>
              </body>
            </html>
            """
            
            plain_text = f"""
Temperaturbericht
Generiert am {current_date} um {current_time}

Hallo Luca,

hier ist ein Überblick der Temperaturdaten der letzten 24 Stunden:

TEMPERATUR-KENNZAHLEN:
- Anzahl der Aufzeichnungen: {temperature_count}
- Minimaltemperatur: {min_temperature:.2f} °C
- Maximaltemperatur: {max_temperature:.2f} °C
- Durchschnittstemperatur: {avg_temperature:.2f} °C
- Standardabweichung: {temperature_stddev:.2f} °C
- Temperaturbereich: {temperature_range:.2f} °C

Eine grafische Darstellung des Temperaturverlaufs ist im HTML-Format dieser E-Mail enthalten.

Mit freundlichen Grüßen,
Temperatur-Sensor

---
Diese E-Mail wurde automatisch generiert. Bitte antworten Sie nicht auf diese Nachricht.
            """.strip()
            
            alt = MIMEMultipart('alternative')
            alt.attach(MIMEText(plain_text, 'plain', 'utf-8'))
            alt.attach(MIMEText(html_body, 'html', 'utf-8'))
            message.attach(alt)
            
            chart_data = create_temperature_chart(temperature_data)
            img = MIMEImage(chart_data)
            img.add_header('Content-ID', '<temperature_chart>')
            img.add_header('Content-Disposition', 'inline', filename='temperature_chart.png')
            message.attach(img)
        else:
            message.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server.send_message(message)
        
def get_temperature_records_with_timestamps() -> List[Tuple[float, str]]:
    """
    Retrieves all temperature records from the database for the last 24 hours.
    Returns a list of tuples containing the timestamp and temperature value.
    """
    connection = psycopg2.connect(
        host=DATABASE_HOST,
        database=DATABASE_NAME,
        user=DATABASE_USER,
        password=DATABASE_PASSWORD
    )
    cursor = connection.cursor()
    
    cursor.execute("SELECT aufzeichnung_wert, aufzeichnung_zeitpunkt FROM temperatur_aufzeichnungen WHERE aufzeichnung_zeitpunkt >= NOW() - INTERVAL '24 hours'")
    records = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return [(record[0], record[1]) for record in records]

def create_temperature_chart(temperature_data: List[Tuple[float, str]]) -> bytes:
    """
    Creates a professional temperature chart from the given data and returns it as bytes.
    """
    temperatures = [data[0] for data in temperature_data]
    timestamps = [data[1] for data in temperature_data]
    
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, temperatures, marker='o', linestyle='-', color='#0078D7', linewidth=2)

    plt.fill_between(timestamps, temperatures, alpha=0.2, color='#0078D7')
    
    plt.grid(True, linestyle='--', alpha=0.7, color='#cccccc')
    plt.title('Temperaturverlauf der letzten 24 Stunden', fontsize=16, pad=20)
    plt.ylabel('Temperatur (°C)', fontsize=12)
    plt.xlabel('Zeitpunkt', fontsize=12)
    
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.xticks(rotation=45)
    
    min_temp = min(temperatures)
    max_temp = max(temperatures)
    min_idx = temperatures.index(min_temp)
    max_idx = temperatures.index(max_temp)
    
    plt.annotate(f"{min_temp:.1f}°C", 
                 xy=(timestamps[min_idx], min_temp),
                 xytext=(10, -15),
                 textcoords="offset points",
                 bbox=dict(boxstyle="round,pad=0.3", fc="blue", alpha=0.3))
                 
    plt.annotate(f"{max_temp:.1f}°C", 
                 xy=(timestamps[max_idx], max_temp),
                 xytext=(10, 10),
                 textcoords="offset points",
                 bbox=dict(boxstyle="round,pad=0.3", fc="red", alpha=0.3))
    
    plt.tight_layout()
    
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=100, bbox_inches='tight')
    img_buf.seek(0)
    
    plt.close()
    return img_buf.getvalue()

def main() -> None:
    """
    Main function that runs the program.
    """
    try:
        print("E-Mail-Dienst gestartet. Warte auf Button-Klick...")
        while True:
            button_state = gpio.input(17)
            if button_state == gpio.LOW:
                print("Button gedrückt. Verarbeite Temperaturaufzeichnungen...")
                
                temperature_records_with_timestamps = get_temperature_records_with_timestamps()
                
                if temperature_records_with_timestamps:
                    print(f"Daten gefunden. Sende E-Mail mit {len(temperature_records_with_timestamps)} Temperaturwerten...")
                    
                    subject = "Temperaturbericht"
                    body = "Diese E-Mail sollte im HTML-Format angezeigt werden."
                    
                    send_email(subject, body, temperature_records_with_timestamps)
                    print("E-Mail erfolgreich gesendet!")
                else:
                    print("Keine Temperaturdaten für die letzten 24 Stunden gefunden!")
                    
                time.sleep(60)  # Warte 60 Sekunden, bevor erneut geprüft wird
                
    except KeyboardInterrupt:
        print("Programm wurde manuell beendet.")
    except Exception as ex:
        print(f"Fehler beim Senden der E-Mail: {ex}")
    finally:
        gpio.cleanup()
        
if __name__ == "__main__":
    main()
