# Simulador de Pago/Cobro con Flask y Mercado Pago

Aplicación web desarrollada en **Python + Flask** que simula el ciclo de **pago y cobro** de una
tienda en línea. El comprador paga mediante **Checkout Pro de Mercado Pago** (entorno de pruebas)
y el vendedor realiza el **cobro** verificando la acreditación real del dinero a través de la API.

Ciclo de vida de un pedido: `pendiente → pagado → cobrado` (o `cancelado`).

---

## 1. Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| Python 3.10+ | Lenguaje base |
| Flask | Framework web y fábrica de la aplicación |
| Flask-SQLAlchemy | ORM y modelo de datos (SQLite) |
| Flask-Login | Registro, inicio y cierre de sesión |
| Flask-WTF / WTForms | Formularios y protección CSRF |
| Jinja2 | Renderizado de plantillas HTML |
| requests | Cliente HTTP para la API de Mercado Pago |
| python-dotenv | Carga de credenciales desde `.env` |
| SQLite | Base de datos de desarrollo |
| unittest | Pruebas automatizadas del flujo |

---

## 2. Funcionalidades

### Autenticación de usuarios (Flask-Login)
- Registro de usuarios con validación de correo y contraseña.
- Inicio y cierre de sesión.
- Contraseñas almacenadas con hash (`werkzeug.security`).

### Gestión de productos (CRUD)
- Crear, listar, editar y eliminar productos.
- Cada producto tiene nombre, descripción, precio y stock.
- Solo el creador puede editar o eliminar sus propios productos.
- Un producto con pedidos asociados no se elimina (se sugiere poner el stock en 0).

### Sistema de pedidos
- Creación de pedidos seleccionando productos con stock disponible.
- El stock se descuenta al crear el pedido y se repone al cancelarlo.
- Vista de detalle con ítems, subtotales y total.
- Cancelación de pedidos pendientes.

### Simulador de pago/cobro (Mercado Pago Checkout Pro)
- **Pagar:** crea una preferencia (`POST /checkout/preferences`) y redirige al checkout de MP.
- **Retorno:** al volver del checkout, la app **no confía en la URL**; consulta
  `GET /v1/payments/{id}` y valida monto y moneda antes de actualizar el pedido.
- **Webhook:** recibe notificaciones de MP y revalida el pago contra la API (idempotente).
- **Cobrar:** verifica que el pago siga aprobado y registra el **neto acreditado**
  (`net_received_amount`, ya descontadas las comisiones).
- **Historial de movimientos:** lista todos los pagos y cobros del usuario.

### Modelo de datos (SQLAlchemy)
- `Usuario 1─N Producto`, `Usuario 1─N Pedido`.
- `Pedido 1─N ItemPedido N─1 Producto`.
- `Pedido 1─N Pago` (tipo `pago` o `cobro`, con `mp_payment_id` y referencia única).

---

## 3. Estructura del proyecto

```
simulador_pagos/
├── app.py                      # Fábrica de la aplicación y punto de entrada
├── config.py                   # Configuración (carga .env) y credenciales MP
├── extensions.py               # Instancias de Flask-SQLAlchemy, Login, CSRF
├── models.py                   # Modelos: Usuario, Producto, Pedido, ItemPedido, Pago
├── forms.py                    # Formularios Flask-WTF
├── requirements.txt            # Dependencias
├── .env.example                # Plantilla de variables de entorno
├── services/
│   └── mercadopago.py          # Cliente de la API de Mercado Pago
├── routes/
│   ├── auth.py                 # Registro, login, logout
│   ├── productos.py            # CRUD de productos
│   ├── pedidos.py              # Creación y gestión de pedidos
│   └── pagos.py                # pagar, retorno, webhook, cobrar, historial
├── templates/                  # Plantillas Jinja2
│   ├── base.html
│   ├── _macros.html
│   ├── auth/
│   ├── productos/
│   ├── pedidos/
│   └── pagos/
├── static/
│   └── style.css               # Estilos
└── tests/
    └── test_mp.py              # Pruebas del flujo con la API simulada
```

---

## 4. Requisitos

