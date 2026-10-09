"""Cliente mínimo de la API de Mercado Pago usando `requests`.

Endpoints usados (Checkout Pro, API de Preferencias):
  POST /checkout/preferences  → crea la preferencia y devuelve init_point
  GET  /v1/payments/{id}      → consulta el estado real de un pago
"""
import requests
from flask import current_app

API = "https://api.mercadopago.com"


class MPError(Exception):
    def __init__(self, mensaje, status=None):
        super().__init__(mensaje)
        self.status = status


def _request(method, path, **kwargs):
    token = current_app.config["MP_ACCESS_TOKEN"]
    if not token:
        raise MPError("Falta configurar MP_ACCESS_TOKEN (ver README).")
    try:
        r = requests.request(method, API + path, timeout=15,
                             headers={"Authorization": f"Bearer {token}"}, **kwargs)
    except requests.RequestException as e:
        raise MPError(f"No se pudo contactar a Mercado Pago: {e}")
    if not r.ok:
        raise MPError(f"Mercado Pago respondió {r.status_code}: {r.text[:200]}", r.status_code)
    return r.json()


def crear_preferencia(pedido, back_url):
    """Crea la preferencia de un pedido. `external_reference` vincula el pago con el pedido."""
    cfg = current_app.config
    body = {
        "items": [{
            "id": str(i.producto_id), "title": i.producto.nombre, "quantity": i.cantidad,
            "unit_price": float(i.precio_unitario), "currency_id": cfg["MP_CURRENCY"],
        } for i in pedido.items],
        "external_reference": f"pedido-{pedido.id}",
        "back_urls": {"success": back_url, "failure": back_url, "pending": back_url},
        "statement_descriptor": "SIMULADOR",
    }
    if cfg["MP_AUTO_RETURN"]:
        body["auto_return"] = "approved"
    if cfg["MP_NOTIFICATION_URL"]:
        body["notification_url"] = cfg["MP_NOTIFICATION_URL"]
    return _request("POST", "/checkout/preferences", json=body)


def obtener_pago(payment_id):
    """Consulta un pago. Siempre se usa esta fuente, nunca los datos de la URL de retorno."""
    return _request("GET", f"/v1/payments/{payment_id}")
