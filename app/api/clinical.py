import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db import AuditLog, AvailabilitySlot, Consultation, ConsultationStatus, Doctor, Prescription, Role, SlotStatus, User, get_db
from app.schemas import ConsultationOut, DoctorIn, DoctorOut, BookingIn, PrescriptionIn, PrescriptionOut, SlotIn, SlotOut
from app.security import current_user, require_roles
router=APIRouter(tags=["clinical"])
def audit(db,actor,action,typ,rid,metadata=None): db.add(AuditLog(actor_id=actor.id if actor else None,action=action,resource_type=typ,resource_id=str(rid),metadata_json=json.dumps(metadata or {})))
@router.post("/doctors",response_model=DoctorOut,status_code=201)
def create_doctor(p:DoctorIn, db:Session=Depends(get_db), user:User=Depends(require_roles(Role.ADMIN))):
    target=db.query(User).filter(User.role==Role.DOCTOR).first()
    if not target: target=User(email=f"doctor-{datetime.now().timestamp()}@internal",password_hash="managed",role=Role.DOCTOR); db.add(target); db.flush()
    d=Doctor(user_id=target.id,**p.model_dump()); db.add(d); db.flush(); audit(db,user,"doctor.created","doctor",d.id); db.commit(); return d
@router.get("/doctors",response_model=list[DoctorOut])
def search_doctors(specialty:str|None=None, q:str|None=None, db:Session=Depends(get_db)):
    query=db.query(Doctor)
    if specialty: query=query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
    if q: query=query.filter(Doctor.name.ilike(f"%{q}%"))
    return query.order_by(Doctor.name).limit(100).all()
@router.post("/doctors/{doctor_id}/slots",response_model=SlotOut,status_code=201)
def add_slot(doctor_id:int,p:SlotIn,db:Session=Depends(get_db),user:User=Depends(require_roles(Role.DOCTOR,Role.ADMIN))):
    d=db.get(Doctor,doctor_id)
    if not d: raise HTTPException(404,"Doctor not found")
    if p.ends_at<=p.starts_at or p.starts_at<=datetime.now(timezone.utc): raise HTTPException(400,"Invalid slot window")
    slot=AvailabilitySlot(doctor_id=doctor_id,**p.model_dump()); db.add(slot); audit(db,user,"slot.created","slot",slot.id or "pending"); db.commit(); db.refresh(slot); return slot
@router.get("/slots",response_model=list[SlotOut])
def list_slots(doctor_id:int|None=None,from_at:datetime|None=None,to_at:datetime|None=None,db:Session=Depends(get_db)):
    q=db.query(AvailabilitySlot).filter(AvailabilitySlot.status==SlotStatus.AVAILABLE)
    if doctor_id:q=q.filter(AvailabilitySlot.doctor_id==doctor_id)
    if from_at:q=q.filter(AvailabilitySlot.starts_at>=from_at)
    if to_at:q=q.filter(AvailabilitySlot.ends_at<=to_at)
    return q.order_by(AvailabilitySlot.starts_at).limit(500).all()
@router.post("/consultations",response_model=ConsultationOut,status_code=201)
def book(p:BookingIn,idempotency_key:str=Header(...,alias="Idempotency-Key",min_length=8,max_length=128),db:Session=Depends(get_db),user:User=Depends(current_user)):
    old=db.query(Consultation).filter(Consultation.idempotency_key==idempotency_key).first()
    if old: return old
    slot=db.query(AvailabilitySlot).filter(AvailabilitySlot.id==p.slot_id).with_for_update().first()
    if not slot or slot.status!=SlotStatus.AVAILABLE: raise HTTPException(409,"Slot is not available")
    slot.status=SlotStatus.BOOKED; c=Consultation(patient_id=user.id,doctor_id=slot.doctor_id,slot_id=slot.id,reason=p.reason,idempotency_key=idempotency_key); db.add(c); db.flush(); audit(db,user,"consultation.booked","consultation",c.id); db.commit(); db.refresh(c); return c
@router.patch("/consultations/{consultation_id}/status",response_model=ConsultationOut)
def update_status(consultation_id:int,status:ConsultationStatus,db:Session=Depends(get_db),user:User=Depends(require_roles(Role.DOCTOR,Role.ADMIN))):
    c=db.get(Consultation,consultation_id)
    if not c: raise HTTPException(404,"Consultation not found")
    allowed={ConsultationStatus.BOOKED:{ConsultationStatus.IN_PROGRESS,ConsultationStatus.CANCELLED},ConsultationStatus.IN_PROGRESS:{ConsultationStatus.COMPLETED,ConsultationStatus.CANCELLED},ConsultationStatus.COMPLETED:set(),ConsultationStatus.CANCELLED:set()}
    if status not in allowed[c.status]: raise HTTPException(409,"Invalid lifecycle transition")
    c.status=status; audit(db,user,"consultation.status_changed","consultation",c.id,{"status":status.value}); db.commit(); db.refresh(c); return c
@router.post("/consultations/{consultation_id}/prescriptions",response_model=PrescriptionOut,status_code=201)
def prescribe(consultation_id:int,p:PrescriptionIn,db:Session=Depends(get_db),user:User=Depends(require_roles(Role.DOCTOR,Role.ADMIN))):
    c=db.get(Consultation,consultation_id)
    if not c or c.status!=ConsultationStatus.COMPLETED: raise HTTPException(400,"Consultation must be completed")
    if user.role==Role.DOCTOR and c.doctor_id != user.doctor.id: raise HTTPException(403,"Not the assigned doctor")
    r=Prescription(consultation_id=c.id,doctor_id=c.doctor_id,**p.model_dump()); db.add(r); audit(db,user,"prescription.created","prescription",r.id or "pending"); db.commit(); db.refresh(r); return r
@router.get("/admin/analytics")
def analytics(db:Session=Depends(get_db),user:User=Depends(require_roles(Role.ADMIN))):
    rows=db.query(Consultation.status,func.count(Consultation.id)).group_by(Consultation.status).all()
    return {"consultations_by_status":{s.value:n for s,n in rows},"total_users":db.query(func.count(User.id)).scalar(),"audit_events":db.query(func.count(AuditLog.id)).scalar()}
