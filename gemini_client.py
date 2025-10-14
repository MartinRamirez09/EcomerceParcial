# gemini_client.py
import os, time, base64, re, requests
from urllib.parse import quote_plus
from dotenv import load_dotenv, find_dotenv

# Carga del .env (desde donde ejecutas uvicorn)
load_dotenv(find_dotenv(usecwd=True), override=True)

def _slug(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]+', '-', s).strip('-').lower()[:60]

def _save_png(b: bytes, name: str) -> str:
    os.makedirs("media", exist_ok=True)
    filename = f"prod-{_slug(name)}-{int(time.time())}.png"
    path = os.path.join("media", filename)
    with open(path, "wb") as f:
        f.write(b)
    return f"/media/{filename}"

def _fallback_text(nombre_producto: str, descripcion_usuario: str | None, precio: float | None) -> str:
    info = []
    if descripcion_usuario:
        info.append(descripcion_usuario)
    if precio is not None:
        info.append(f"Precio: {precio:.2f}")
    extra = (". " + " | ".join(info)) if info else ""
    return (f"{nombre_producto}: Una propuesta versátil que combina calidad, estilo y rendimiento. "
            f"Ideal para quienes buscan practicidad diaria y un diseño que se luce sin esfuerzo. "
            f"Ofrece una experiencia confiable con detalles que elevan cada uso y un valor que se percibe desde el primer momento{extra}.")

def generar_descripcion(nombre_producto: str, descripcion_usuario: str | None = None, precio: float | None = None) -> str:
    """
    Genera un párrafo de marketing con Gemini si hay API key; si falla, usa fallback local.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[IA] GEMINI_API_KEY no definido. Usando fallback local.")
        return _fallback_text(nombre_producto, descripcion_usuario, precio)

    prompt = (
        "Actúa como copywriter senior. Redacta UN párrafo (80-120 palabras), tono persuasivo y claro, "
        "sin emojis ni listas, evitando clichés. Enfócate en beneficios y diferenciadores reales.\n"
        f"Producto: {nombre_producto}\n"
        f"Notas del vendedor: {descripcion_usuario or '—'}\n"
        f"Precio: {precio if precio is not None else '—'}\n"
        "Entrega SOLO el párrafo."
    )

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            generation_config={"temperature": 0.85, "top_p": 0.9}
        )
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", None)
        if not text and getattr(resp, "candidates", None):
            text = resp.candidates[0].content.parts[0].text
        text = (text or "").strip()
        if not text:
            print("[IA] Gemini devolvió vacío. Usando fallback.")
            return _fallback_text(nombre_producto, descripcion_usuario, precio)
        print("[IA] Descripción generada por Gemini.")
        return text
    except Exception as e:
        print(f"[IA] Error Gemini: {e}. Usando fallback.")
        return _fallback_text(nombre_producto, descripcion_usuario, precio)

def generar_imagen(descripcion_marketing: str, nombre_producto: str) -> str:
    """
    Genera imagen del producto. Soporta:
      - pollinations (sin API key): descarga y guarda PNG en ./media
      - openai (requiere OPENAI_API_KEY): guarda PNG en ./media
      - placeholder (fallback neutro)
    Devuelve la URL servida por FastAPI (/media/...png) o una URL externa.
    """
    provider = os.getenv("IMAGE_API_PROVIDER", "placeholder").lower()

    if provider == "pollinations":
        try:
            w = int(os.getenv("POLLINATIONS_WIDTH", "1024"))
            h = int(os.getenv("POLLINATIONS_HEIGHT", "1024"))
            seed = os.getenv("POLLINATIONS_SEED")
            nologo = os.getenv("POLLINATIONS_NOLOGO", "1")

            prompt = (
                f"Studio product photo, soft light, minimal background, detailed, "
                f"{nombre_producto}. Context: {descripcion_marketing}. No text overlay."
            )
            url = f"https://image.pollinations.ai/prompt/{quote_plus(prompt)}?width={w}&height={h}&nologo={nologo}"
            if seed:
                url += f"&seed={quote_plus(seed)}"

            r = requests.get(url, timeout=120)
            r.raise_for_status()
            return _save_png(r.content, nombre_producto)
        except Exception as e:
            print(f"[IA-IMG] Error Pollinations: {e}. Usando placeholder.")

    if provider == "openai":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            prompt = (
                f"Ultra-detailed studio product photo, soft light, minimal background, "
                f"{nombre_producto}. Context: {descripcion_marketing}. No text overlay."
            )
            resp = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="512x512",              
                response_format="b64_json"
            )
            b64 = resp.data[0].b64_json
            return _save_png(base64.b64decode(b64), nombre_producto)
        except Exception as e:
            print(f"[IA-IMG] Error OpenAI: {e}. Usando placeholder.")

    # Fallback neutro sin texto
    return "https://placehold.co/1024x1024/png"
