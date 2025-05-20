from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
from sqlalchemy.orm import Session
from models import Marker as MarkerModel, Room as RoomModel
from database import SessionLocal, database, Base, engine
from pydantic import BaseModel, UUID4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis
from datetime import datetime
from datetime import timedelta
import os
from fastapi.middleware import Middleware

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "http://127.0.0.1",  # Your frontend domain
    "https://marker.wasmer.app",
    "http://129.159.224.245",
    "https://129.159.224.245"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allowed origins
    allow_credentials=True,
    allow_methods=["*"],            # GET, POST, etc.
    allow_headers=["*"],           # Custom headers, e.g., Authorization
)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Models
class MarkerCreate(BaseModel):
    lat: float
    lng: float
    data: Dict[str, Any]
    room_id: str

class Marker(MarkerCreate):
    id: UUID4  # Use UUID4 type explicitly

    class Config:
        orm_mode = True

class RoomCreate(BaseModel):
    title: str
    defaultLocation: str
    zoom: int
    extraFieldsAllowed: bool
    predefinedFields: List[str]
    mandatoryFields: List[str]
    expiresOn: datetime
    
class Room(RoomCreate):
    id: str  # Use UUID4 type explicitly

    class Config:
        orm_mode = True

@app.on_event("startup")
async def startup():
    load_dotenv()
    redis_url = os.getenv("REDIS")
    redis_connection = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis_connection)

async def get_client_ip(request: Request):
    return request.client.host

add_rate_limiter = RateLimiter(
    times=3,  # Allow 2 requests
    seconds=60,  # Per 24 hours (adjust as needed)
    identifier= get_client_ip  # Use IP address as identifier
)
delete_rate_limiter = RateLimiter(
    times=3,  # Allow 2 requests
    seconds=60,  # Per 24 hours (adjust as needed)
    identifier= get_client_ip  # Use IP address as identifier
)

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/markers", response_model=Marker, dependencies=[Depends(add_rate_limiter)])
async def create_marker(marker: MarkerCreate, db: Session = Depends(get_db)):
    marker_id = str(uuid.uuid4())  # Convert to string immediately
    db_marker = MarkerModel(id=marker_id, **marker.dict())
    db.add(db_marker)
    db.commit()
    db.refresh(db_marker)
    return db_marker

@app.get("/rooms/check-availability")
async def check_room_name_availability(id: str, db: Session = Depends(get_db)):
    room_exists = db.query(RoomModel).filter(RoomModel.id == id).first()
    return {"available": room_exists is None}

@app.post("/rooms", response_model=Room, dependencies=[Depends(add_rate_limiter)])
async def create_room(room: Room, db: Session = Depends(get_db)):
    db_room = RoomModel(**room.dict())
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

@app.get("/rooms/{room_id}", response_model=Room)
async def get_room_by_id(room_id: str, db: Session = Depends(get_db)):
    db_room = db.query(RoomModel).filter(RoomModel.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    return db_room

@app.put("/markers/{marker_id}", response_model=Marker, dependencies=[Depends(add_rate_limiter)])
async def edit_marker(marker_id: str, marker: MarkerCreate, db: Session = Depends(get_db)):
    db_marker = db.query(MarkerModel).filter(MarkerModel.id == marker_id).first()
    db_marker.lat = marker.lat
    db_marker.lng = marker.lng
    db_marker.data = marker.data
    db.commit()
    db.refresh(db_marker)
    return db_marker

@app.get("/markers/{room_id}", response_model=List[Marker])
async def get_markers(room_id: str, db: Session = Depends(get_db)):
    query = select(MarkerModel).where(MarkerModel.room_id == room_id)
    markers = db.execute(query)
    return markers.scalars().all()

@app.get("/markers/{room_id}/bbox", response_model=List[Marker])
async def get_markers_bbox(
    room_id: str,
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    db: AsyncSession = Depends(get_db)
):
    query = select(MarkerModel).where(
        (MarkerModel.room_id == room_id) &
        (MarkerModel.lat >= min_lat) &
        (MarkerModel.lat <= max_lat) &
        (MarkerModel.lng >= min_lng) &
        (MarkerModel.lng <= max_lng)
    )
    result = db.execute(query)
    return result.scalars().all()

@app.delete("/markers/{marker_id}", dependencies=[Depends(delete_rate_limiter)])
async def delete_marker(marker_id: str, db: Session = Depends(get_db)):
    db_marker = db.query(MarkerModel).filter(MarkerModel.id == marker_id).first()
    if not db_marker:
        raise HTTPException(status_code=404, detail="Marker not found")
    db.delete(db_marker)
    db.commit()
    return {"status": "deleted"}