"""
product_listing_generator.py
Lab día 8 (Ironhack): generar fichas de producto a partir de una imagen y sus datos.

Flujo: datos + imagen -> Python -> API (Gemini en modo compatible con OpenAI) -> JSON -> validación -> listings.json

Nota: el enunciado usa ChatGPT. Aquí se usa Gemini (nivel gratuito) con la misma
biblioteca `openai`, cambiando solo `base_url`, el nombre del modelo y la clave.
La clave se lee del archivo .env y nunca se escribe en el código.
"""

# 1. Cargar bibliotecas
import os
import json
import time
import base64

import openai
from dotenv import load_dotenv
from openai import OpenAI

# 2. Leer la clave del .env (sin mostrarla)
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Error controlado: sin clave no tiene sentido continuar
    raise SystemExit("ERROR: falta GEMINI_API_KEY en el archivo .env")

# 3. Crear el cliente apuntando a Gemini (Step 1)
client = OpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
MODEL = "gemini-3.5-flash-lite"

# 4. Datos de los productos (Step 2)
products = [
    {"id": 1, "name": "Taza esmaltada vintage", "price": 12.99,
     "category": "Hogar", "image_path": "images/taza.jpg"},
    {"id": 2, "name": "Zapatillas deportivas", "price": 59.90,
     "category": "Calzado", "image_path": "images/zapatillas.jpg"},
    {"id": 3, "name": "Auriculares inalámbricos", "price": 79.99,
     "category": "Electrónica", "image_path": "images/auriculares.jpg"},
]


# 5. Codificar imagen a base64 (Step 3)
def encode_image_to_base64(image_path):
    """Lee la imagen en binario y la devuelve como texto base64."""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


# 6. Crear el prompt (Step 4)
def create_product_listing_prompt(name, price, category):
    """Devuelve el texto de instrucciones para la IA con los datos del producto."""
    return f"""Eres un redactor con mucha experiencia, preciso y con pocas palabras, que crea copys atractivos para el consumidor y para Google. Analiza la imagen y crea una ficha de producto en español.

Datos del producto:
- Nombre: {name}
- Precio: {price:.2f} €
- Categoría: {category}

Devuelve SOLO un JSON con esta estructura:
{{
  "title": "título SEO, máximo 60 caracteres",
  "description": "descripción persuasiva de 150-200 palabras",
  "features": ["5 a 7 características"],
  "keywords": "10-15 palabras clave separadas por comas"
}}

Menciona colores, materiales y detalles que veas en la imagen."""


# 7. Llamar a la API con imagen + prompt (Step 5)
def call_model(prompt, encoded_image):
    """Envía el prompt y la imagen al modelo y devuelve el texto de la respuesta."""
    response = client.chat.completions.create(
        model=MODEL,
        timeout=60,  # si en 60 s no responde, error en lugar de esperar para siempre
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}},
                ],
            }
        ],
    )
    return response.choices[0].message.content


# 8. Convertir la respuesta en diccionario y validarla (Step 5)
REQUIRED_FIELDS = ["title", "description", "features", "keywords"]


def parse_listing(raw_text):
    """Recorta desde la primera { hasta la última } (quita ```json ... ```) y la convierte en diccionario."""
    start = raw_text.find("{")
    end = raw_text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("la respuesta no contiene ningún JSON")
    listing = json.loads(raw_text[start:end])
    missing = [f for f in REQUIRED_FIELDS if f not in listing]
    if missing:
        raise ValueError(f"faltan campos en la respuesta: {missing}")
    return listing


# 9. Generar la ficha de UN producto, con manejo de errores (Step 6)
def generate_listing(product):
    """Devuelve un diccionario con el producto y su ficha, o con el error ocurrido."""
    result = {"id": product["id"], "name": product["name"],
              "price": product["price"], "category": product["category"]}
    try:
        encoded = encode_image_to_base64(product["image_path"])
        prompt = create_product_listing_prompt(product["name"], product["price"], product["category"])
        raw_text = call_model(prompt, encoded)
        result["listing"] = parse_listing(raw_text)
        result["status"] = "ok"
    except FileNotFoundError:
        result["status"] = "error"
        result["error"] = f"imagen no encontrada: {product['image_path']}"
    except openai.AuthenticationError as e:          # 401: clave no válida
        result["status"] = "error"
        result["error"] = f"autenticación: {e}"
    except openai.BadRequestError as e:              # 400: petición incorrecta (Gemini también lo usa para clave no válida)
        result["status"] = "error"
        result["error"] = f"petición incorrecta: {e}"
    except openai.RateLimitError as e:               # 429: demasiadas peticiones o sin cuota
        result["status"] = "error"
        result["error"] = f"límite de uso: {e}"
    except (openai.APITimeoutError, openai.APIConnectionError) as e:   # sin respuesta o sin conexión
        result["status"] = "error"
        result["error"] = f"conexión o tiempo agotado: {e}"
    except openai.InternalServerError as e:          # 5xx: problema del servidor (ej. 503 saturado)
        result["status"] = "error"
        result["error"] = f"servidor no disponible: {e}"
    except (json.JSONDecodeError, ValueError) as e:  # la IA no devolvió un JSON válido o le faltan campos
        result["status"] = "error"
        result["error"] = f"respuesta mal formada: {e}"
    return result


# 10. Procesar todos los productos y guardar los resultados (Step 6)
if __name__ == "__main__":
    results = []
    for product in products:
        print(f"Procesando {product['id']}: {product['name']} ...")
        result = generate_listing(product)
        if result["status"] == "ok":
            print(f"  OK -> {result['listing']['title']}")
        else:
            print(f"  ERROR -> {result['error']}")
        results.append(result)
        time.sleep(2)  # pausa entre llamadas para no saturar la API

    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\nTerminado: {ok}/{len(results)} fichas correctas. Guardado en listings.json")
