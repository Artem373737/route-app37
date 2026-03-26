from flask import Flask, render_template, request
import pandas as pd
import re
import requests

app = Flask(__name__)

START = "Кривий Ріг, бульв. Вечірній, 35"

def clean(addr):
    addr = str(addr)
    addr = re.sub(r"\+\d+", "", addr)
    addr = re.sub(r"кв\.\s*\d+", "", addr, flags=re.I)

    if "Кривий Ріг" not in addr:
        addr += ", Кривий Ріг"

    return addr.strip()


def geocode(address):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": address, "format": "json"}

        r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()

        if data:
            return [float(data[0]["lon"]), float(data[0]["lat"])]
    except:
        return None


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

        valid = []
        for a in cleaned:
            if geocode(a):
                valid.append(a)
            else:
                errors.append(a)

        for c in chunks(valid):
            route = [START] + c + [START]
            routes.append(build_link(route))

    return render_template("index.html", routes=routes, errors=errors)


if __name__ == "__main__":
    app.run()
