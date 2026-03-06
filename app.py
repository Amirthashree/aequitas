from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()  # loads MONGO_URI and MONGO_DB from .env
from scoring import compute_difficulty_score
from balancer import assign_routes
from models import Driver, Route
from database import (
    init_db,
    db_get_all_drivers, db_get_driver, db_insert_driver,
    db_delete_driver, db_update_driver_score,
    db_get_all_routes, db_get_route, db_insert_route,
    db_delete_route, db_assign_route,
    db_unassign_all_routes,
    db_get_all_assignments, db_insert_assignment,
    db_clear_assignments, db_reset_driver_scores,
)

app = Flask(__name__)
CORS(app)

# Initialise DB tables on startup
init_db()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "AEQUITAS Backend"})


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------
@app.route("/api/drivers", methods=["GET"])
def get_drivers():
    return jsonify(db_get_all_drivers())


@app.route("/api/drivers", methods=["POST"])
def add_driver():
    data = request.get_json()
    if not data or not all(k in data for k in ["id", "name"]):
        return jsonify({"error": "Fields required: id, name"}), 400

    if db_get_driver(data["id"]):
        return jsonify({"error": f"Driver '{data['id']}' already exists"}), 409

    driver = {
        "id":               data["id"],
        "name":             data["name"],
        "email":            data.get("email", ""),
        "phone":            data.get("phone", ""),
        "cumulative_score": 0.0,
    }
    db_insert_driver(driver)
    return jsonify(driver), 201


@app.route("/api/drivers/<driver_id>", methods=["GET"])
def get_driver(driver_id):
    driver = db_get_driver(driver_id)
    if not driver:
        return jsonify({"error": "Driver not found"}), 404
    return jsonify(driver)


@app.route("/api/drivers/<driver_id>", methods=["DELETE"])
def delete_driver(driver_id):
    if not db_delete_driver(driver_id):
        return jsonify({"error": "Driver not found"}), 404
    return jsonify({"message": "Driver deleted"}), 200


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/api/routes", methods=["GET"])
def get_routes():
    return jsonify(db_get_all_routes())


@app.route("/api/routes", methods=["POST"])
def add_route():
    data = request.get_json()
    required = ["id", "packages", "total_weight_kg", "stairs_count", "distance_km"]
    if not data or not all(k in data for k in required):
        return jsonify({"error": f"Fields required: {required}"}), 400

    if db_get_route(data["id"]):
        return jsonify({"error": f"Route '{data['id']}' already exists"}), 409

    temp = Route(
        id=data["id"],
        name=data.get("name", data["id"]),
        packages=int(data["packages"]),
        total_weight_kg=float(data["total_weight_kg"]),
        stairs_count=int(data["stairs_count"]),
        distance_km=float(data["distance_km"]),
    )
    score = compute_difficulty_score(temp)

    route = {
        "id":               data["id"],
        "name":             data.get("name", data["id"]),
        "packages":         int(data["packages"]),
        "total_weight_kg":  float(data["total_weight_kg"]),
        "stairs_count":     int(data["stairs_count"]),
        "distance_km":      float(data["distance_km"]),
        "origin":           data.get("origin", ""),
        "destination":      data.get("destination", ""),
        "difficulty_score": round(score, 4),
        "assigned_to":      None,
    }
    db_insert_route(route)
    return jsonify(route), 201


@app.route("/api/routes/<route_id>", methods=["GET"])
def get_route(route_id):
    route = db_get_route(route_id)
    if not route:
        return jsonify({"error": "Route not found"}), 404
    return jsonify(route)


@app.route("/api/routes/<route_id>", methods=["DELETE"])
def delete_route(route_id):
    if not db_delete_route(route_id):
        return jsonify({"error": "Route not found"}), 404
    return jsonify({"message": "Route deleted"}), 200


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
@app.route("/api/score", methods=["POST"])
def score_route():
    data = request.get_json()
    required = ["packages", "total_weight_kg", "stairs_count", "distance_km"]
    if not data or not all(k in data for k in required):
        return jsonify({"error": f"Fields required: {required}"}), 400

    temp = Route(
        id="temp", name="temp",
        packages=int(data["packages"]),
        total_weight_kg=float(data["total_weight_kg"]),
        stairs_count=int(data["stairs_count"]),
        distance_km=float(data["distance_km"]),
    )
    score, breakdown = compute_difficulty_score(temp, return_breakdown=True)
    return jsonify({
        "difficulty_score":  round(score, 2),
        "breakdown":         breakdown,
        "difficulty_label":  _difficulty_label(score),
    })


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------
@app.route("/api/assign", methods=["POST"])
def assign():
    drivers_data = db_get_all_drivers()
    routes_data  = db_get_all_routes()

    if not drivers_data:
        return jsonify({"error": "No drivers registered"}), 400
    if not routes_data:
        return jsonify({"error": "No routes available"}), 400

    unassigned_data = [r for r in routes_data if not r["assigned_to"]]
    if not unassigned_data:
        return jsonify({"message": "All routes are already assigned", "assignments": []}), 200

    drivers = [
        Driver(id=d["id"], name=d["name"], email=d["email"],
               phone=d["phone"], cumulative_score=d["cumulative_score"])
        for d in drivers_data
    ]
    unassigned = [
        Route(
            id=r["id"], name=r["name"],
            packages=r["packages"], total_weight_kg=r["total_weight_kg"],
            stairs_count=r["stairs_count"], distance_km=r["distance_km"],
            difficulty_score=r["difficulty_score"],
        )
        for r in unassigned_data
    ]

    result = assign_routes(drivers, unassigned)

    for a in result:
        db_assign_route(a.route_id, a.driver_id)
        driver = next(d for d in drivers if d.id == a.driver_id)
        new_score = driver.cumulative_score + a.difficulty_score
        db_update_driver_score(a.driver_id, new_score)
        driver.cumulative_score = new_score
        db_insert_assignment(a.to_dict())

    updated_drivers = db_get_all_drivers()
    return jsonify({
        "assignments":      [a.to_dict() for a in result],
        "driver_summaries": updated_drivers,
    })


@app.route("/api/assignments", methods=["GET"])
def get_assignments():
    return jsonify(db_get_all_assignments())


@app.route("/api/assignments/reset", methods=["POST"])
def reset_assignments():
    db_clear_assignments()
    db_unassign_all_routes()
    db_reset_driver_scores()
    return jsonify({"message": "All assignments reset"})


# ---------------------------------------------------------------------------
# CO₂ Emissions
# ---------------------------------------------------------------------------
@app.route("/api/emissions", methods=["POST"])
def estimate_emissions():
    data = request.get_json()
    if not data or "distance_km" not in data:
        return jsonify({"error": "distance_km is required"}), 400

    distance = float(data["distance_km"])
    factor   = float(data.get("emission_factor_kg_per_km", 0.21))
    co2_kg   = round(distance * factor, 3)
    return jsonify({
        "distance_km":               distance,
        "emission_factor_kg_per_km": factor,
        "co2_kg":                    co2_kg,
        "co2_label":                 f"{co2_kg:.2f} kg CO₂",
    })


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _difficulty_label(score: float) -> str:
    if score < 30: return "Easy"
    if score < 60: return "Moderate"
    if score < 80: return "Hard"
    return "Extreme"


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    