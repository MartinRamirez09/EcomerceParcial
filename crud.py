# crud.py
from sqlalchemy.orm import Session
from models import Vendedor, Producto
from security import get_password_hash, verify_password

# ------- Vendedores -------
def get_vendedor_by_email(db: Session, email: str):
    return db.query(Vendedor).filter(Vendedor.email == email).first()

def get_vendedores(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Vendedor).offset(skip).limit(limit).all()

def get_vendedor(db: Session, vendedor_id: int):
    return db.query(Vendedor).filter(Vendedor.id == vendedor_id).first()

def create_vendedor(db: Session, email: str, password: str):
    hashed = get_password_hash(password)
    vend = Vendedor(email=email, hashed_password=hashed)
    db.add(vend)
    db.commit()
    db.refresh(vend)
    return vend

def update_vendedor(db: Session, vendedor: Vendedor, *, email: str | None = None, password: str | None = None):
    if email is not None:
        vendedor.email = email
    if password is not None:
        vendedor.hashed_password = get_password_hash(password)
    db.add(vendedor)
    db.commit()
    db.refresh(vendedor)
    return vendedor

def delete_vendedor(db: Session, vendedor: Vendedor):
    db.delete(vendedor)
    db.commit()

def authenticate_vendedor(db: Session, email: str, password: str):
    user = get_vendedor_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

# ------- Productos -------
def create_producto(
    db: Session,
    vendedor_id: int,
    nombre: str,
    precio: float,
    descripcion: str | None,
    descripcion_marketing: str | None,
    imagen_url: str | None,
):
    prod = Producto(
        vendedor_id=vendedor_id,
        nombre=nombre,
        precio=precio,
        descripcion=descripcion,
        descripcion_marketing=descripcion_marketing,
        imagen_url=imagen_url,
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod

def get_productos_by_vendedor(db: Session, vendedor_id: int):
    return db.query(Producto).filter(Producto.vendedor_id == vendedor_id).order_by(Producto.id.desc()).all()

def get_producto(db: Session, vendedor_id: int, producto_id: int):
    return (
        db.query(Producto)
        .filter(Producto.id == producto_id, Producto.vendedor_id == vendedor_id)
        .first()
    )

def update_producto(db: Session, producto: Producto, **fields):
    for k, v in fields.items():
        setattr(producto, k, v)
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto

def delete_producto(db: Session, producto: Producto):
    db.delete(producto)
    db.commit()
