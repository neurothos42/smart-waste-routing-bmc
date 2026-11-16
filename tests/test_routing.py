import os
import sys
from pathlib import Path

# Add project root to Python import path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Prevent OSM network downloads during tests
os.environ["DISABLE_OSM_DOWNLOAD"] = "true"

import pytest
from app import app, smart_greedy_route, get_color


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_bin_color_thresholds():
    assert get_color("BISWM", 100) == "purple"
    assert get_color("BMC", 10) == "green"
    assert get_color("BMC", 45) == "yellow"
    assert get_color("BMC", 85) == "red"


def test_smart_greedy_route_ends_at_biswm():
    path, distance = smart_greedy_route("BMC", ["Railway Station", "City Hospital"])

    assert path[0] == "BMC"
    assert path[-1] == "BISWM"
    assert distance > 0


def test_role_based_authentication(client):
    response = client.get("/dashboard")
    assert response.status_code == 302

    login_response = client.post(
        "/login",
        data={"userid": "admin", "password": "adminpass"},
        follow_redirects=True,
    )

    assert login_response.status_code == 200
    assert b"Truck Dispatch Info" in login_response.data
