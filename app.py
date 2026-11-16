from functools import wraps
import os
import random
import secrets

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from fpdf import FPDF
import networkx as nx
import osmnx as ox
import pandas as pd
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import safe_join

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))

EXPORT_FOLDER = os.getenv("EXPORT_FOLDER", "exports")
GRAPH_PATH = os.getenv("OSM_GRAPH_PATH", "osm_graph.graphml")
MAX_TRUCK_CAPACITY = int(os.getenv("MAX_TRUCK_CAPACITY", "5000"))
FUEL_MILEAGE_KMPL = float(os.getenv("FUEL_MILEAGE_KMPL", "3.5"))
FUEL_PRICE_INR = float(os.getenv("FUEL_PRICE_INR", "110.0"))
EXPORT_INTERVAL_CYCLES = int(os.getenv("EXPORT_INTERVAL_CYCLES", "60"))

os.makedirs(EXPORT_FOLDER, exist_ok=True)

cycle_data = []
CYCLE_COUNT = 0
last_route = []
latest_bin_status = {}

# Role-based demo credentials (override via environment variables in production)
USERS = {
    os.getenv("ADMIN_USER", "admin"): {
        "password": generate_password_hash(os.getenv("ADMIN_PASSWORD", "adminpass")),
        "role": "admin",
    },
    os.getenv("CITIZEN_USER", "user123"): {
        "password": generate_password_hash(os.getenv("CITIZEN_PASSWORD", "userpass")),
        "role": "user",
    },
}

# Real GPS coordinates (Berhampur Municipal Corporation & key city zones)
LATLNG = {
    "BMC": (19.314258006872173, 84.78260316967018),
    "Khallikote University": (19.3119534, 84.7930920),
    "City Hospital": (19.312835507334853, 84.79347890987734),
    "Railway Station": (19.29686456895169, 84.79734512734125),
    "New Bus Stand": (19.314039157089145, 84.80095372337018),
    "MKCG Hospital": (19.307711234412327, 84.81096706750354),
    "Ganesh Market": (19.316270655567067, 84.77882263871312),
    "Janata City Centre": (19.31051270805593, 84.79141736754872),
    "Kamapalli Square": (19.305504311806992, 84.80572119638434),
    "BISWM": (19.299156676857383, 84.76016757023291),
}

SHORT_LABELS = {
    "MKCG Hospital": "001",
    "BMC": "BMC",
    "Khallikote University": "KU",
    "Railway Station": "RailS",
    "City Hospital": "CityH",
    "New Bus Stand": "NewBS",
    "Ganesh Market": "GMarket",
    "Janata City Centre": "JanataCC",
    "Kamapalli Square": "Kamapalli",
    "BISWM": "BISWM",
}

RAW_POSITIONS = {
    "MKCG Hospital": (252, 592),
    "BMC": (823, 117),
    "Khallikote University": (112, 949),
    "Railway Station": (680, 712),
    "City Hospital": (536, 357),
    "New Bus Stand": (964, 472),
    "Ganesh Market": (397, 236),
    "Janata City Centre": (594, 639),
    "Kamapalli Square": (308, 707),
    "BISWM": (1104, 828),
}
POSITIONS = {k: (x, 1000 - y) for k, (x, y) in RAW_POSITIONS.items()}

PRIORITY_ZONES = {
    "Railway Station": 1,
    "MKCG Hospital": 2,
    "New Bus Stand": 3,
    "City Hospital": 4,
}

MEAN_RATES = {
    "MKCG Hospital": 15,
    "BMC": 8,
    "Khallikote University": 7,
    "Railway Station": 19,
    "City Hospital": 12,
    "New Bus Stand": 11,
    "Ganesh Market": 10,
    "Janata City Centre": 9,
    "Kamapalli Square": 13,
    "BISWM": 6,
}

