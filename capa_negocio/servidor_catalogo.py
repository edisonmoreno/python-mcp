# ./capa_negocio/servidor_catalogo.py
import os
import sys
import time
import json
import sqlite3
import logging
from fastmcp import FastMCP

# Configurar logs
logging.basicConfig(stream=sys.stderr,
                    level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

mcp = FastMCP("CatalogoUniversal")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "capa_datos", "catalogo.db")
print(f"Ruta.db: {DB_PATH}", file=sys.stderr)


def _buscar_en_catalogo(termino: str, limite: int = 5):
    """Busca en el índice FTS5 de la base de datos."""
    search_start = time.perf_counter()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    palabras = [f"{p}*" for p in termino.split() if p]
    query_fts = " AND ".join(palabras)

    if not query_fts:
        conn.close()
        return []

    cursor.execute(
        "SELECT codigo, nombre FROM buscar_productos WHERE buscar_productos MATCH ? LIMIT ?", (query_fts, limite))
    filas = cursor.fetchall()
    conn.close()

    search_finish = time.perf_counter()
    print(
        f"⏱️ Buscando: {search_finish - search_start:.6f} seg. -> {query_fts}")
    return [{"codigo": cod, "nombre": nom} for cod, nom in filas]


@mcp.tool()
def validar_catalogo(data: str) -> str:
    try:
        search_start = time.perf_counter()
        lista_productos = json.loads(data)
        lista_items = []

        for item in lista_productos:
            input_nombre = item.get("nombre", "").strip()
            input_cantidad = item.get("cantidad", 1)
            if not input_nombre:
                continue

            coincidencias = _buscar_en_catalogo(input_nombre)

            item_res = {
                "status": "OK",
                "message": "Mapeado correctamente.",
                "data": {
                    "busqueda": input_nombre,
                    "codigo": None,
                    "nombre": None,
                    "cantidad": input_cantidad,
                }
            }

            if len(coincidencias) == 0:
                item_res.update({
                    "status": "NO_ENCONTRADO",
                    "message": f"No se encontró '{input_nombre}'."
                })
            elif len(coincidencias) > 1:
                item_res.update({
                    "status": "REQUIERE_CONFIRMACION",
                    "message": f"Múltiples opciones para '{input_nombre}'.",
                })
                item_res["data"].update({
                    "candidatos": coincidencias
                })
            else:
                # Extraemos el primer resultado de la lista de forma segura
                producto_encontrado = coincidencias[0]
                item_res["data"].update({
                    "codigo": producto_encontrado["codigo"],
                    "nombre": producto_encontrado["nombre"]
                })

            lista_items.append(item_res)

        response = {
            "productos": lista_items
        }
        search_finish = time.perf_counter()
        print(
            f"⏱️ Validando: {search_finish - search_start:.6f} seg. -> {response}")
        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        logging.error(f"💥 Error en la herramienta: {str(e)}")
        return json.dumps([{"producto_buscado": "Error", "estado": "ERROR_INTERNO", "mensaje": str(e)}])


if __name__ == "__main__":
    # main solo se ejecutará si se corre el script directamente con: python servidor_catalogo.py
    print("Corriendo servidor_catalogo de forma directa...", file=sys.stderr)
    mcp.run()
