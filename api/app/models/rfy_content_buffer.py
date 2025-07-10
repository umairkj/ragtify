from sqlalchemy import Column, Integer, String, Text
from app.db.base import Base

class RfyContentBuffer(Base):
    __tablename__ = 'rfy_content_buffer'
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    source_id = Column(Integer, nullable=False)
    collection_name = Column(String(255), nullable=False)
    payload = Column(Text, nullable=False) 