SHORTEST_PATHS_KM = {
    "MKCG Hospital": {
        "BMC": 2.6,
        "Khallikote University": 2.2,
        "Railway Station": 2.5,
        "City Hospital": 2.8,
        "New Bus Stand": 1.5,
        "Ganesh Market": 4.3,
        "Janata City Centre": 2.7,
        "Kamapalli Square": 0.95,
        "BISWM": 12.1,
    },
    "BMC": {
        "MKCG Hospital": 2.6,
        "Khallikote University": 1.6,
        "Railway Station": 2.4,
        "City Hospital": 1.4,
        "New Bus Stand": 2.5,
        "Ganesh Market": 0.6,
        "Janata City Centre": 1.8,
        "Kamapalli Square": 2.8,
        "BISWM": 8.4,
    },
    "Khallikote University": {
        "MKCG Hospital": 2.2,
        "BMC": 1.6,
        "Railway Station": 1.4,
        "City Hospital": 0.75,
        "New Bus Stand": 1.6,
        "Ganesh Market": 2.3,
        "Janata City Centre": 0.8,
        "Kamapalli Square": 1.3,
        "BISWM": 10.0,
    },
    "Railway Station": {
        "MKCG Hospital": 2.5,
        "BMC": 2.4,
        "Khallikote University": 1.4,
        "City Hospital": 1.5,
        "New Bus Stand": 2.8,
        "Ganesh Market": 2.9,
        "Janata City Centre": 1.6,
        "Kamapalli Square": 1.8,
        "BISWM": 10.5,
    },
    "City Hospital": {
        "MKCG Hospital": 2.8,
        "BMC": 1.4,
        "Khallikote University": 0.75,
        "Railway Station": 1.5,
        "New Bus Stand": 1.3,
        "Ganesh Market": 2.0,
        "Janata City Centre": 0.7,
        "Kamapalli Square": 1.8,
        "BISWM": 10.1,
    },
    "New Bus Stand": {
        "MKCG Hospital": 1.5,
        "BMC": 2.5,
        "Khallikote University": 1.6,
        "Railway Station": 2.8,
        "City Hospital": 1.3,
        "Ganesh Market": 2.9,
        "Janata City Centre": 1.9,
        "Kamapalli Square": 1.5,
        "BISWM": 11.4,
    },
    "Ganesh Market": {
        "MKCG Hospital": 4.3,
        "BMC": 0.6,
        "Khallikote University": 2.3,
        "Railway Station": 2.9,
        "City Hospital": 2.0,
        "New Bus Stand": 2.9,
        "Janata City Centre": 1.7,
        "Kamapalli Square": 3.6,
        "BISWM": 8.1,
    },
    "Janata City Centre": {
        "MKCG Hospital": 2.7,
        "BMC": 1.8,
        "Khallikote University": 0.8,
        "Railway Station": 1.6,
        "City Hospital": 0.7,
        "New Bus Stand": 1.9,
        "Ganesh Market": 1.7,
        "Kamapalli Square": 1.7,
        "BISWM": 9.9,
    },
    "Kamapalli Square": {
        "MKCG Hospital": 0.95,
        "BMC": 2.8,
        "Khallikote University": 1.3,
        "Railway Station": 1.6,
        "City Hospital": 1.8,
        "New Bus Stand": 1.5,
        "Ganesh Market": 3.6,
        "Janata City Centre": 1.7,
        "BISWM": 11.1,
    },
    "BISWM": {
        "MKCG Hospital": 12.1,
        "BMC": 8.4,
        "Khallikote University": 10.0,
        "Railway Station": 10.5,
        "City Hospital": 10.1,
        "New Bus Stand": 11.4,
        "Ganesh Market": 8.1,
        "Janata City Centre": 9.9,
        "Kamapalli Square": 11.1,
    },
}

waste_levels = {node: random.randint(0, 15) for node in POSITIONS}

# Build abstract routing graph
G = nx.Graph()
for u, neighbors in SHORTEST_PATHS_KM.items():
    for v, weight in neighbors.items():
        G.add_edge(u, v, weight=weight)

all_lengths = dict(nx.floyd_warshall(G, weight="weight"))
all_paths = dict(nx.all_pairs_dijkstra_path(G, weight="weight"))

# Lazy-loaded OSMnx road network graph
_ox_graph = None
_ox_load_attempted = False


def get_osm_graph():
    """Load cached OSM road graph or fetch from OpenStreetMap on demand."""
    global _ox_graph, _ox_load_attempted
    if _ox_load_attempted:
        return _ox_graph
    _ox_load_attempted = True

    if os.getenv(
        "DISABLE_OSM_DOWNLOAD", "false"
    ).lower() == "true" and not os.path.exists(GRAPH_PATH):
        return None

    try:
        if os.path.exists(GRAPH_PATH):
            _ox_graph = ox.load_graphml(GRAPH_PATH)
        else:
            center_lat, center_lng = LATLNG["BMC"]
            _ox_graph = ox.graph.graph_from_point(
                (center_lat, center_lng), dist=15000, network_type="drive"
            )
            ox.save_graphml(_ox_graph, GRAPH_PATH)
    except Exception as exc:
        app.logger.warning(
            "OSM graph unavailable, falling back to straight segments: %s", exc
        )
        _ox_graph = None
    return _ox_graph


def login_required(role=None):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                return "Access denied", 403
            return fn(*args, **kwargs)

        return decorated_view

    return wrapper


def get_color(node: str, level: float) -> str:
    if node == "BISWM":
        return "purple"
    if level < 20:
        return "green"
    if level < 70:
        return "yellow"
    return "red"


