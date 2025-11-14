from sqlalchemy import Column, Integer, String, JSON
from app.db.base import Base

class RfyContentBuffer(Base):
    __tablename__ = 'rfy_content_buffer'
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    source_id = Column(String(255), nullable=True)
    collection_name = Column(String(255), nullable=True)
    payload = Column(JSON, nullable=True) 