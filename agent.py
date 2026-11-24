"""
Agente de IA para el inventario de cafetería.
Bucle: Observar → Pensar → Actuar → Actualizar → Repetir
"""

import os
import json
import httpx
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ─── Cliente LLM ──────────────────────────────────────────────────
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    raise ValueError("Falta OPENROUTER_API_KEY en el archivo .env")

BASE_URL = os.getenv("BASE_URL", "https://llm.4geeks.ai")
MODEL = os.getenv("MODEL", "online/openrouter/deepseek/deepseek-v4-flash")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)

# ─── Definición de tools ──────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": "Obtiene la lista completa de productos en el inventario.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_product",
            "description": "Añade un nuevo producto al inventario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nombre del producto"},
                    "quantity": {"type": "number", "description": "Cantidad inicial"},
                    "unit": {"type": "string", "description": "Unidad de medida (ej: unidades, kg, litros, bolsas)"},
                    "price": {"type": "number", "description": "Precio por unidad en dólares"},
                },
                "required": ["name", "quantity", "unit", "price"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_stock",
            "description": "Actualiza el stock de un producto. Usa delta positivo para entradas y delta negativo para salidas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "ID del producto a actualizar"},
                    "delta": {"type": "number", "description": "Cambio en stock: positivo para entrada, negativo para salida"},
                },
                "required": ["product_id", "delta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alerts",
            "description": "Obtiene productos con stock por debajo de un umbral. Por defecto 10.",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold": {"type": "number", "description": "Umbral de stock mínimo (default: 10)"},
                },
                "required": [],
            },
        },
    },
]

API_BASE_URL = "http://127.0.0.1:8000"


def call_tool(tool_name: str, arguments: dict) -> str:
    """Ejecuta la tool llamando al endpoint de la API y devuelve el resultado como string."""
    try:
        if tool_name == "get_inventory":
            resp = httpx.get(f"{API_BASE_URL}/inventory", timeout=10)
            return format_response(resp)

        elif tool_name == "add_product":
            resp = httpx.post(
                f"{API_BASE_URL}/inventory",
                json=arguments,
                timeout=10,
            )
            return format_response(resp)

        elif tool_name == "update_stock":
            product_id = arguments.pop("product_id")
            resp = httpx.patch(
                f"{API_BASE_URL}/inventory/{product_id}",
                json=arguments,
                timeout=10,
            )
            return format_response(resp)

        elif tool_name == "get_alerts":
            threshold = arguments.get("threshold", 10)
            resp = httpx.get(
                f"{API_BASE_URL}/inventory/alerts",
                params={"threshold": threshold},
                timeout=10,
            )
            return format_response(resp)

        else:
            return f"Error: tool desconocida '{tool_name}'"
    except httpx.RequestError as e:
        return f"Error de conexión con la API: {e}"


def format_response(resp: httpx.Response) -> str:
    """Formatea la respuesta HTTP como texto (tabla si es lista de productos)."""
    try:
        data = resp.json()
    except Exception:
        return f"Error {resp.status_code}: {resp.text}"

    # Si es una lista de productos, la mostramos como tabla con precio
    if isinstance(data, list) and len(data) > 0 and "name" in data[0]:
        lines = []
        lines.append(f"{'ID':<4} {'Producto':<30} {'Cantidad':<10} {'Unidad':<12} {'Precio':<10}")
        lines.append("-" * 70)
        for p in data:
            price_str = f"${p['price']:.2f}"
            lines.append(f"{p['id']:<4} {p['name']:<30} {p['quantity']:<10} {p['unit']:<12} {price_str:<10}")
        return "\n".join(lines)

    # Si es un solo producto (POST/PATCH)
    if isinstance(data, dict) and "name" in data:
        lines = []
        lines.append(f"{'ID':<4} {'Producto':<30} {'Cantidad':<10} {'Unidad':<12} {'Precio':<10}")
        lines.append("-" * 70)
        price_str = f"${data['price']:.2f}"
        lines.append(f"{data['id']:<4} {data['name']:<30} {data['quantity']:<10} {data['unit']:<12} {price_str:<10}")
        return "\n".join(lines)

    # Para otros casos, devolvemos JSON formateado
    return json.dumps(data, ensure_ascii=False, indent=2)


# ─── Registro de conversación ──────────────────────────────────────
import csv
from datetime import datetime, timezone

LOG_FILE = "conversation_log.csv"


def log_event(actor: str, message: str, tool_call: str = ""):
    """Añade una fila al conversation_log.csv (append-only)."""
    fieldnames = ["actor", "message", "tool_call", "timestamp"]
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "actor": actor,
            "message": message,
            "tool_call": tool_call,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


# ─── Bucle del agente ──────────────────────────────────────────────
SYSTEM_PROMPT = """Eres un asistente de inventario para una cafetería.
Regla de oro: NUNCA inventes productos, cantidades ni datos del inventario.
Siempre que el usuario mencione el inventario, productos o stock, DEBES usar la herramienta get_inventory para obtener los datos reales.
NUNCA respondas con datos del inventario sin antes haber llamado a la herramienta correspondiente.

Puedes:
- Consultar productos (get_inventory)
- Añadir nuevos productos (add_product)
- Actualizar stock (update_stock)
- Ver alertas de stock bajo (get_alerts)

Siempre respondes de forma amable y en español.
Se directo y conciso en tus respuestas.
Cuando un usuario te pida registrar una entrada o salida de stock, usa la herramienta correspondiente.
Si no sabes el ID de un producto, primero consulta el inventario para obtenerlo."""


def run_agent():
    """Bucle principal del agente: Observar → Pensar → Actuar → Actualizar → Repetir."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    print("=" * 50)
    print("🤖 Asistente de inventario de cafetería")
    print("Escribe 'salir' para terminar la conversación.")
    print("=" * 50)

    while True:
        # ─── Observar ─────────────────────────────────────────────
        user_input = input("\n👤 Tú: ").strip()
        if user_input.lower() in ("salir", "exit", "quit"):
            print("🤖 ¡Hasta luego! ☕")
            break

        log_event("user", user_input)
        messages.append({"role": "user", "content": user_input})

        # ─── Pensar → Actuar → Actualizar (bucle interno) ────────
        while True:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )

            choice = response.choices[0]
            msg = choice.message

            # Si el LLM no quiere llamar a ninguna tool, respondemos
            if not msg.tool_calls:
                agent_reply = msg.content or ""
                log_event("agent", agent_reply)
                print(f"\n🤖 {agent_reply}")
                messages.append({"role": "assistant", "content": agent_reply})
                break

            # ─── Actuar: ejecutar cada tool que el LLM pidió ────
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}

                log_event("agent", f"Llamando a tool: {func_name}", tool_call=func_name)

                result = call_tool(func_name, func_args)
                log_event("tool", result, tool_call=func_name)

                # ─── Actualizar: inyectar resultado en el historial ──
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": func_name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                    ],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            # El bucle continúa → el LLM recibe los resultados y decide si llama más tools o responde


if __name__ == "__main__":
    run_agent()