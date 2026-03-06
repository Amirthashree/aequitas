from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Driver:
    id: str
    name: str
    email: str = ""
    phone: str = ""
    cumulative_score: float = 0.0

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "cumulative_score": round(self.cumulative_score, 2),
        }


@dataclass
class Route:
    id: str
    name: str
    packages: int
    total_weight_kg: float
    stairs_count: int
    distance_km: float
    origin: str = ""
    destination: str = ""
    waypoints: list = field(default_factory=list)
    difficulty_score: float = 0.0
    assigned_to: Optional[str] = None  # driver id

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "packages": self.packages,
            "total_weight_kg": self.total_weight_kg,
            "stairs_count": self.stairs_count,
            "distance_km": self.distance_km,
            "origin": self.origin,
            "destination": self.destination,
            "waypoints": self.waypoints,
            "difficulty_score": round(self.difficulty_score, 2),
            "assigned_to": self.assigned_to,
        }


@dataclass
class Assignment:
    driver_id: str
    driver_name: str
    route_id: str
    route_name: str
    difficulty_score: float
    explanation: str

    def to_dict(self):
        return {
            "driver_id": self.driver_id,
            "driver_name": self.driver_name,
            "route_id": self.route_id,
            "route_name": self.route_name,
            "difficulty_score": round(self.difficulty_score, 2),
            "explanation": self.explanation,
        }
