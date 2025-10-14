# models.py
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from database import Base

class Vendedor(Base):
    __tablename__ = "vendedores"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    productos = relationship("Producto", back_populates="vendedor", cascade="all, delete-orphan")

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False, index=True)
    precio = Column(Float, nullable=False)
    descripcion = Column(Text, nullable=True)
    descripcion_marketing = Column(Text, nullable=True)
    imagen_url = Column(Text, nullable=True)

    vendedor_id = Column(Integer, ForeignKey("vendedores.id", ondelete="CASCADE"), nullable=False, index=True)
    vendedor = relationship("Vendedor", back_populates="productos")

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
