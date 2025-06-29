from sqlalchemy import Column, Integer, String, Text
from app.db.base import Base

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    variations = Column(Text)
    attributes = Column(Text)
    url = Column(String(1024)) 