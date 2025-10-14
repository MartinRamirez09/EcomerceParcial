# schemas.py
from pydantic import BaseModel, EmailStr, Field, constr
from typing import Optional, List

# --- Vendedores ---
class VendedorBase(BaseModel):
    email: EmailStr

class VendedorCreate(VendedorBase):
    password: str = Field(min_length=6)

class VendedorUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6)

class VendedorOut(VendedorBase):
    id: int
    class Config:
        from_attributes = True

# --- Auth ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    sub: Optional[str] = None
    user_id: Optional[int] = None

# --- Productos ---
class ProductoBase(BaseModel):
    nombre: constr(min_length=2)
    precio: float = Field(ge=0)
    descripcion: Optional[str] = None
    imagen: Optional[str] = None  # si el cliente quiere forzar una imagen propia

class ProductoCreate(ProductoBase):
    pass

class ProductoUpdate(BaseModel):
    nombre: Optional[constr(min_length=2)] = None
    precio: Optional[float] = Field(default=None, ge=0)
    descripcion: Optional[str] = None
    imagen: Optional[str] = None
    # Opcionalmente podrías permitir actualizar estos:
    descripcion_marketing: Optional[str] = None

class ProductoOut(BaseModel):
    id: int
    nombre: str
    precio: float
    descripcion: Optional[str]
    descripcion_marketing: Optional[str]
    imagen_url: Optional[str]
    vendedor_id: int

    class Config:
        from_attributes = True
