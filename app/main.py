import logging, time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from app.api import auth, clinical
from app.config import get_settings
from app.db import init_db
settings=get_settings(); logging.basicConfig(level=settings.log_level,format="%(asctime)s %(levelname)s %(message)s")
app=FastAPI(title="Amrutam Telemedicine API",version="1.0.0",description="Secure, observable telemedicine backend",openapi_url="/openapi.json")
REQUESTS=Counter("http_requests_total","HTTP requests",["method","path","status"])
LATENCY=Histogram("http_request_duration_seconds","HTTP request duration",["method","path"])
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins.split(","),allow_credentials=False,allow_methods=["GET","POST","PATCH"],allow_headers=["Authorization","Content-Type","Idempotency-Key"])
@app.on_event("startup")
def startup(): init_db()
@app.middleware("http")
async def request_context(request:Request,call_next):
    started=time.perf_counter(); response=await call_next(request); elapsed=time.perf_counter()-started
    REQUESTS.labels(request.method,request.url.path,str(response.status_code)).inc(); LATENCY.labels(request.method,request.url.path).observe(elapsed)
    response.headers["X-Request-ID"]=request.headers.get("X-Request-ID","generated"); logging.info("request method=%s path=%s status=%s duration_ms=%.2f",request.method,request.url.path,response.status_code,elapsed*1000); return response
@app.get("/health/live",tags=["ops"])
def liveness(): return {"status":"ok"}
@app.get("/health/ready",tags=["ops"])
def readiness(): return {"status":"ready"}
@app.get("/metrics",include_in_schema=False)
def metrics(): return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)
app.include_router(auth.router,prefix="/v1")
app.include_router(clinical.router,prefix="/v1")