- Python 3.10 o superior.
- Una cuenta de desarrollador en Mercado Pago (https://www.mercadopago.com.ar/developers).
- Conexión a internet para el flujo de pago.

---

## 5. Instalación de dependencias

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

---

## 6. Configuración

### 6.1 Credenciales de Mercado Pago

1. Ingresa a https://www.mercadopago.com.ar/developers y crea una **aplicación**
   (producto: **Checkout Pro**).
2. En **Cuentas de prueba** crea **dos usuarios de prueba**:
   - un **vendedor** (dueño del Access Token con el que corre la app), y
   - un **comprador** (con el que se paga en el checkout).
3. Copia el **Access Token** del vendedor.

> Mercado Pago no permite pagar con la misma cuenta que genera el cobro: el comprador debe ser
> un usuario de prueba distinto. Se recomienda iniciar sesión en el checkout en una ventana de
> incógnito con las credenciales del comprador.

### 6.2 Variables de entorno

Copia la plantilla y completa los valores:

```bash
cp .env.example .env     # Windows: copy .env.example .env
```

Contenido de `.env`:

```ini
SECRET_KEY=una-clave-larga-y-aleatoria
MP_ACCESS_TOKEN=APP_USR-xxxxxxxxxxxxxxxx
MP_CURRENCY=ARS
BASE_URL=http://127.0.0.1:5000
# Opcionales (requieren URL pública, ver sección 9):
# MP_AUTO_RETURN=1
# MP_NOTIFICATION_URL=https://tu-url-publica/pagos/webhook
```

---

## 7. Ejecución

```bash
python app.py
```

La aplicación queda disponible en **http://127.0.0.1:5000**.

> Si tenías una base `simulador.db` de una versión anterior, elimínala: la estructura de la tabla
> `pago` cambió. La base se crea automáticamente al iniciar.

---

## 8. Demostración en vivo (guion)

1. **Registro:** crea una cuenta en *Crear cuenta* e inicia sesión.
2. **Producto:** en *Productos* → *Agregar producto*, registra un ítem (ej. "Taza", $10.50, stock 5).
3. **Pedido:** en *Pedidos* → *Crear pedido*, elige cantidades y confirma. El stock se descuenta.
4. **Pago:** abre el pedido y pulsa **Pagar con Mercado Pago**. La app crea la preferencia y
   redirige al checkout.
5. **Checkout:** inicia sesión con el **usuario comprador de prueba** y paga con una tarjeta de
   prueba. El nombre del titular define el resultado:
   - `APRO` → aprobado
   - `OTHE` → rechazado
   - `CONT` → pendiente
   - `FUND` → fondos insuficientes
6. **Retorno:** al pulsar *Volver al sitio*, MP redirige a `/pagos/retorno`. La app consulta el
   pago por API, valida monto/moneda y marca el pedido como **pagado**.
7. **Cobro:** pulsa **Verificar y cobrar**. La app reconsulta el pago, confirma que sigue
   `approved` y registra el **neto** acreditado. El pedido pasa a **cobrado**.
8. **Movimientos:** revisa el historial en *Movimientos* (pago bruto y cobro neto).

---

## 9. Webhook y retorno automático (opcional)

En local, Mercado Pago no puede notificar a `127.0.0.1`. Para probar el webhook expón la app con
una URL pública (ngrok, cloudflared) y define en `.env`:

```ini
BASE_URL=https://tu-url-publica
MP_NOTIFICATION_URL=https://tu-url-publica/pagos/webhook
MP_AUTO_RETURN=1
```

Para producción debe agregarse la validación de la firma `x-signature` de las notificaciones
(no incluida en esta versión).

---

## 10. Pruebas automatizadas

Las pruebas simulan la API de Mercado Pago (sin red) y cubren el ciclo completo, el webhook y la
validación de monto alterado:

```bash
python -m unittest discover -s tests -t .
```

---

## 11. Seguridad

- El estado del pago se toma **siempre** de la API de Mercado Pago, nunca de los parámetros de la
  URL de retorno.
- El `external_reference` (`pedido-<id>`) vincula de forma fiable el pago con el pedido.
- El webhook es **idempotente** y revalida el pago contra la API.
- Los formularios están protegidos con **CSRF** (Flask-WTF).
- El Access Token vive en `.env`, excluido de git mediante `.gitignore`.
