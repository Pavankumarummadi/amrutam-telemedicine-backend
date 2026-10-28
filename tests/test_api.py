import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import (
    AvailabilitySlot,
    Base,
    Doctor,
    Role,
    SessionLocal,
    SlotStatus,
    User,
    engine,
)
from app.main import app
from app.security import hash_password


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


def client():
    return TestClient(app)


def register(email, role="patient"):
    response = client().post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": "CorrectHorseBattery12!",
            "role": role,
        },
    )

    assert response.status_code == 201

    return response.json()["access_token"]


def test_register_login():
    register("patient@example.com")

    response = client().post(
        "/v1/auth/login",
        data={
            "username": "patient@example.com",
            "password": "CorrectHorseBattery12!",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_booking_idempotency():
    token = register("patient@example.com")

    db = SessionLocal()

    doctor_user = User(
        email="doc@example.com",
        password_hash=hash_password("CorrectHorseBattery12!"),
        role=Role.DOCTOR,
    )

    db.add(doctor_user)
    db.flush()

    doctor = Doctor(
        user_id=doctor_user.id,
        name="Dr. Rao",
        specialty="Dermatology",
    )

    db.add(doctor)
    db.flush()

    start_time = datetime.now(timezone.utc) + timedelta(days=1)
    end_time = start_time + timedelta(minutes=30)

    slot = AvailabilitySlot(
        doctor_id=doctor.id,
        starts_at=start_time,
        ends_at=end_time,
    )

    db.add(slot)
    db.commit()

    slot_id = slot.id
    db.close()

    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "booking-123",
    }

    payload = {
        "slot_id": slot_id,
        "reason": "rash",
    }

    first_response = client().post(
        "/v1/consultations",
        json=payload,
        headers=headers,
    )

    second_response = client().post(
        "/v1/consultations",
        json=payload,
        headers=headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["id"] == second_response.json()["id"]

    db = SessionLocal()

    assert db.query(AvailabilitySlot).one().status == SlotStatus.BOOKED

    db.close()


def test_admin_endpoint_requires_role():
    token = register("patient@example.com")

    response = client().get(
        "/v1/admin/analytics",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403
