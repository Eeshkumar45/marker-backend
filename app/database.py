from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from databases import Database
from dotenv import load_dotenv
import os
load_dotenv()
DATABASE_URL = os.getenv("POSTGRES")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# databases setup (for async)
database = Database(DATABASE_URL)

Base = declarative_base()

async def connect_db():
    await database.connect()

async def disconnect_db():
    await database.disconnect()