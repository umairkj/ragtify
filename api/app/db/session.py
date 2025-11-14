from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

MYSQL_USER = os.getenv('MYSQL_USER', 'llmuser')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'llmpassword')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql')
MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
MYSQL_DB = os.getenv('MYSQL_DATABASE', 'llm')
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 