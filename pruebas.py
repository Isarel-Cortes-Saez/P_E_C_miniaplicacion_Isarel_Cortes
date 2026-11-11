"""Pruebas automatizadas sobre copias temporales, sin alterar los datos reales."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import migrar_usuarios
from seguridad import crear_hash, verificar_clave


class PruebasInventario(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        carpeta = Path(self.temporal.name)
        self.archivo_inventario = carpeta / "inventario.json"
        self.archivo_usuarios = carpeta / "usuarios.json"
        self.archivo_log = carpeta / "auditoria.jsonl"
        # Cada prueba comienza con P001 = 10, aunque la entrega final conserve 20.
        datos = json.loads((app.RAIZ / "inventario.json").read_text(encoding="utf-8"))
        next(x for x in datos if x["id"] == "P001")["cantidad"] = 10
        self.archivo_inventario.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.archivo_usuarios.write_bytes((app.RAIZ / "usuarios.json").read_bytes())
        for variable, ruta in (
            ("DATOS", self.archivo_inventario),
            ("USUARIOS", self.archivo_usuarios),
            ("LOG", self.archivo_log),
        ):
            parche = patch.object(app, variable, ruta)
            parche.start()
            self.addCleanup(parche.stop)

    def cantidad(self):
        productos = json.loads(self.archivo_inventario.read_text(encoding="utf-8"))
        return next(x["cantidad"] for x in productos if x["id"] == "P001")

    def llamada(self, funcion, *args):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            retorno = funcion(*args)
        return retorno, salida.getvalue()

    def admin(self):
        sesion, _ = self.llamada(app.autenticar, "admin", "AdminDemo2700!")
        self.assertEqual(sesion["rol"], "admin")
        return sesion

    def usuario(self):
        sesion, _ = self.llamada(app.autenticar, "user", "UserDemo2700!")
        self.assertEqual(sesion["rol"], "user")
        return sesion

    def eventos(self):
        return [json.loads(x) for x in self.archivo_log.read_text(encoding="utf-8").splitlines()]

    def test_01_usuarios_tienen_hash_argon2id_sin_clave(self):
        usuarios = json.loads(self.archivo_usuarios.read_text(encoding="utf-8"))
        self.assertEqual(len(usuarios), 2)
        self.assertTrue(all("clave" not in u and u["hash"].startswith("$argon2id$") for u in usuarios))
        self.assertTrue(verificar_clave(usuarios[0]["hash"], "AdminDemo2700!"))
        self.assertFalse(verificar_clave(usuarios[0]["hash"], "no_es_la_clave"))
        self.assertNotEqual(crear_hash("UserDemo2700!"), crear_hash("UserDemo2700!"))

    def test_02_login_exito_error_e_inexistente(self):
        self.assertIsNotNone(self.admin())
        incorrecta, aviso_1 = self.llamada(app.autenticar, "admin", "mal")
        inexistente, aviso_2 = self.llamada(app.autenticar, "inexistente", "mal")
        self.assertIsNone(incorrecta)
        self.assertIsNone(inexistente)
        self.assertEqual(aviso_1, aviso_2)
        self.assertEqual([x["resultado"] for x in self.eventos()], ["exitoso", "fallido", "fallido"])

    def test_03_autorizacion_directa_y_consulta_sin_sesion(self):
        sesion = self.usuario()
        inicial = self.archivo_inventario.read_bytes()
        for quien in (sesion, None):
            resultado, texto = self.llamada(app.modificar_cantidad, quien, "P001", "99")
            self.assertFalse(resultado)
            self.assertIn("Acceso denegado", texto)
        resultado, texto = self.llamada(app.consultar_inventario, None)
        self.assertFalse(resultado)
        self.assertIn("Acceso denegado", texto)
        self.assertEqual(self.archivo_inventario.read_bytes(), inicial)
        ultimos = self.eventos()[-2:]
        self.assertEqual([x["resultado"] for x in ultimos], ["rechazado_sin_autorizacion"] * 2)
        self.assertEqual([x["nueva"] for x in ultimos], [99, 99])
        self.assertEqual(ultimos[-1]["usuario"], "sin_sesion")

    def test_04_cinco_cantidades_invalidas_no_cambian_archivo(self):
        sesion = self.admin()
        inicial = self.archivo_inventario.read_bytes()
        for valor in ("-1", "1001", "abc", "2.5", ""):
            with self.subTest(entrada=valor):
                resultado, texto = self.llamada(app.modificar_cantidad, sesion, "P001", valor)
                self.assertFalse(resultado)
                self.assertIn("Cantidad", texto)
                self.assertEqual(self.archivo_inventario.read_bytes(), inicial)

    def test_05_limites_validos_y_restauracion_a_10(self):
        sesion = self.admin()
        for valor, esperado in (("0", 0), ("1000", 1000), ("10", 10)):
            with self.subTest(entrada=valor):
                correcto, _ = self.llamada(app.modificar_cantidad, sesion, "P001", valor)
                self.assertTrue(correcto)
                self.assertEqual(self.cantidad(), esperado)

    def test_06_consulta_ambos_y_cambio_p999(self):
        admin, user = self.admin(), self.usuario()
        for sesion in (admin, user):
            resultado, texto = self.llamada(app.consultar_inventario, sesion)
            self.assertTrue(resultado)
            self.assertIn("P001 Teclado 10", texto)
        correcto, _ = self.llamada(app.modificar_cantidad, admin, "P001", "20")
        self.assertTrue(correcto)
        cantidad_antes = self.archivo_inventario.read_bytes()
        incorrecto, texto = self.llamada(app.modificar_cantidad, admin, "P999", "5")
        self.assertFalse(incorrecto)
        self.assertIn("no existe", texto)
        self.assertEqual(cantidad_antes, self.archivo_inventario.read_bytes())
        self.assertEqual(self.cantidad(), 20)

    def test_07_persistencia_en_archivo(self):
        sesion = self.admin()
        self.llamada(app.modificar_cantidad, sesion, "P001", "20")
        contenido_disco = json.loads(self.archivo_inventario.read_text(encoding="utf-8"))
        self.assertEqual(contenido_disco[0]["cantidad"], 20)
        productos_releidos, _ = self.llamada(app.cargar_inventario)
        self.assertEqual(productos_releidos[0]["cantidad"], 20)

    def test_08_log_jsonl_formato_y_sin_secretos(self):
        sesion = self.admin()
        self.llamada(app.autenticar, "admin", "incorrecta")
        self.llamada(app.modificar_cantidad, sesion, "P001", "20")
        self.llamada(app.modificar_cantidad, self.usuario(), "P001", "99")
        eventos = self.eventos()
        self.assertTrue(all(set(("fecha_hora", "usuario", "accion", "resultado")) <= x.keys() for x in eventos))
        self.assertEqual(eventos[2]["anterior"], 10)
        self.assertEqual(eventos[2]["nueva"], 20)
        self.assertEqual(eventos[-1]["anterior"], 20)
        self.assertEqual(eventos[-1]["nueva"], 99)
        texto = self.archivo_log.read_text(encoding="utf-8")
        self.assertNotIn("AdminDemo2700!", texto)
        self.assertNotIn("UserDemo2700!", texto)
        self.assertNotIn("$argon2", texto)

    def test_09_archivo_ausente_json_invalido_y_restauracion(self):
        sesion = self.admin()
        respaldo = self.archivo_inventario.read_bytes()
        self.archivo_inventario.unlink()
        resultado, aviso = self.llamada(app.consultar_inventario, sesion)
        self.assertFalse(resultado)
        self.assertIn("no se encontró", aviso)
        self.assertFalse(self.archivo_inventario.exists())
        self.archivo_inventario.write_text("ESTO NO ES JSON", encoding="utf-8")
        resultado, aviso = self.llamada(app.modificar_cantidad, sesion, "P001", "20")
        self.assertFalse(resultado)
        self.assertIn("no contiene JSON válido", aviso)
        self.assertEqual(self.archivo_inventario.read_text(encoding="utf-8"), "ESTO NO ES JSON")
        self.archivo_inventario.write_bytes(respaldo)
        resultado, texto = self.llamada(app.consultar_inventario, sesion)
        self.assertTrue(resultado)
        self.assertIn("P001 Teclado 10", texto)

    def test_10_migracion_funciona_y_es_idempotente(self):
        sin_migrar = [
            {"usuario": "admin", "rol": "admin", "clave": "AdminDemo2700!"},
            {"usuario": "user", "rol": "user", "clave": "UserDemo2700!"},
        ]
        self.archivo_usuarios.write_text(json.dumps(sin_migrar), encoding="utf-8")
        with patch.object(migrar_usuarios, "USUARIOS", self.archivo_usuarios):
            self.assertTrue(self.llamada(migrar_usuarios.migrar)[0])
            migrados = json.loads(self.archivo_usuarios.read_text(encoding="utf-8"))
            self.assertTrue(all("clave" not in x for x in migrados))
            self.assertFalse(self.llamada(migrar_usuarios.migrar)[0])
        self.assertIsNotNone(self.admin())


if __name__ == "__main__":
    unittest.main(verbosity=2)
