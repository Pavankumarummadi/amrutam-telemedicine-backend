from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.db import ConsultationStatus, Role, SlotStatus
class RegisterIn(BaseModel): email:EmailStr; password:str=Field(min_length=12); role:Role=Role.PATIENT
class LoginIn(BaseModel): email:EmailStr; password:str
class TokenOut(BaseModel): access_token:str; token_type:str="bearer"
class DoctorIn(BaseModel): name:str=Field(min_length=2,max_length=160); specialty:str=Field(min_length=2,max_length=120); bio:str=""
class DoctorOut(DoctorIn): model_config=ConfigDict(from_attributes=True); id:int
class SlotIn(BaseModel): starts_at:datetime; ends_at:datetime
class SlotOut(SlotIn): model_config=ConfigDict(from_attributes=True); id:int; doctor_id:int; status:SlotStatus
class BookingIn(BaseModel): slot_id:int; reason:str=Field(default="",max_length=2000)
class ConsultationOut(BaseModel): model_config=ConfigDict(from_attributes=True); id:int; patient_id:int; doctor_id:int; slot_id:int; status:ConsultationStatus; reason:str; created_at:datetime
class PrescriptionIn(BaseModel): medications:str=Field(min_length=1,max_length=10000); notes:str=""
class PrescriptionOut(PrescriptionIn): model_config=ConfigDict(from_attributes=True); id:int; consultation_id:int; doctor_id:int
