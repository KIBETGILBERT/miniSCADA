# MiniSCADA - Live Dashboard

A real-time SCADA dashboard built with Python + Flask + Postgres + Docker.

Sensor sends temperature and humidity every 2 seconds. Dashboard updates live with NO page reload, smooth animated graph.

Features:
- Live smooth graph
- Temperature + Humidity cards
- Pump control - AUTO / MANUAL
- Auto logic: Pump ON over 30C, OFF under 25C
- High / Low temp alarms
- Postgres storage

How to run:
docker compose up --build -d
python3 sensor.py

Open: http://localhost:5000/readings
