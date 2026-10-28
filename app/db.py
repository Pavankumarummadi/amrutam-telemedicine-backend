from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from app.config import get_settings

class Base(DeclarativeBase): pass
class Role(str, Enum): PATIENT="patient"; DOCTOR="doctor"; ADMIN="admin"
class ConsultationStatus(str, Enum): BOOKED="booked"; IN_PROGRESS="in_progress"; COMPLETED="completed"; CANCELLED="cancelled"
class SlotStatus(str, Enum): AVAILABLE="available"; HELD="held"; BOOKED="booked"; BLOCKED="blocked"

def utcnow(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__="users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SAEnum(Role), default=Role.PATIENT, index=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    doctor: Mapped["Doctor|None"] = relationship(back_populates="user", uselist=False)

class Doctor(Base):
    __tablename__="doctors"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    specialty: Mapped[str] = mapped_column(String(120), index=True)
    bio: Mapped[str] = mapped_column(Text, default="")
    user: Mapped[User] = relationship(back_populates="doctor")
    slots: Mapped[list["AvailabilitySlot"]] = relationship(back_populates="doctor")

class AvailabilitySlot(Base):
    __tablename__="availability_slots"
    __table_args__=(UniqueConstraint("doctor_id", "starts_at", name="uq_doctor_slot"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[SlotStatus] = mapped_column(SAEnum(SlotStatus), default=SlotStatus.AVAILABLE, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    doctor: Mapped[Doctor] = relationship(back_populates="slots")

class Consultation(Base):
    __tablename__="consultations"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("availability_slots.id"), unique=True)
    status: Mapped[ConsultationStatus] = mapped_column(SAEnum(ConsultationStatus), default=ConsultationStatus.BOOKED, index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    idempotency_key: Mapped[str|None] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Prescription(Base):
    __tablename__="prescriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    consultation_id: Mapped[int] = mapped_column(ForeignKey("consultations.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    medications: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AuditLog(Base):
    __tablename__="audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int|None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    resource_type: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str] = mapped_column(String(80))
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

engine = create_engine(get_settings().database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
def init_db(): Base.metadata.create_all(bind=engine)
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