def smart_greedy_route(start: str, targets: list[str]) -> tuple[list[str], float]:
    """Compute a nearest-neighbor greedy tour through target bins ending at BISWM."""
    total_distance = 0.0
    current = start
    full_path = [start]
    remaining = set(targets)

    while remaining:
        next_node = min(remaining, key=lambda x: all_lengths[current][x])
        total_distance += all_lengths[current][next_node]
        full_path.extend(all_paths[current][next_node][1:])
        current = next_node
        remaining.remove(next_node)

    if current != "BISWM":
        total_distance += all_lengths[current]["BISWM"]
        full_path.extend(all_paths[current]["BISWM"][1:])

    return full_path, total_distance


def get_real_route_coords(route: list[str]) -> list[tuple[float, float]]:
    """Map abstract node hops onto real-world OpenStreetMap road coordinates."""
    if not route or len(route) < 2:
        return []

    ox_graph = get_osm_graph()
    coords = []

    for i in range(len(route) - 1):
        u, v = route[i], route[i + 1]
        if u not in LATLNG or v not in LATLNG:
            continue

        if ox_graph is None:
            segment_coords = [LATLNG[u], LATLNG[v]]
        else:
            try:
                orig_node = ox.distance.nearest_nodes(
                    ox_graph, LATLNG[u][1], LATLNG[u][0]
                )
                dest_node = ox.distance.nearest_nodes(
                    ox_graph, LATLNG[v][1], LATLNG[v][0]
                )
                path = nx.shortest_path(ox_graph, orig_node, dest_node, weight="length")
                segment_coords = [
                    (ox_graph.nodes[n]["y"], ox_graph.nodes[n]["x"]) for n in path
                ]
            except Exception:
                segment_coords = [LATLNG[u], LATLNG[v]]

        if coords and coords[-1] == segment_coords[0]:
            coords.extend(segment_coords[1:])
        else:
            coords.extend(segment_coords)

    return coords


def export_cycle_data() -> None:
    """Append recent cycles to CSV and generate a 10-cycle summary PDF."""
    if not cycle_data:
        return

    df = pd.DataFrame(cycle_data)
    csv_path = os.path.join(EXPORT_FOLDER, "cycle_data.csv")
    pdf_path = os.path.join(EXPORT_FOLDER, "cycle_data.pdf")

    write_header = not os.path.isfile(csv_path)
    df.to_csv(csv_path, mode="a", header=write_header, index=False)

    recent_df = df.tail(10)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt="Smart Waste Cycle Data (Last 10 Cycles)", ln=True, align="C")
    pdf.ln(5)

    col_width = pdf.w / 8
    row_height = 7

    for col in recent_df.columns:
        pdf.cell(col_width, row_height, str(col)[:14], border=1)
    pdf.ln()

    for _, row in recent_df.iterrows():
        for col in recent_df.columns:
            pdf.cell(col_width, row_height, str(row[col])[:16], border=1)
        pdf.ln()

    pdf.output(pdf_path)
    cycle_data.clear()


# --- Web & API Routes ---


@app.route("/")
def index():
    if "user" in session:
        return redirect(
            url_for("dashboard" if session.get("role") == "admin" else "live_map")
        )
    return render_template("homepage.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form.get("userid", "").strip()
        password = request.form.get("password", "")
        user = USERS.get(user_id)
        if user and check_password_hash(user["password"], password):
            session["user"] = user_id
            session["role"] = user["role"]
            return redirect(
                url_for("dashboard" if user["role"] == "admin" else "live_map")
            )
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")


@app.route("/dashboard")
@login_required(role="admin")
def dashboard():
    success_message = session.pop("success", None)
    return render_template("dashboard.html", success=success_message)


@app.route("/live-map")
@login_required(role="user")
def live_map():
    return render_template("moving_truck.html")


@app.route("/moving_truck")
@login_required()
def moving_truck():
    return render_template("moving_truck.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/download/<filetype>")
@login_required(role="admin")
def download_file(filetype: str):
    if filetype not in {"csv", "pdf"}:
        return "Invalid file type", 400

    filepath = safe_join(EXPORT_FOLDER, f"cycle_data.{filetype}")
    if filepath and os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)

    return render_template(
        "dashboard.html", error="Export file not yet generated (runs every 60 cycles)."
    )


@app.route("/map-data")
def map_data():
    real_path = get_real_route_coords(last_route) if last_route else []
    return jsonify(
        {
            "bins": [
                {
                    "name": node,
                    "lat": LATLNG[node][0],
                    "lng": LATLNG[node][1],
                    "status": latest_bin_status.get(node, {}).get("color", "green"),
                }
                for node in LATLNG
            ],
            "route_coords": [{"lat": lat, "lng": lng} for lat, lng in real_path],
        }
    )


