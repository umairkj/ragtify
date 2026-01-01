from sqlalchemy import Column, Integer, String, Text
from app.db.base import Base

class Settings(Base):
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Settings(key='{self.key}', value='{self.value}')>"

