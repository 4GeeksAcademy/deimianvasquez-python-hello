from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import csv
import os

CSV_FILE = os.path.join(os.path.dirname(__file__), "..", "products.csv")

app = FastAPI(title="Cafetería Inventory API")


# ─── Models ───────────────────────────────────────────────────────
class ProductCreate(BaseModel):
    name: str
    quantity: float
    unit: str  # ej: "unidades", "kg", "litros", "bolsas"
    price: float  # precio por unidad


class ProductOut(BaseModel):
    id: int
    name: str
    quantity: float
    unit: str
    price: float


class ProductPatch(BaseModel):
    delta: float  # positivo = entrada, negativo = salida


# ─── CSV helpers ─────────────────────────────────────────────────
def load_products() -> list[dict]:
    """Lee products.csv y devuelve lista de productos."""
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_products(products: list[dict]):
    """Escribe la lista completa de productos a products.csv."""
    fieldnames = ["id", "name", "quantity", "unit", "price"]
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)


def next_id(products: list[dict]) -> int:
    """Genera un nuevo ID numérico auto-incremental."""
    if not products:
        return 1
    return max(int(p["id"]) for p in products) + 1


# ─── Endpoints ────────────────────────────────────────────────────
@app.get("/inventory", response_model=list[ProductOut])
def get_inventory():
    """Devuelve la lista completa de productos."""
    products = load_products()
    return [
        ProductOut(id=int(p["id"]), name=p["name"],
                   quantity=float(p["quantity"]), unit=p["unit"],
                   price=float(p["price"]))
        for p in products
    ]


@app.post("/inventory", response_model=ProductOut, status_code=201)
def add_product(product: ProductCreate):
    """Añade un nuevo producto al inventario."""
    products = load_products()
    new_id = next_id(products)
    new_product = {
        "id": str(new_id),
        "name": product.name,
        "quantity": str(product.quantity),
        "unit": product.unit,
        "price": str(product.price),
    }
    products.append(new_product)
    save_products(products)
    return ProductOut(id=new_id, name=product.name,
                      quantity=product.quantity, unit=product.unit, price=product.price)


@app.patch("/inventory/{product_id}", response_model=ProductOut)
def update_stock(product_id: int, patch: ProductPatch):
    """Actualiza el stock de un producto aplicando un delta (positivo o negativo)."""
    products = load_products()
    for p in products:
        if int(p["id"]) == product_id:
            current_qty = float(p["quantity"])
            new_qty = current_qty + patch.delta
            if new_qty < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"No hay suficiente stock. Actual: {current_qty}, "
                           f"intentaste restar: {abs(patch.delta)}"
                )
            p["quantity"] = str(new_qty)
            save_products(products)
            return ProductOut(
                id=int(p["id"]), name=p["name"],
                quantity=new_qty, unit=p["unit"],
                price=float(p["price"])
            )
    raise HTTPException(status_code=404, detail="Producto no encontrado")


@app.get("/inventory/alerts", response_model=list[ProductOut])
def get_alerts(threshold: float = Query(10.0, description="Umbral de stock mínimo")):
    """Devuelve productos con cantidad por debajo del umbral."""
    products = load_products()
    alerts = [
        ProductOut(id=int(p["id"]), name=p["name"],
                   quantity=float(p["quantity"]), unit=p["unit"],
                   price=float(p["price"]))
        for p in products
        if float(p["quantity"]) < threshold
    ]
    return alerts
