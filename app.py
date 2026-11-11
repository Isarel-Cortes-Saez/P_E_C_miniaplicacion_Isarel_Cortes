"""Inventario académico en terminal: autenticación, permisos y auditoría."""
import json
import re
from datetime import datetime
from getpass import getpass
from pathlib import Path

from seguridad import verificar_clave

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "inventario.json"
USUARIOS = RAIZ / "usuarios.json"
LOG = RAIZ / "auditoria.jsonl"


def cargar_inventario():
    """Devuelve los productos, o None si no se puede leer el JSON."""
    try:
        return json.loads(DATOS.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("Error: no se encontró inventario.json. Restaure el archivo original.")
    except json.JSONDecodeError:
        print("Error: inventario.json no contiene JSON válido. Restaure el archivo original.")
    except (OSError, UnicodeError):
        print("Error: no se pudo leer inventario.json.")
    return None


def guardar_inventario(productos):
    """Guarda cambios de un inventario previamente leído y válido."""
    try:
        DATOS.write_text(
            json.dumps(productos, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return True
    except OSError:
        print("Error: no se pudo guardar inventario.json.")
        return False


def registrar_evento(usuario, accion, resultado, **detalles):
    """Agrega un JSON por línea; acepta solo detalles de inventario."""
    evento = {
        "fecha_hora": datetime.now().astimezone().isoformat(timespec="seconds"),
        "usuario": usuario,
        "accion": accion,
        "resultado": resultado,
    }
    for campo in ("producto", "anterior", "nueva"):
        if campo in detalles:
            evento[campo] = detalles[campo]
    try:
        with LOG.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(evento, ensure_ascii=False) + "\n")
    except OSError:
        print("Aviso: no fue posible registrar el evento de auditoría.")


def autenticar(nombre, clave):
    """Devuelve una sesión únicamente tras verificar el hash de la clave."""
    try:
        usuarios = json.loads(USUARIOS.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        registrar_evento(nombre, "login", "fallido")
        print("Error: no se pudo leer usuarios.json.")
        return None

    for usuario in usuarios:
        if usuario["usuario"] == nombre:
            if verificar_clave(usuario["hash"], clave):
                registrar_evento(nombre, "login", "exitoso")
                return {"usuario": nombre, "rol": usuario["rol"]}
            break

    registrar_evento(nombre, "login", "fallido")
    print("Credenciales incorrectas.")
    return None


def sesion_valida(sesion):
    return (
        isinstance(sesion, dict)
        and isinstance(sesion.get("usuario"), str)
        and bool(sesion["usuario"])
        and sesion.get("rol") in ("admin", "user")
    )


def consultar_inventario(sesion):
    if not sesion_valida(sesion):
        print("Acceso denegado: necesita iniciar sesión.")
        return False
    productos = cargar_inventario()
    if productos is None:
        return False
    for producto in productos:
        print(producto["id"], producto["nombre"], producto["cantidad"])
    return True


def interpretar_entero(entrada):
    """Interpreta un entero sin convertir flotantes ni registrar texto arbitrario."""
    if isinstance(entrada, bool):
        return None
    texto = str(entrada).strip()
    if not re.fullmatch(r"[+-]?[0-9]+", texto):
        return None
    try:
        return int(texto)
    except ValueError:
        return None


def validar_cantidad(entrada):
    """Admite exclusivamente enteros decimales del 0 al 1000."""
    cantidad = interpretar_entero(entrada)
    if cantidad is None:
        print("Cantidad inválida: escriba un entero entre 0 y 1000.")
        return None
    if not 0 <= cantidad <= 1000:
        print("Cantidad fuera de rango: debe estar entre 0 y 1000.")
        return None
    return cantidad


def modificar_cantidad(sesion, identificador, entrada):
    # Comprobación de permisos dentro de la operación, no solo en el menú.
    if not sesion_valida(sesion) or sesion["rol"] != "admin":
        nombre = sesion.get("usuario", "sin_sesion") if isinstance(sesion, dict) else "sin_sesion"
        anterior = None
        # 'user' sí puede consultar: se anota la cantidad actual sin modificarla.
        # Sin sesión no se accede al archivo y 'anterior' queda en null.
        if sesion_valida(sesion):
            productos = cargar_inventario()
            if productos is not None:
                anterior = next(
                    (p["cantidad"] for p in productos if p["id"] == identificador), None
                )
        registrar_evento(
            nombre, "modificar", "rechazado_sin_autorizacion",
            producto=identificador, anterior=anterior, nueva=interpretar_entero(entrada),
        )
        print("Acceso denegado: solo admin puede modificar cantidades.")
        return False

    cantidad = validar_cantidad(entrada)
    if cantidad is None:
        registrar_evento(
            sesion["usuario"], "modificar", "cantidad_invalida",
            producto=identificador, anterior=None, nueva=interpretar_entero(entrada),
        )
        return False

    productos = cargar_inventario()
    if productos is None:
        return False

    for producto in productos:
        if producto["id"] == identificador:
            anterior = producto["cantidad"]
            producto["cantidad"] = cantidad
            if not guardar_inventario(productos):
                registrar_evento(
                    sesion["usuario"], "modificar", "error_escritura",
                    producto=identificador, anterior=anterior, nueva=cantidad,
                )
                return False
            registrar_evento(
                sesion["usuario"], "modificar", "exitoso",
                producto=identificador, anterior=anterior, nueva=cantidad,
            )
            print("Cantidad actualizada.")
            return True

    registrar_evento(
        sesion["usuario"], "modificar", "producto_inexistente",
        producto=identificador, anterior=None, nueva=cantidad,
    )
    print(f"Producto {identificador} no existe. No se modificó el inventario.")
    return False


def main():
    print("Inventario académico — versión corregida")
    estudiante = input("Escriba su nombre: ").strip()
    print("Estudiante:", estudiante)
    sesion = None
    while True:
        if sesion is None:
            nombre = input("Usuario (o salir): ").strip()
            if nombre == "salir":
                break
            sesion = autenticar(nombre, getpass("Contraseña de prueba: "))
            continue
        if sesion["rol"] == "admin":
            print("1. Consultar | 2. Modificar | 3. Cerrar sesión | 0. Salir")
        else:
            print("1. Consultar | 3. Cerrar sesión | 0. Salir")
        opcion = input("Opción: ").strip()
        if opcion == "1":
            consultar_inventario(sesion)
        elif opcion == "2":
            identificador = input("ID del producto: ").strip()
            entrada = input("Nueva cantidad: ")
            modificar_cantidad(sesion, identificador, entrada)
        elif opcion == "3":
            sesion = None
        elif opcion == "0":
            break
        else:
            print("Opción inválida.")


if __name__ == "__main__":
    main()
