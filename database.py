"""
database.py — MongoDB persistence layer for AEQUITAS
=====================================================
Collections:
  drivers     — registered delivery drivers
  routes      — delivery routes with difficulty scores
  assignments — assignment history (driver ↔ route pairings)

Configuration:
  Set MONGO_URI in a .env file or as an environment variable.
  Defaults to mongodb://localhost:27017 if not set.
"""

import os
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = os.getenv("MONGO_DB",  "aequitas")

_client: MongoClient | None = None


def get_db():
    """Return the MongoDB database instance (lazy singleton)."""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client[DB_NAME]


def init_db():
    """
    Verify connection and create indexes.
    Called once at app startup.
    """
    try:
        db = get_db()
        # Ping to confirm connection
        db.command("ping")

        # Unique indexes on our custom 'id' field
        db.drivers.create_index("id", unique=True)
        db.routes.create_index("id",  unique=True)
        db.assignments.create_index([("assigned_at", ASCENDING)])

        print(f"[DB] Connected to MongoDB → {MONGO_URI} / {DB_NAME}")
    except Exception as e:
        print(f"[DB] ⚠️  MongoDB connection failed: {e}")
        raise


def _clean(doc: dict) -> dict:
    """Remove MongoDB's internal _id field before returning to the API."""
    doc.pop("_id", None)
    return doc


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------

def db_get_all_drivers() -> list[dict]:
    return [_clean(d) for d in get_db().drivers.find({}, {"_id": 0}).sort("name", ASCENDING)]


def db_get_driver(driver_id: str) -> dict | None:
    doc = get_db().drivers.find_one({"id": driver_id}, {"_id": 0})
    return doc or None


def db_insert_driver(driver: dict) -> None:
    get_db().drivers.insert_one({
        "id":               driver["id"],
        "name":             driver["name"],
        "email":            driver.get("email", ""),
        "phone":            driver.get("phone", ""),
        "cumulative_score": driver.get("cumulative_score", 0.0),
    })


def db_delete_driver(driver_id: str) -> bool:
    result = get_db().drivers.delete_one({"id": driver_id})
    return result.deleted_count > 0


def db_update_driver_score(driver_id: str, new_score: float) -> None:
    get_db().drivers.update_one(
        {"id": driver_id},
        {"$set": {"cumulative_score": new_score}}
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def db_get_all_routes() -> list[dict]:
    return [_clean(r) for r in get_db().routes.find({}, {"_id": 0}).sort("name", ASCENDING)]


def db_get_route(route_id: str) -> dict | None:
    doc = get_db().routes.find_one({"id": route_id}, {"_id": 0})
    return doc or None


def db_insert_route(route: dict) -> None:
    get_db().routes.insert_one({
        "id":               route["id"],
        "name":             route["name"],
        "packages":         route["packages"],
        "total_weight_kg":  route["total_weight_kg"],
        "stairs_count":     route["stairs_count"],
        "distance_km":      route["distance_km"],
        "origin":           route.get("origin", ""),
        "destination":      route.get("destination", ""),
        "difficulty_score": route.get("difficulty_score", 0.0),
        "assigned_to":      route.get("assigned_to", None),
    })


def db_delete_route(route_id: str) -> bool:
    result = get_db().routes.delete_one({"id": route_id})
    return result.deleted_count > 0


def db_assign_route(route_id: str, driver_id: str) -> None:
    get_db().routes.update_one(
        {"id": route_id},
        {"$set": {"assigned_to": driver_id}}
    )


def db_unassign_all_routes() -> None:
    get_db().routes.update_many({}, {"$set": {"assigned_to": None}})


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------

def db_get_all_assignments() -> list[dict]:
    return [
        _clean(a) for a in
        get_db().assignments.find({}, {"_id": 0}).sort("assigned_at", -1)
    ]


def db_insert_assignment(a: dict) -> None:
    get_db().assignments.insert_one({
        "driver_id":        a["driver_id"],
        "driver_name":      a["driver_name"],
        "route_id":         a["route_id"],
        "route_name":       a["route_name"],
        "difficulty_score": a["difficulty_score"],
        "explanation":      a["explanation"],
        "assigned_at":      datetime.now(timezone.utc).isoformat(),
    })


def db_clear_assignments() -> None:
    get_db().assignments.delete_many({})


def db_reset_driver_scores() -> None:
    get_db().drivers.update_many({}, {"$set": {"cumulative_score": 0.0}})
    