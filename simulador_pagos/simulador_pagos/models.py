"""Modelos de datos (SQLAlchemy).

Usuario 1─N Producto, Usuario 1─N Pedido, Pedido 1─N ItemPedido N─1 Producto,
Pedido 1─N Pago.
Estados de un pedido: pendiente → pagado → cobrado (o cancelado).
"""
import uuid
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager


def ahora():
    return datetime.now(timezone.utc)


class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    productos = db.relationship("Producto", backref="dueno", lazy=True)
    pedidos = db.relationship("Pedido", backref="usuario", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def cargar_usuario(user_id):
    return db.session.get(Usuario, int(user_id))


class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text, default="")
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    dueno_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)


class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    creado = db.Column(db.DateTime, default=ahora)
    items = db.relationship("ItemPedido", backref="pedido", cascade="all, delete-orphan")
    pagos = db.relationship("Pago", backref="pedido", order_by="Pago.id.desc()")

    @property
    def total(self):
        return sum(i.subtotal for i in self.items)


class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("producto.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    producto = db.relationship("Producto")

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad


class Pago(db.Model):
    """Movimiento. tipo 'pago': pago del comprador en Mercado Pago.
    tipo 'cobro': acreditación al vendedor (neto tras comisiones).
    estado: aprobado / pendiente / rechazado."""
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    metodo = db.Column(db.String(60), nullable=False, default="")
    estado = db.Column(db.String(20), nullable=False)
    motivo = db.Column(db.String(200), default="")
    mp_payment_id = db.Column(db.String(30), unique=True, nullable=True)
    referencia = db.Column(db.String(12), default=lambda: uuid.uuid4().hex[:12].upper())
    creado = db.Column(db.DateTime, default=ahora)
