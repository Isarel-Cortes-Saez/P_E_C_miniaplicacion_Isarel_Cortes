"""Ejercicio 9: errores de archivo y restauración con respaldo físico."""
import shutil
import app


def main():
    nombre = input("Nombre del estudiante: ").strip()
    print("Estudiante:", nombre)
    sesion = app.autenticar("admin", "AdminDemo2700!")
    if sesion is None:
        print("No fue posible iniciar la prueba.")
        return

    respaldo = app.RAIZ / "inventario.json.bak"
    if respaldo.exists():
        print("Ya existe inventario.json.bak; resguárdelo antes de esta prueba.")
        return
    # Copia física dentro de esta carpeta, no se toca ningún archivo personal.
    shutil.copy2(app.DATOS, respaldo)
    print("Copia de respaldo creada:", respaldo.name)
    try:
        app.DATOS.unlink()
        print("CASO A: inventario.json ausente")
        print("Resultado consulta:", app.consultar_inventario(sesion))
        print("¿Se recreó?:", app.DATOS.exists())

        app.DATOS.write_text("ESTO NO ES JSON", encoding="utf-8")
        print("CASO B: inventario.json inválido")
        print("Resultado consulta:", app.consultar_inventario(sesion))
        print("¿Se sobrescribió?:", app.DATOS.read_text(encoding="utf-8") != "ESTO NO ES JSON")
    finally:
        shutil.copy2(respaldo, app.DATOS)
        respaldo.unlink()

    print("CASO C: inventario restaurado")
    print("Resultado consulta:", app.consultar_inventario(sesion))


if __name__ == "__main__":
    main()
