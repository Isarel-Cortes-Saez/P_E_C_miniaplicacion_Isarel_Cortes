# Inventario académico seguro (COMP 2700)

**Estudiante:** [Isarel M. Cortés Sáez]

Corrección de la base educativa original, conservando Python, terminal (CLI),
`inventario.json` y `usuarios.json`. No es una aplicación de producción.

## Requisitos

- Python 3.10 o posterior.
- Dependencia: `argon2-cffi>=23.1.0,<26` (en `requirements.txt`).
- No usa base de datos ni servidor web.

## Instalación y ejecución

En Windows PowerShell, desde la carpeta del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

En macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Escriba su nombre cuando el programa lo solicite. Aparecerá en la terminal,
para que pueda tomar las capturas auténticas de Blackboard.

Cuentas **públicas y exclusivamente ficticias**, originales de la tarea:

| Usuario | Clave de demostración | Permisos |
|---|---|---|
| `admin` | `AdminDemo2700!` | Consultar y modificar cantidades |
| `user` | `UserDemo2700!` | Consultar únicamente |

**Importante:** estas claves aparecen aquí solo para reproducir la demostración
académica. `usuarios.json` almacena únicamente hashes Argon2id con salts
aleatorios: no contiene `clave` ni contraseñas legibles. `seguridad.py` es la
implementación proporcionada por el profesor y se integra sin reemplazarla.

## Estructura

| Archivo | Función |
|---|---|
| `app.py` | CLI, autenticación, autorización, validación, persistencia y auditoría |
| `seguridad.py` | Funciones suministradas `crear_hash` y `verificar_clave` |
| `migrar_usuarios.py` | Migra una copia de usuarios originales a hashes; ejecución idempotente |
| `inventario.json` | Tres productos ficticios con `id`, `nombre` y `cantidad` |
| `usuarios.json` | Cuentas ficticias con `usuario`, `rol`, `hash` |
| `auditoria.jsonl` | Eventos registrados realmente durante las pruebas de desarrollo |
| `pruebas.py` | Pruebas automatizadas sobre copias temporales de los datos |
| `prueba_acceso.py` | Guion del ejercicio 4: invocaciones directas sin privilegios |
| `prueba_errores.py` | Guion del ejercicio 9: respaldo, ausencia, JSON inválido, restauración |
| `.gitignore` | Excluye entornos virtuales, cachés y copias de respaldo |

## Ejecución de las pruebas

Desde el entorno Python del proyecto, en Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest -v pruebas
.\.venv\Scripts\python.exe prueba_acceso.py
.\.venv\Scripts\python.exe prueba_errores.py
```

En macOS/Linux, use `.venv/bin/python` en lugar del ejecutable de Windows.
El conjunto `unittest` crea archivos temporales con **P001 = 10** y no altera
el inventario de la entrega. Las otras dos pruebas utilizan el inventario real;
`prueba_acceso.py` no lo modifica y `prueba_errores.py` lo restaura desde
`inventario.json.bak` incluso si falla una consulta.

Para las capturas de los ejercicios 5 a 7, en una copia de trabajo, siga este
orden con la cuenta `admin`:

1. Comience con P001 = 10 (cámbielo a 10 desde el programa si está a 20).
2. Rechace `-1`, `1001`, `abc`, `2.5` y vacío; confirme que nada se modifica.
3. Acepte `0` y `1000`, y restaure P001 a `10`.
4. Como `user`, consulte; como `admin`, cambie P001 de `10` a `20`.
5. Intente P999; compruebe que no se crea.
6. Cierre el programa **por completo** y arránquelo de nuevo; P001 debe seguir a 20.

**Estado de la versión entregada:** P001 = **20**, P002 = 15 y P003 = 5,
para que coincida con la comprobación final de persistencia. No vuelva a guardar
P001 = 10 después de preparar la versión final para GitHub.

## Controles y límites

- Autenticación mediante hashes Argon2id con salt de `argon2-cffi`.
- El rol se comprueba **dentro** de `modificar_cantidad`, no solo en el menú.
- Cantidad: entero decimal de 0 a 1000, inclusive; errores sin interrumpir CLI.
- Log JSONL con fecha/hora, usuario, acción, resultado y detalles no sensibles.
- Un cambio rechazado por `user` incluye cantidad actual y solicitada;
  sin sesión se omite la lectura y `anterior` es `null`.
- Si inventario.json falta o contiene JSON inválido, se muestra un mensaje y no
  se recrea ni se sobrescribe automáticamente.

Limitaciones: permisos aplicados dentro del proceso; una persona con escritura
sobre archivos locales puede modificarlos. No hay protección de archivos del
sistema operativo, cifrado de inventario, MFA, recuperación de cuentas ni
protección externa del log. No se evalúa estructura JSON con campos incorrectos.

## IA, revisión y fuentes

Se utilizó **ChatGPT (OpenAI, GPT-6)** para revisar los TODO de la base,
proponer las modificaciones, generar pruebas y comparar su resultado con el
enunciado. Las sugerencias se verificaron en el entorno de desarrollo con
`python -m unittest -v pruebas` (10 pruebas aprobadas) y una ejecución
interactiva real cerrando y abriendo de nuevo el programa. **El estudiante debe
repetir estas comprobaciones en su propio equipo y tomar las capturas.**

Se descartó confiar solo en ocultar «Modificar» en el menú: eso no protege una
llamada directa a `modificar_cantidad`. También se evitó registrar directamente
entradas arbitrarias en JSONL, para no introducir datos sensibles en el log.

Fuentes de consulta, además del código base y las instrucciones del profesor:

- argon2-cffi, `PasswordHasher`: https://argon2-cffi.readthedocs.io/en/stable/api.html
- Documentación Python de `json`/`JSONDecodeError`: https://docs.python.org/3.13/library/json.html
- GitHub Docs, publicación del proyecto local: https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github

## Publicación y verificación independiente

Cree primero un repositorio **público y vacío** en GitHub, sin README automático.
Desde esta carpeta:

```sh
git init
git branch -M main
git add .
git commit -m "Corregir inventario y controles de seguridad"
git remote add origin https://github.com/TU_USUARIO/inventario-seguro.git
git push -u origin main
git rev-parse HEAD
```

Sustituya `TU_USUARIO` y el nombre del repositorio. El hash devuelto por
`git rev-parse HEAD` permite construir la dirección del commit:
`https://github.com/TU_USUARIO/inventario-seguro/commit/HASH`.

En **otra carpeta**, con el URL real:

```sh
cd ..
git clone https://github.com/TU_USUARIO/inventario-seguro.git inventario-verificacion
cd inventario-verificacion
```

Aplique la instalación anterior desde `inventario-verificacion` y ejecute
`app.py` y las pruebas. Tome capturas legibles con su nombre. No incluya
archivos sensibles reales, `.venv` ni `__pycache__` en el repositorio.
