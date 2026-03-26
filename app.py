from flask import Flask, render_template, request
import pandas as pd
import openrouteservice
import re
import os
import requests

app = Flask(__name__)

ORS_KEY = os.environ.get("ORS_KEY")
client = openrouteservice.Client(key=ORS_KEY)

START = "Кривий Ріг, бульв. Вечірній, 35"

# 🔧 Нормалізація адрес
def clean(addr):
    addr = str(addr)

    addr = re.sub(r"\+\d+", "", addr)
    addr = re.sub(r"кв\.\s*\d+", "", addr, flags=re.I)

    replacements = {
        "пр.": "проспект",
        "пл.": "площа",
        "ул.": "вулиця",
    }

    for k, v in replacements.items():
        addr = addr.replace(k, v)

    if "Кривий Ріг" not in addr:
        addr += ", Кривий Ріг"

    return addr.strip()


# 🔥 Геокодинг з fallback
def geocode(address):
    # 1. ORS
    try:
        r = client.pelias_search(text=address)
        return r["features"][0]["geometry"]["coordinates"]
    except:
        pass

    # 2. OSM
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": address, "format": "json"}
        r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()

        if data:
            return [float(data[0]["lon"]), float(data[0]["lat"])]
    except:
        pass

    # 3. спрощення
    try:
        simple = address.split(",")[0]
        return geocode(simple)
    except:
        return None


def optimize(addresses):
    coords = []
    valid = []

    for a in addresses:
        c = geocode(a)
        if c:
            coords.append(c)
            valid.append(a)

    jobs = [{"id": i, "location": c} for i, c in enumerate(coords)]

    route = client.optimization(
        jobs=jobs,
        vehicles=[{
            "id": 1,
            "start": geocode(START),
            "end": geocode(START)
        }]
    )

    order = [s["job"] for s in route["routes"][0]["steps"] if "job" in s]

    return [valid[i] for i in order], [a for a in addresses if a not in valid]


def chunks(lst, n=8):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]


def build_link(points):
    return "https://www.google.com/maps/dir/" + "/".join(points)


@app.route("/", methods=["GET", "POST"])
def index():
    routes = []
    errors = []

    if request.method == "POST":
        f = request.files["file"]
        df = pd.read_csv(f)

        raw = df.iloc[:, 1].tolist()
        cleaned = [clean(a) for a in raw]

        optimized, errors = optimize(cleaned)

        for c in chunks(optimized):
            route = [START] + c + [START]
            routes.append(build_link(route))

    return render_template("index.html", routes=routes, errors=errors)


if __name__ == "__main__":
    app.run()
