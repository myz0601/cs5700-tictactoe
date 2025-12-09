# dashboard.py
from flask import Flask, render_template_string
import json
import os
from datetime import datetime

STATS_FILE = "stats.json"
LOG_FILE = "server.log"

app = Flask(__name__)

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def load_logs(max_lines=100):
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-max_lines:]
    except Exception:
        return []

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Tic-Tac-Toe Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2 { margin-bottom: 0.3em; }
        table { border-collapse: collapse; margin-bottom: 20px; }
        th, td {
            border: 1px solid #ccc;
            padding: 8px 12px;
            text-align: center;
        }
        th { background: #f0f0f0; }
        .log-box {
            border: 1px solid #ccc;
            padding: 8px;
            max-height: 400px;
            overflow-y: scroll;
            white-space: pre-wrap;
            background: #fafafa;
        }
        .timestamp {
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <h1>Network Tic-Tac-Toe Dashboard</h1>
    <p class="timestamp">Last refresh: {{ now }}</p>

    <h2>Player Stats</h2>
    {% if stats %}
    <table>
        <tr>
            <th>Player</th>
            <th>Wins</th>
            <th>Losses</th>
            <th>Draws</th>
        </tr>
        {% for name, s in stats.items() %}
        <tr>
            <td>{{ name }}</td>
            <td>{{ s.wins }}</td>
            <td>{{ s.losses }}</td>
            <td>{{ s.draws }}</td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <p>No stats yet.</p>
    {% endif %}

    <h2>Server Logs (latest)</h2>
    {% if logs %}
    <div class="log-box">
        {% for line in logs %}
        {{ line }}
        {% endfor %}
    </div>
    {% else %}
    <p>No logs yet.</p>
    {% endif %}
</body>
</html>
"""

@app.route("/")
def index():
    raw_stats = load_stats()
    # 转成对象，模板里好访问
    stats = {
        name: type("S", (), s) for name, s in raw_stats.items()
    }
    logs = load_logs()
    return render_template_string(
        TEMPLATE,
        stats=stats,
        logs=logs,
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

if __name__ == "__main__":
    # 默认在 http://127.0.0.1:5000
    app.run(debug=True)
