import os
from flask import Flask, redirect, jsonify
import psycopg2

app = Flask(__name__)

def get_db():
    return psycopg2.connect(
        host="db",
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD"),
        dbname=os.environ.get("POSTGRES_DB")
    )

def get_latest(sensor_name):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT value, created_at FROM readings WHERE sensor=%s ORDER BY id DESC LIMIT 1;", (sensor_name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def get_pump():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pump (id INT PRIMARY KEY, state TEXT, mode TEXT DEFAULT 'AUTO', updated_at TIMESTAMP DEFAULT NOW());")
    cur.execute("ALTER TABLE pump ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'AUTO';")
    conn.commit()
    cur.execute("INSERT INTO pump (id, state, mode) VALUES (1, 'OFF', 'AUTO') ON CONFLICT (id) DO NOTHING;")
    conn.commit()
    cur.execute("SELECT state, mode FROM pump WHERE id=1;")
    state, mode = cur.fetchone()
    cur.close()
    conn.close()
    return state, mode

def set_pump(state, mode):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pump (id INT PRIMARY KEY, state TEXT, mode TEXT DEFAULT 'AUTO', updated_at TIMESTAMP DEFAULT NOW());")
    cur.execute("ALTER TABLE pump ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'AUTO';")
    conn.commit()
    cur.execute("UPDATE pump SET state=%s, mode=%s, updated_at=NOW() WHERE id=1;", (state, mode))
    if cur.rowcount == 0:
        cur.execute("INSERT INTO pump (id, state, mode) VALUES (1, %s, %s);", (state, mode))
    conn.commit()
    cur.close()
    conn.close()

