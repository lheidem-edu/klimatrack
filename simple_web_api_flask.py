#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
import io
import time
from typing import List, Tuple
import psycopg2

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from flask import Flask, jsonify, render_template_string
from flask_cors import CORS

DATABASE_HOST = "localhost"
DATABASE_NAME = "klimatrack"
DATABASE_USER = "klimatrack"
DATABASE_PASSWORD = "sec"

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

app = Flask(__name__)

CORS(app)

@app.route("/api/v1/temperatur_aufzeichnungen", methods=["GET"])
def get_temperature_records() -> str:
    """
    Endpoint to retrieve temperature records for the last 24 hours.
    Returns a JSON response with the temperature records.
    """
    records = get_temperature_records_with_timestamps()
    
    records_list = [{"temperature": record[0], "timestamp": record[1].isoformat()} for record in records]
    
    return jsonify(records_list)

@app.route("/", methods=["GET"])
def root_page():
    """
    Renders a dashboard page with temperature statistics and a chart.
    """
    temperature_data = get_temperature_records_with_timestamps()
    
    if not temperature_data:
        return "Keine Temperaturdaten für die letzten 24 Stunden gefunden."
        
    chart_data = create_temperature_chart(temperature_data)
    encoded_chart = base64.b64encode(chart_data).decode('utf-8')
    chart_src = f"data:image/png;base64,{encoded_chart}"
    
    temperatures = [data[0] for data in temperature_data]
    temperature_count = len(temperature_data)
    min_temperature = min(temperatures)
    max_temperature = max(temperatures)
    avg_temperature = sum(temperatures) / len(temperatures)
    temperature_variance = sum((x - avg_temperature) ** 2 for x in temperatures) / len(temperatures)
    temperature_stddev = temperature_variance ** 0.5
    temperature_range = max_temperature - min_temperature
    
    current_date = time.strftime('%d.%m.%Y')
    current_time = time.strftime('%H:%M:%S')
    
    template = """
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KlimaTrack Dashboard</title>
        <style>
          body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333333;
            max-width: 800px;
            margin: 0 auto;
            padding: 0;
            background-color: #f0f0f0;
          }
          .header {
            background-color: #0078D7;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
          }
          .content {
            padding: 20px;
            background-color: #f9f9f9;
            border: 1px solid #dddddd;
          }
          .chart-container {
            margin: 20px 0;
            text-align: center;
          }
          table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
          }
          th, td {
            text-align: left;
            padding: 12px 15px;
            border-bottom: 1px solid #dddddd;
          }
          th {
            background-color: #f2f2f2;
          }
          .footer {
            font-size: 12px;
            color: #777777;
            text-align: center;
            margin-top: 20px;
            padding: 10px;
            border-top: 1px solid #dddddd;
          }
          .refresh-button {
            display: inline-block;
            background-color: #0078D7;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 4px;
            margin: 10px 0;
          }
          .refresh-button:hover {
            background-color: #005fa3;
          }
          @media (max-width: 600px) {
            body {
              padding: 10px;
            }
            .header {
              padding: 10px;
            }
            table {
              font-size: 14px;
            }
            th, td {
              padding: 8px 10px;
            }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>Dashboard</h1>
          <p>Temperaturdaten der letzten 24 Stunden</p>
          <p>Stand: {{ current_date }} um {{ current_time }}</p>
        </div>
        <div class="content">
          <a href="/" class="refresh-button">Daten aktualisieren</a>
          
          <table>
            <tr>
              <th>Kennzahl</th>
              <th>Wert</th>
            </tr>
            <tr>
              <td>Anzahl der Aufzeichnungen</td>
              <td>{{ temperature_count }}</td>
            </tr>
            <tr>
              <td>Minimaltemperatur</td>
              <td><strong>{{ "%.2f"|format(min_temperature) }} °C</strong></td>
            </tr>
            <tr>
              <td>Maximaltemperatur</td>
              <td><strong>{{ "%.2f"|format(max_temperature) }} °C</strong></td>
            </tr>
            <tr>
              <td>Durchschnittstemperatur</td>
              <td><strong>{{ "%.2f"|format(avg_temperature) }} °C</strong></td>
            </tr>
            <tr>
              <td>Standardabweichung</td>
              <td>{{ "%.2f"|format(temperature_stddev) }} °C</td>
            </tr>
            <tr>
              <td>Temperaturbereich</td>
              <td>{{ "%.2f"|format(temperature_range) }} °C</td>
            </tr>
          </table>
          
          <div class="chart-container">
            <h2>Grafische Darstellung</h2>
            <img src="{{ chart_src }}" width="100%" alt="Temperaturverlauf der letzten 24 Stunden" style="max-width:800px; border:1px solid #ddd; border-radius:4px;">
          </div>
          
          <p><small>Letzte Messung: {{ last_measurement_time }}</small></p>
        </div>
        <div class="footer">
          <p>&copy; 2025 Luca Heidemann</p>
        </div>
      </body>
    </html>
    """
    
    last_measurement_time = temperature_data[-1][1].strftime('%d.%m.%Y %H:%M:%S') if temperature_data else "Keine Daten"
    
    return render_template_string(
        template,
        temperature_count=temperature_count,
        min_temperature=min_temperature,
        max_temperature=max_temperature,
        avg_temperature=avg_temperature,
        temperature_stddev=temperature_stddev,
        temperature_range=temperature_range,
        current_date=current_date,
        current_time=current_time,
        chart_src=chart_src,
        last_measurement_time=last_measurement_time
    )

def main() -> None:
    """
    Main function to run the Flask application.
    """
    app.run(host="0.0.0.0", port=8080)
    
if __name__ == "__main__":
    main()
