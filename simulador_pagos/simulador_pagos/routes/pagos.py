"""Pago y cobro con Mercado Pago (Checkout Pro).

Flujo:
  1. pagar   → se crea una preferencia y se redirige al comprador a Mercado Pago.
  2. retorno → al volver, se consulta el pago en la API (no se confía en la URL).
  3. webhook → Mercado Pago avisa de cambios de estado (requiere URL pública).
  4. cobrar  → el vendedor verifica la acreditación y registra el neto recibido.
"""
from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user

from extensions import db, csrf
from forms import AccionForm
from models import Pago, Pedido
from routes.pedidos import pedido_propio_o_404
from services import mercadopago as mp

bp = Blueprint("pagos", __name__, url_prefix="/pagos")
PREFIJO = "pedido-"


def _pedido_de_pago(payment):
    """Obtiene el pedido a partir de external_reference del pago."""
    ref = payment.get("external_reference") or ""
    try:
        return db.session.get(Pedido, int(ref[len(PREFIJO):])) if ref.startswith(PREFIJO) else None
    except ValueError:
        return None


def aplicar_pago(pedido, payment):
    """Sincroniza un pago (ya consultado a la API) con la base. Es idempotente.
    Devuelve (pago, error)."""
    monto = Decimal(str(payment.get("transaction_amount", 0)))
    if monto != pedido.total or payment.get("currency_id") != current_app.config["MP_CURRENCY"]:
        return None, "El monto o la moneda del pago no coincide con el pedido."
    estado = {"approved": "aprobado", "pending": "pendiente", "in_process": "pendiente",
              "authorized": "pendiente"}.get(payment.get("status"), "rechazado")
    pago = Pago.query.filter_by(mp_payment_id=str(payment["id"])).first()
    if not pago:
        pago = Pago(pedido_id=pedido.id, tipo="pago", monto=monto, mp_payment_id=str(payment["id"]))
        db.session.add(pago)
    pago.estado = estado
    pago.metodo = payment.get("payment_method_id") or "mercadopago"
    pago.motivo = payment.get("status_detail") or ""
    if estado == "aprobado" and pedido.estado == "pendiente":
        pedido.estado = "pagado"
    db.session.commit()
    return pago, None


@bp.route("/")
@login_required
def historial():
    pagos = (Pago.query.join(Pedido).filter(Pedido.usuario_id == current_user.id)
             .order_by(Pago.id.desc()).all())
    return render_template("pagos/historial.html", pagos=pagos)


@bp.route("/<int:pedido_id>/pagar", methods=["POST"])
@login_required
def pagar(pedido_id):
    if not AccionForm().validate_on_submit():
        abort(400)
    pedido = pedido_propio_o_404(pedido_id)
    if pedido.estado != "pendiente":
        flash("Este pedido no está pendiente de pago.", "error")
        return redirect(url_for("pedidos.detalle", id=pedido.id))
    back = current_app.config["BASE_URL"].rstrip("/") + url_for("pagos.retorno")
    try:
        pref = mp.crear_preferencia(pedido, back)
    except mp.MPError as e:
        flash(str(e), "error")
        return redirect(url_for("pedidos.detalle", id=pedido.id))
    return redirect(pref["init_point"])


@bp.route("/retorno")
@login_required
def retorno():
    """back_url: Mercado Pago devuelve al comprador aquí con payment_id y status."""
    payment_id = request.args.get("payment_id") or request.args.get("collection_id")
    if not payment_id or payment_id == "null":
        flash("Volviste de Mercado Pago sin completar el pago.", "error")
        return redirect(url_for("pedidos.lista"))
    try:
        payment = mp.obtener_pago(payment_id)
    except mp.MPError as e:
        flash(str(e), "error")
        return redirect(url_for("pedidos.lista"))
    pedido = _pedido_de_pago(payment)
    if not pedido or pedido.usuario_id != current_user.id:
        abort(403)
    pago, error = aplicar_pago(pedido, payment)
    if error:
        flash(error, "error")
    elif pago.estado == "aprobado":
        flash("Pago aprobado por Mercado Pago. El pedido quedó pagado.", "ok")
    elif pago.estado == "pendiente":
        flash("Pago pendiente de acreditación. Se actualizará cuando Mercado Pago lo confirme.", "ok")
    else:
        flash(f"Pago rechazado ({pago.motivo or 'sin detalle'}). Puedes intentarlo de nuevo.", "error")
    return redirect(url_for("pedidos.detalle", id=pedido.id))


@bp.route("/webhook", methods=["POST"])
@csrf.exempt
def webhook():
    """Notificaciones de Mercado Pago. Se revalida siempre contra la API."""
    data = request.get_json(silent=True) or {}
    tipo = data.get("type") or request.args.get("type") or request.args.get("topic")
    pid = (data.get("data") or {}).get("id") or request.args.get("data.id") or request.args.get("id")
    if tipo == "payment" and pid:
        try:
            payment = mp.obtener_pago(pid)
        except mp.MPError as e:
            return ("", 200) if e.status == 404 else ("", 500)
        pedido = _pedido_de_pago(payment)
        if pedido:
            aplicar_pago(pedido, payment)
    return "", 200


@bp.route("/<int:pedido_id>/cobrar", methods=["POST"])
@login_required
def cobrar(pedido_id):
    """Cobro: verifica en la API que el pago sigue aprobado y registra el neto acreditado."""
    if not AccionForm().validate_on_submit():
        abort(400)
    pedido = pedido_propio_o_404(pedido_id)
    pago = next((g for g in pedido.pagos if g.tipo == "pago" and g.estado == "aprobado"), None)
    if pedido.estado != "pagado" or not pago:
        flash("Solo se pueden cobrar pedidos pagados.", "error")
        return redirect(url_for("pedidos.detalle", id=pedido.id))
    try:
        payment = mp.obtener_pago(pago.mp_payment_id)
    except mp.MPError as e:
        flash(str(e), "error")
        return redirect(url_for("pedidos.detalle", id=pedido.id))
    if payment.get("status") != "approved":
        flash(f"El pago figura como '{payment.get('status')}' en Mercado Pago; no se puede cobrar.", "error")
        return redirect(url_for("pedidos.detalle", id=pedido.id))
    bruto = Decimal(str(payment["transaction_amount"]))
    neto = Decimal(str((payment.get("transaction_details") or {}).get("net_received_amount", bruto)))
    db.session.add(Pago(pedido_id=pedido.id, tipo="cobro", monto=neto, estado="aprobado",
                        metodo="Cuenta Mercado Pago",
                        motivo=f"Neto de ${bruto:.2f} bruto (pago MP {pago.mp_payment_id})"))
    pedido.estado = "cobrado"
    db.session.commit()
    flash(f"Cobro registrado: ${neto:.2f} netos acreditados.", "ok")
    return redirect(url_for("pedidos.detalle", id=pedido.id))
