"""Ejercicio 4: llamadas directas sin autorización a funciones protegidas."""
import app


def cantidad_p001():
    productos = app.cargar_inventario()
    if productos is None:
        return None
    return next(p["cantidad"] for p in productos if p["id"] == "P001")


def main():
    nombre = input("Nombre del estudiante: ").strip()
    print("Estudiante:", nombre)
    original = cantidad_p001()
    print("P001 antes:", original)
    sesion = app.autenticar("user", "UserDemo2700!")
    print("Intento user, P001 -> 99:", app.modificar_cantidad(sesion, "P001", "99"))
    print("Intento None, P001 -> 99:", app.modificar_cantidad(None, "P001", "99"))
    print("Consulta con None:", app.consultar_inventario(None))
    final = cantidad_p001()
    print("P001 después:", final)
    print("¿Inventario sin cambios?:", original == final)


if __name__ == "__main__":
    main()