@app.route("/graph-data")
def graph_data():
    global CYCLE_COUNT, last_route, latest_bin_status
    CYCLE_COUNT += 1
    am_pm = "AM" if CYCLE_COUNT % 2 == 1 else "PM"
    truck_label = f"Truck 1 ({am_pm})"

    priority_targets = []
    predictive_targets = []
    bin_status = {}

    for node in G.nodes:
        if node == "BISWM":
            level = 100.0
            pred_level = 100.0
        else:
            rate = MEAN_RATES.get(node, 10)
            growth = max(0.0, rate + random.uniform(-0.4 * rate, 0.4 * rate))
            waste_levels[node] = min(waste_levels[node] + growth, 100.0)

            pred_growth = max(0.0, rate + random.uniform(-0.4 * rate, 0.4 * rate))
            pred_level = min(waste_levels[node] + pred_growth, 100.0)
            level = round(waste_levels[node], 1)

        bin_status[node] = {"level": level, "color": get_color(node, level)}

        if node in PRIORITY_ZONES and level >= 70:
            priority_targets.append((PRIORITY_ZONES[node], node))
        elif node not in {"BMC", "BISWM"} and pred_level >= 100:
            predictive_targets.append(node)

    priority_targets.sort()
    ordered_nodes = [node for _, node in priority_targets] + predictive_targets

    if ordered_nodes:
        full_path, distance_to_biswm = smart_greedy_route("BMC", ordered_nodes)
        return_path = all_paths["BISWM"]["BMC"][1:]
        full_path.extend(return_path)

        total_distance = distance_to_biswm + all_lengths["BISWM"]["BMC"]
        last_route = full_path
        last_edges = [
            (full_path[i], full_path[i + 1]) for i in range(len(full_path) - 1)
        ]

        total_waste = 0.0
        collected = []

        if "BMC" in full_path and waste_levels["BMC"] >= 70:
            waste_levels["BMC"] = 0.0

        for node in full_path:
            if node in {"BMC", "BISWM"}:
                continue
            if waste_levels[node] >= 70:
                bin_waste = (waste_levels[node] / 100.0) * 660.0
                if total_waste + bin_waste <= MAX_TRUCK_CAPACITY:
                    total_waste += bin_waste
                    collected.append(node)
                    waste_levels[node] = 0.0

        fuel_used = total_distance / FUEL_MILEAGE_KMPL
        fuel_cost = fuel_used * FUEL_PRICE_INR

        cleaned_route = []
        for node in full_path:
            if not cleaned_route or cleaned_route[-1] != node:
                cleaned_route.append(node)

        dispatch_info = (
            f"Truck Dispatch Info:\n"
            f"  > Label: {truck_label}\n"
            f"  > Route: {' -> '.join([SHORT_LABELS[n] for n in cleaned_route])}\n"
            f"  > Total Distance: {round(total_distance, 1)} km\n"
            f"  > Fuel Used: {round(fuel_used, 2)} L\n"
            f"  > Fuel Cost: Rs. {round(fuel_cost, 2)}\n"
            f"  > Waste Collected: {round(total_waste, 1)} kg\n"
            f"  > Collected Bins: {[SHORT_LABELS[n] for n in collected]}"
        )

        cycle_data.append(
            {
                "Cycle": CYCLE_COUNT,
                "Label": truck_label,
                "Distance (km)": round(total_distance, 1),
                "Fuel (L)": round(fuel_used, 2),
                "Fuel Cost (Rs)": round(fuel_cost, 2),
                "Waste Collected (kg)": round(total_waste, 1),
                "Collected Bins": ", ".join([SHORT_LABELS[n] for n in collected])
                or "None",
            }
        )
    else:
        last_route = []
        last_edges = []
        dispatch_info = "No collection needed this cycle."
        cycle_data.append(
            {
                "Cycle": CYCLE_COUNT,
                "Label": truck_label,
                "Distance (km)": 0,
                "Fuel (L)": 0,
                "Fuel Cost (Rs)": 0,
                "Waste Collected (kg)": 0,
                "Collected Bins": "None",
            }
        )

    latest_bin_status = bin_status
    export_success = False
    if CYCLE_COUNT % EXPORT_INTERVAL_CYCLES == 0:
        export_cycle_data()
        export_success = True

    return jsonify(
        {
            "positions": POSITIONS,
            "edges": list(G.edges()),
            "route_edges": last_edges,
            "bin_status": bin_status,
            "dispatch_info": dispatch_info,
            "export_success": export_success,
        }
    )


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=debug_mode)
