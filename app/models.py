from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Marker(Base):
    __tablename__ = "markers"
    
    id = Column(String, primary_key=True, index=True)
    lat = Column(Float)
    lng = Column(Float)
    data = Column(JSONB)
    room_id = Column(String, ForeignKey("rooms.id"))  # New field

    
class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    defaultLocation = Column(String)
    zoom = Column(Integer)
    extraFieldsAllowed = Column(Boolean)
    predefinedFields = Column(JSONB)
    mandatoryFields = Column(JSONB)
    expiresOn = Column(DateTime)