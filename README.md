# AEQUITAS Backend

Fair & Transparent Delivery Route Assignment System — REST API

## Stack
- **Python 3.10+** with **Flask**
- In-memory store (swap for SQLite / PostgreSQL in production)

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Server runs at `http://localhost:5000`

---

## API Reference

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Service health check |

---

### Drivers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/drivers` | List all drivers |
| POST | `/api/drivers` | Add a driver |
| GET | `/api/drivers/:id` | Get a driver |
| DELETE | `/api/drivers/:id` | Remove a driver |

**POST `/api/drivers` body:**
```json
{
  "id": "d1",
  "name": "Ravi Kumar",
  "email": "ravi@example.com",
  "phone": "9876543210"
}
```

---

### Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/routes` | List all routes |
| POST | `/api/routes` | Add a route (auto-scores it) |
| GET | `/api/routes/:id` | Get a route |
| DELETE | `/api/routes/:id` | Remove a route |

**POST `/api/routes` body:**
```json
{
  "id": "r1",
  "name": "Zone A - Morning",
  "packages": 35,
  "total_weight_kg": 80,
  "stairs_count": 4,
  "distance_km": 22,
  "origin": "Warehouse, Chennai",
  "destination": "Anna Nagar, Chennai"
}
```

---

### Scoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/score` | Score a route without saving it |

**POST `/api/score` body:**
```json
{
  "packages": 40,
  "total_weight_kg": 120,
  "stairs_count": 8,
  "distance_km": 35
}
```

**Response:**
```json
{
  "difficulty_score": 54.17,
  "difficulty_label": "Moderate",
  "breakdown": {
    "packages": { "raw_value": 40, "cap": 60, "normalised": 0.6667, "weight": 0.25, "weighted_contrib": 16.67 },
    ...
  }
}
```

---

### Assignment
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/assign` | Run fair load-balancing & assign routes |
| GET | `/api/assignments` | Get all assignments |
| POST | `/api/assignments/reset` | Clear all assignments |

---

### Emissions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/emissions` | Estimate CO₂ for a route |

**POST `/api/emissions` body:**
```json
{
  "distance_km": 22,
  "emission_factor_kg_per_km": 0.21
}
```

---

## Scoring Algorithm

Each route's difficulty score (0–100) is computed as a weighted sum of four normalised factors:

| Factor | Weight | Cap |
|--------|--------|-----|
| Total weight (kg) | 30 % | 200 kg |
| Packages | 25 % | 60 packages |
| Stairs stops | 25 % | 20 stops |
| Distance (km) | 20 % | 100 km |

## Load-Balancing Algorithm

**Greedy Least-Load Dispatch** (optimal for makespan minimisation):
1. Sort routes hardest → easiest.
2. Assign each route to the driver with the lowest cumulative score.
3. Attach a transparent, human-readable explanation to every assignment.