@app.route("/")
def home():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS visits (id SERIAL PRIMARY KEY, visited_at TIMESTAMP DEFAULT NOW());")
        cur.execute("INSERT INTO visits DEFAULT VALUES;")
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM visits;")
        count = cur.fetchone()[0]
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        cur.execute("SELECT id, visited_at FROM visits ORDER BY id DESC LIMIT 5;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        history = "".join([f"<li>Visit #{r[0]} at {r[1]}</li>" for r in rows])
        return f"""
        <h1>Kibet's Cloud Lab is Live!</h1>
        <p>Web: OK | DB: OK ✅</p>
        <p><b>You are visitor number: {count}</b></p>
        <p>Postgres: {version}</p>
        <h3>Last 5 visits:</h3>
        <ul>{history}</ul>
        <p><a href="/readings">Go to MiniSCADA Dashboard -></a></p>
        <p>Built on Ubuntu + Docker + Postgres + Python</p>
        """
    except Exception as e:
        return f"<h1>DB FAILED</h1><p>{e}</p>"

@app.route("/api/history")
def api_history():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT value, created_at FROM readings WHERE sensor='temperature' ORDER BY id DESC LIMIT 40;")
    temp_rows = cur.fetchall()[::-1]
    cur.execute("SELECT value, created_at FROM readings WHERE sensor='humidity' ORDER BY id DESC LIMIT 40;")
    hum_rows = cur.fetchall()[::-1]
    cur.close()
    conn.close()
    labels = [r[1].strftime("%H:%M:%S") for r in temp_rows]
    temps = [round(r[0], 2) for r in temp_rows]
    hums = [round(r[0], 1) for r in hum_rows]
    return jsonify({"labels": labels, "temps": temps, "hums": hums})

@app.route("/api/live")
def api_live():
    temp_row = get_latest("temperature")
    hum_row = get_latest("humidity")
    pump_state, pump_mode = get_pump()
    if not temp_row:
        return jsonify({"error": "no data"})
    temp = temp_row[0]
    hum = hum_row[0] if hum_row else 0
    if pump_mode == "AUTO":
        if temp > 30 and pump_state != "ON":
            set_pump("ON", "AUTO")
            pump_state = "ON"
        elif temp < 25 and pump_state != "OFF":
            set_pump("OFF", "AUTO")
            pump_state = "OFF"
    if temp > 30:
        status = "⚠️ HIGH TEMP ALARM"
        color = "#ff4444"
        bg = "#ffe0e0"
    elif temp < 20:
        status = "❄️ LOW TEMP ALARM"
        color = "#4488ff"
        bg = "#e0f0ff"
    else:
        status = "✅ NORMAL"
        color = "#22aa55"
        bg = "#e0ffe0"
    return jsonify({
        "temp": round(temp, 2),
        "hum": round(hum, 1),
        "time": temp_row[1].strftime("%H:%M:%S"),
        "full_time": str(temp_row[1]),
        "pump_state": pump_state,
        "pump_mode": pump_mode,
        "status": status,
        "color": color,
        "bg": bg
    })

@app.route("/readings")
def readings():
    try:
        temp_row = get_latest("temperature")
        hum_row = get_latest("humidity")
        pump_state, pump_mode = get_pump()
        if not temp_row:
            return "<h1>No readings yet - start sensor.py</h1>"
        temp = temp_row[0]
        latest_time = temp_row[1]
        hum = hum_row[0] if hum_row else 0

        if temp > 30:
            status = "⚠️ HIGH TEMP ALARM"
            color = "#ff4444"
            bg = "#ffe0e0"
        elif temp < 20:
            status = "❄️ LOW TEMP ALARM"
            color = "#4488ff"
            bg = "#e0f0ff"
        else:
            status = "✅ NORMAL"
            color = "#22aa55"
            bg = "#e0ffe0"

        pump_color = "#22aa55" if pump_state == "ON" else "#888888"

        return f"""
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <body id="mainBody" style="background:{bg}; font-family: Arial; text-align:center;">
        <h1>MiniSCADA - Live Dashboard</h1>
        <div style="display:flex; justify-content:center; gap:15px; flex-wrap:wrap; margin:20px;">
            <div id="tempCard" style="background:{color}; color:white; padding:20px; border-radius:15px; width:260px; transition: background 0.5s;">
                <h3>TEMPERATURE</h3>
                <h2 id="tempVal" style="font-size:50px; margin:0;">{temp:.2f} °C</h2>
                <h3 id="statusText">{status}</h3>
                <p>Sensor: temperature | Last update: <span id="timeVal">{latest_time}</span></p>
            </div>
            <div style="background:#333; color:white; padding:20px; border-radius:15px; width:260px;">
                <h3>HUMIDITY</h3>
                <h2 id="humVal" style="font-size:50px; margin:0;">{hum:.1f} %</h2>
                <p>Sensor: humidity</p>
            </div>
            <div id="pumpCard" style="background:{pump_color}; color:white; padding:20px; border-radius:15px; width:260px; transition: background 0.5s;">
                <h3>PUMP 1 - <span id="pumpMode">{pump_mode}</span></h3>
                <h2 id="pumpState" style="font-size:50px; margin:0;">{pump_state}</h2>
                <p>Mode: <span id="pumpMode2">{pump_mode}</span> | Auto: ON &gt;30°C, OFF &lt;25°C</p>
                <a id="pumpBtn" href="/pump/OFF" style="background:white; color:black; padding:10px 20px; border-radius:10px; text-decoration:none; font-weight:bold; display:inline-block; margin-top:10px;">START Pump ▶️</a><br><br>
                <a id="modeBtn" href="/pump/MANUAL" style="background:#222; color:white; padding:8px 15px; border-radius:10px; text-decoration:none; display:inline-block;">Switch to MANUAL</a>
            </div>
        </div>

        <div style="background:white; max-width:900px; margin:20px auto; padding:20px; border-radius:15px;">
            <h3>📈 Live Graph - Last 40 Readings</h3>
            <canvas id="myChart" height="120"></canvas>
        </div>
        <script>
        let myChart = null;
        fetch('/api/history').then(r => r.json()).then(data => {{
            myChart = new Chart(document.getElementById('myChart'), {{
                type: 'line',
                data: {{
                    labels: data.labels,
                    datasets: [
                        {{ label: 'Temperature (°C)', data: data.temps, borderColor: '#ff4444', backgroundColor: 'rgba(255,68,68,0.1)', tension: 0.6, borderWidth: 2.5, pointRadius: 0, pointHoverRadius: 5, fill: true, cubicInterpolationMode: 'monotone' }},
                        {{ label: 'Humidity (%)', data: data.hums, borderColor: '#22aa55', backgroundColor: 'rgba(34,170,85,0.1)', tension: 0.6, borderWidth: 2.5, pointRadius: 0, pointHoverRadius: 5, fill: true, cubicInterpolationMode: 'monotone' }}
                    ]
                }},
                options: {{
                    responsive: true,
                    animation: {{ duration: 2000, easing: 'easeInOutQuart' }},
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{ legend: {{ labels: {{ usePointStyle: true }} }} }},
                    scales: {{
                        x: {{ grid: {{ color: 'rgba(0,0,0,0.05)' }} }},
                        y: {{ beginAtZero: false, grid: {{ color: 'rgba(0,0,0,0.05)' }} }}
                    }}
                }}
            }});
        }});

        setInterval(() => {{
            fetch('/api/live').then(r => r.json()).then(d => {{
                if (d.error) return;
                document.getElementById('tempVal').innerText = d.temp.toFixed(2) + ' °C';
                document.getElementById('humVal').innerText = d.hum.toFixed(1) + ' %';
                document.getElementById('statusText').innerText = d.status;
                document.getElementById('timeVal').innerText = d.full_time;
                document.getElementById('tempCard').style.background = d.color;
                document.getElementById('mainBody').style.background = d.bg;
                document.getElementById('pumpState').innerText = d.pump_state;
                document.getElementById('pumpMode').innerText = d.pump_mode;
                document.getElementById('pumpMode2').innerText = d.pump_mode;
                document.getElementById('pumpCard').style.background = d.pump_state === 'ON' ? '#22aa55' : '#888888';
                const pumpBtn = document.getElementById('pumpBtn');
                if (d.pump_state === 'ON') {{
                    pumpBtn.innerText = 'STOP Pump 🛑';
                    pumpBtn.href = '/pump/OFF';
                }} else {{
                    pumpBtn.innerText = 'START Pump ▶️';
                    pumpBtn.href = '/pump/ON';
                }}
                const modeBtn = document.getElementById('modeBtn');
                if (d.pump_mode === 'AUTO') {{
                    modeBtn.innerText = 'Switch to MANUAL';
                    modeBtn.href = '/pump/MANUAL';
                }} else {{
                    modeBtn.innerText = 'Switch to AUTO';
                    modeBtn.href = '/pump/AUTO';
                }}
                if (myChart) {{
                    const lastLabel = myChart.data.labels[myChart.data.labels.length - 1];
                    if (lastLabel !== d.time) {{
                        myChart.data.labels.push(d.time);
                        myChart.data.datasets[0].data.push(d.temp);
                        myChart.data.datasets[1].data.push(d.hum);
                        if (myChart.data.labels.length > 40) {{
                            myChart.data.labels.shift();
                            myChart.data.datasets[0].data.shift();
                            myChart.data.datasets[1].data.shift();
                        }}
                        myChart.update();
                    }}
                }}
            }});
        }}, 2000);
        </script>

        <p>Live updating without reload... ✅</p>
        <p><a href="/">Back to Home</a></p>
        </body>
        """
    except Exception as e:
        return f"<h1>DB FAILED</h1><p>{e}</p>"

@app.route("/pump/<state>")
def set_pump_route(state):
    state = state.upper()
    if state in ["ON", "OFF"]:
        set_pump(state, "MANUAL")
        return redirect("/readings")
    if state == "AUTO":
        current_state, _ = get_pump()
        set_pump(current_state, "AUTO")
        return redirect("/readings")
    if state == "MANUAL":
        current_state, _ = get_pump()
        set_pump(current_state, "MANUAL")
        return redirect("/readings")
    return redirect("/readings")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)