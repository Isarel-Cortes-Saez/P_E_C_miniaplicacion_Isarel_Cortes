"""Migra los usuarios ficticios de 'clave' a hashes Argon2id (una sola vez)."""
import json
from pathlib import Path

from seguridad import crear_hash

USUARIOS = Path(__file__).resolve().parent / "usuarios.json"


def migrar():
    usuarios = json.loads(USUARIOS.read_text(encoding="utf-8"))
    actualizados = []
    cambio = False
    for usuario in usuarios:
        if "clave" in usuario:
            actualizados.append({
                "usuario": usuario["usuario"],
                "rol": usuario["rol"],
                "hash": crear_hash(usuario["clave"]),
            })
            cambio = True
        elif "hash" in usuario:
            actualizados.append({
                "usuario": usuario["usuario"],
                "rol": usuario["rol"],
                "hash": usuario["hash"],
            })
        else:
            raise ValueError("Registro sin 'clave' ni 'hash'; no se modifica el archivo.")

    if not cambio:
        print("usuarios.json ya contiene hashes; no se modificó.")
        return False

    # Solo se guarda después de convertir todos los registros satisfactoriamente.
    temporal = USUARIOS.with_name("usuarios.json.tmp")
    try:
        temporal.write_text(
            json.dumps(actualizados, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporal.replace(USUARIOS)
    finally:
        temporal.unlink(missing_ok=True)
    print("Usuarios migrados a hashes Argon2id; campo 'clave' eliminado.")
    return True


if __name__ == "__main__":
    migrar()
