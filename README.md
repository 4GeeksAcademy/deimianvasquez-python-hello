# ☕ Asistente de Inventario para Cafetería

Sistema de gestión de inventario con API REST y agente de IA conversacional para la cafetería de Carla.

## 🚀 Cómo iniciar

Necesitas **dos terminales** abiertos al mismo tiempo.

### Terminal 1 — Iniciar la API

```bash
uv run uvicorn api.app:app --reload
```

La API arrancará en `http://127.0.0.1:8000`.

### Terminal 2 — Iniciar el agente

```bash
uv run python agent.py
```

## ⚙️ Configuración

Crea un archivo `.env` en la raíz con tu clave de API de Groq:

```
GROQ_API_KEY=tu_clave_aqui
```

## 📦 Endpoints de la API

| Método | Ruta                    | Descripción                                  |
|--------|-------------------------|----------------------------------------------|
| GET    | `/inventory`            | Lista todos los productos                    |
| POST   | `/inventory`            | Añade un nuevo producto                      |
| PATCH  | `/inventory/{id}`       | Actualiza stock (delta positivo/negativo)    |
| GET    | `/inventory/alerts`     | Productos con stock bajo el umbral (def: 10) |

## 🧠 Uso del agente

Escribe en lenguaje natural cosas como:

- _"Agrega 30 unidades de leche de avena"_
- _"Vendimos 12 bolsas de arábica hoy"_
- _"Acaban de llegar 5 kg de café tostado"_
- _"¿Qué productos están por agotarse?"_
- _"Muéstrame todo el inventario"_

Escribe `salir` para terminar la conversación.

## 📁 Archivos del proyecto

```
api/
  app.py              ← API FastAPI
agent.py              ← Agente con bucle Observar→Pensar→Actuar
products.csv          ← Datos del inventario (se crea automáticamente)
conversation_log.csv  ← Registro de conversaciones (append-only)
.env                  ← Tu clave de API (no se sube a Git)
```
