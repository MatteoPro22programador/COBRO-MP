"""Pruebas del flujo con la API de Mercado Pago simulada (sin red). Ejecutar: python -m unittest"""
import os, unittest
from unittest.mock import patch, MagicMock

os.environ["MP_ACCESS_TOKEN"] = "TEST-token"
from app import create_app
from extensions import db


def resp(data, status=200):
    m = MagicMock(); m.ok = status < 400; m.status_code = status; m.json.return_value = data; m.text = str(data)
    return m


class Flujo(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(WTF_CSRF_ENABLED=False, SQLALCHEMY_DATABASE_URI="sqlite://")
        with self.app.app_context():
            db.drop_all(); db.create_all()
        self.c = self.app.test_client()
        self.c.post("/auth/registro", data=dict(nombre="A", email="a@a.com", password="123456", confirmar="123456"))
        self.c.post("/auth/login", data=dict(email="a@a.com", password="123456"))
        self.c.post("/productos/nuevo", data=dict(nombre="Taza", descripcion="", precio="10.50", stock=5))
        self.c.post("/pedidos/nuevo", data={"qty_1": "2"})

    def pago(self, status="approved"):
        return {"id": 999, "status": status, "status_detail": "accredited", "transaction_amount": 21.0,
                "currency_id": "ARS", "external_reference": "pedido-1", "payment_method_id": "visa",
                "transaction_details": {"net_received_amount": 19.8}}

    @patch("services.mercadopago.requests.request")
    def test_ciclo_completo(self, rq):
        rq.return_value = resp({"init_point": "https://mp/checkout"})
        r = self.c.post("/pagos/1/pagar")
        self.assertEqual(r.headers["Location"], "https://mp/checkout")
        body = rq.call_args.kwargs["json"]
        self.assertEqual(body["external_reference"], "pedido-1"); self.assertEqual(body["items"][0]["unit_price"], 10.5)

        rq.return_value = resp(self.pago("rejected"))
        r = self.c.get("/pagos/retorno?payment_id=999&status=approved", follow_redirects=True)
        self.assertIn(b"rechazado", r.data)

        rq.return_value = resp(self.pago())
        r = self.c.get("/pagos/retorno?payment_id=999", follow_redirects=True)
        self.assertIn(b"pagado", r.data)

        r = self.c.post("/pagos/1/cobrar", follow_redirects=True)
        self.assertIn(b"cobrado", r.data); self.assertIn(b"19.80", r.data)

    @patch("services.mercadopago.requests.request")
    def test_webhook_y_monto_alterado(self, rq):
        rq.return_value = resp(self.pago())
        self.assertEqual(self.c.post("/pagos/webhook", json={"type": "payment", "data": {"id": "999"}}).status_code, 200)
        self.assertIn(b"pagado", self.c.get("/pedidos/1").data)

    @patch("services.mercadopago.requests.request")
    def test_monto_no_coincide(self, rq):
        p = self.pago(); p["transaction_amount"] = 1.0
        rq.return_value = resp(p)
        r = self.c.get("/pagos/retorno?payment_id=999", follow_redirects=True)
        self.assertIn(b"no coincide", r.data)


if __name__ == "__main__":
    unittest.main()
