import os
import time
import random
import psycopg2
from dotenv import load_dotenv
load_dotenv()

#connect to the database
conn = psycopg2.connect(
   host=os.getenv("DB_HOST", "localhost"),
   dbname=os.getenv("POSTGRES_DB"),
   user=os.getenv("POSTGRES_USER"),
   password=os.getenv("POSTGRES_PASSWORD"),
)

cur = conn.cursor()

# Create table if it doesn't exist
cur.execute("""
    CREATE TABLE IF NOT EXISTS readings (
        id SERIAL PRIMARY KEY,
        sensor VARCHAR(50),
        value FLOAT,
        created_at TIMESTAMP DEFAULT NOW()
    );
""")
conn.commit()

# Fake sensor loop
print("Sensor started... sending data every 5 seconds")
while True:
    temp = random.uniform(20, 35)
    hum = random.uniform(40, 70)
    cur.execute("INSERT INTO readings (sensor, value) VALUES (%s, %s)", ("temperature", temp))
    cur.execute("INSERT INTO readings (sensor, value) VALUES (%s, %s)", ("humidity", hum))
    conn.commit()
    print(f"Saved: {temp:.2f}°C | Humidity: {hum:.1f}%")
    time.sleep(2)