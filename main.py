# main.py
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy.orm import Session
from typing import List, Optional
import os

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True), override=True)

from database import Base, engine, get_db
from schemas import (
    VendedorCreate, VendedorUpdate, VendedorOut, Token,
    ProductoCreate, ProductoUpdate, ProductoOut
)
from crud import (
    get_vendedor_by_email, create_vendedor, authenticate_vendedor,
    get_vendedores, get_vendedor, update_vendedor, delete_vendedor,
    create_producto, get_productos_by_vendedor, get_producto,
    update_producto, delete_producto
)
from security import create_access_token, get_current_vendedor
from gemini_client import generar_descripcion, generar_imagen

app = FastAPI(title="Mercurio API", version="1.2.0")

# Crear tablas
Base.metadata.create_all(bind=engine)

# Estáticos para /media
os.makedirs("media", exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")

# ---------- AUTH ----------
@app.post("/register", response_model=VendedorOut, status_code=201, tags=["auth"])
def register(v: VendedorCreate, db: Session = Depends(get_db)):
    if get_vendedor_by_email(db, v.email):
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    user = create_vendedor(db, v.email, v.password)
    return user

@app.post("/token", response_model=Token, tags=["auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    vendedor = authenticate_vendedor(db, form_data.username, form_data.password)
    if not vendedor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    token = create_access_token(subject=vendedor.email, user_id=vendedor.id)
    return {"access_token": token, "token_type": "bearer"}

# ---------- VENDEDORES ----------
@app.get("/vendedores/me", response_model=VendedorOut, tags=["vendedores"])
def leer_mi_perfil(current=Depends(get_current_vendedor)):
    return current

@app.get("/vendedores/", response_model=List[VendedorOut], tags=["vendedores"])
def listar_vendedores(skip: int = 0, limit: int = 100, current=Depends(get_current_vendedor), db: Session = Depends(get_db)):
    return get_vendedores(db, skip=skip, limit=limit)

@app.get("/vendedores/{vendedor_id}", response_model=VendedorOut, tags=["vendedores"])
def obtener_vendedor_endpoint(vendedor_id: int, current=Depends(get_current_vendedor), db: Session = Depends(get_db)):
    if current.id != vendedor_id:
        raise HTTPException(status_code=403, detail="Solo puedes consultar tu propio perfil")
    vend = get_vendedor(db, vendedor_id)
    if not vend:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    return vend

@app.put("/vendedores/{vendedor_id}", tags=["vendedores"])
def actualizar_vendedor_endpoint(vendedor_id: int, data: VendedorUpdate, current=Depends(get_current_vendedor), db: Session = Depends(get_db)):
    if current.id != vendedor_id:
        raise HTTPException(status_code=403, detail="Solo puedes actualizar tu propio perfil")
    vend = get_vendedor(db, vendedor_id)
    if not vend:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    fields = data.model_dump(exclude_unset=True)
    updated = update_vendedor(db, vend, email=fields.get("email"), password=fields.get("password"))
    return {"message": "Vendedor actualizado", "vendedor": {"id": updated.id, "email": updated.email}}

@app.delete("/vendedores/{vendedor_id}", tags=["vendedores"])
def eliminar_vendedor_endpoint(vendedor_id: int, current=Depends(get_current_vendedor), db: Session = Depends(get_db)):
    if current.id != vendedor_id:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tu propia cuenta")
    vend = get_vendedor(db, vendedor_id)
    if not vend:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    delete_vendedor(db, vend)
    return {"message": "Vendedor eliminado", "id": vendedor_id}

# ---------- PRODUCTOS ----------
@app.get("/productos/", response_model=List[ProductoOut], tags=["productos"])
def listar_productos(id: Optional[int] = None, current=Depends(get_current_vendedor), db: Session = Depends(get_db)):
    if id is not None:
        prod = get_producto(db, current.id, id)
        return [prod] if prod else []
    return get_productos_by_vendedor(db, current.id)

@app.get("/productos/{producto_id}", response_model=ProductoOut, tags=["productos"])
def obtener_producto(producto_id: int, current=Depends(get_current_vendedor), db: Session = Depends(get_db)):
    prod = get_producto(db, current.id, producto_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return prod

@app.post("/productos/", response_model=ProductoOut, status_code=201, tags=["productos"])
def crear_producto(data: ProductoCreate, request: Request, current=Depends(get_current_vendedor), db: Session = Depends(get_db)):
    desc_mkt = generar_descripcion(data.nombre, data.descripcion, data.precio)
    imagen_url = data.imagen or generar_imagen(desc_mkt, data.nombre)
    producto = create_producto(
        db=db,
        vendedor_id=current.id,
        nombre=data.nombre,
        precio=data.precio,
        descripcion=data.descripcion,
        descripcion_marketing=desc_mkt,
        imagen_url=imagen_url,
    )
    return producto

@app.put("/productos/{producto_id}", tags=["productos"])
def actualizar_producto(producto_id: int, data: ProductoUpdate, current=Depends(get_current_vendedor), db: Session = Depends(get_db)):
    prod = get_producto(db, current.id, producto_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    fields = data.model_dump(exclude_unset=True)
    if "nombre" in fields and "descripcion_marketing" not in fields:
        nueva_desc = generar_descripcion(fields["nombre"], fields.get("descripcion"), fields.get("precio"))
        fields["descripcion_marketing"] = nueva_desc
        if "imagen" not in fields and "imagen_url" not in fields:
            fields["imagen_url"] = generar_imagen(nueva_desc, fields["nombre"])

    updated = update_producto(db, prod, **fields)
    return {
        "message": "Producto actualizado",
        "producto": {
            "id": updated.id,
            "nombre": updated.nombre,
            "precio": updated.precio,
            "descripcion": updated.descripcion,
            "descripcion_marketing": updated.descripcion_marketing,
            "imagen_url": updated.imagen_url,
            "vendedor_id": updated.vendedor_id,
        },
    }

@app.delete("/productos/{producto_id}", tags=["productos"])
def eliminar_producto(producto_id: int, current=Depends(get_current_vendedor), db: Session = Depends(get_db)):
    prod = get_producto(db, current.id, producto_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    delete_producto(db, prod)
    return {"message": "Producto eliminado", "id": producto_id}

# Imagen binaria o redirección
@app.get("/productos/{producto_id}/imagen", responses={200: {"content": {"image/png": {}}}, 404: {"description": "Not found"}}, tags=["productos"])
def ver_imagen_producto(producto_id: int, current=Depends(get_current_vendedor), db: Session = Depends(get_db)):
    prod = get_producto(db, current.id, producto_id)
    if not prod or not prod.imagen_url:
        raise HTTPException(status_code=404, detail="Imagen no disponible")
    url = prod.imagen_url
    if url.startswith("http://") or url.startswith("https://"):
        return RedirectResponse(url=url)
    if url.startswith("/media/"):
        path = os.path.join(".", url.lstrip("/"))
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        return FileResponse(path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Imagen no disponible")

# Debug
@app.get("/_debug/ia", tags=["debug"])
def debug_ia():
    return {"gemini_key_present": bool(os.getenv("GEMINI_API_KEY")), "image_provider": os.getenv("IMAGE_API_PROVIDER", "placeholder")}
