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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "catalogo.db")
print(f"Ruta.db: {DB_PATH}", file=sys.stderr)


def inicializar_base_de_datos():
    """Inicializa la base de datos de forma segura. Si no existe, la CREA automáticamente."""
    print(
        f"🚀 [SERVIDOR MCP] Inicializando base de datos en: {DB_PATH}", file=sys.stderr)

    # ✅ sqlite3.connect CREA el archivo catalogo.db si no existe en la carpeta. ¡No saltará error!
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Optimizaciones de velocidad
    cursor.execute("PRAGMA synchronous = OFF")
    cursor.execute("PRAGMA journal_mode = MEMORY")

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS productos (codigo TEXT PRIMARY KEY, nombre TEXT, categoria TEXT)")
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS buscar_productos USING fts5(
            codigo, nombre, categoria, tokenize="porter unicode61 remove_diacritics 1"
        )
    """)
    conn.commit()

    # Verificar si tiene los 100k registros poblados
    cursor.execute("SELECT COUNT(*) FROM productos")
    count = cursor.fetchone()[0]

    if count == 0:
        print(
            "⚡ [SERVIDOR MCP] Catálogo vacío. Generando 100,000 productos de prueba...", file=sys.stderr)

        productos_demo = [
            ("001", "Coca Cola Original 350ml", "Bebidas"),
            ("002", "Coca Cola sin Azúcar 350ml", "Bebidas"),
            ("003", "Postobón Manzana 1.5L", "Bebidas Locales"),
            ("004", "Papas Fritas Margaritas Naturales", "Snacks"),
            ("005", "Cerveza Aguila Original", "Bebidas Locales"),
            ("006", "Pan Aliñado", "Panaderia"),
            ("007", "Yuquitas Fritas", "Snacks"),
            ("008", "Chocolativa", "Dulces"),
            ("009", "Chororamo", "Panaderia"),
            ("010", "Pan Trenza", "Panaderia"),
            ("011", "Cerveza Pilsen", "Panaderia"),
            ("012", "Cerveza Aguila Ligth", "Panaderia"),
            ("013", "Manzana Chilena", "Frutas"),
            ("014", "Chocolate sin Azúcar", "Despensa"),
        ]

        # Generar masivamente los 100k registros en lote
        for i in range(7, 100001):
            productos_demo.append(
                (f"PROD_{i:06d}", f"Producto de Limpieza Número {i} Multiusos", "Limpieza"))

        cursor.execute("BEGIN TRANSACTION")
        cursor.executemany(
            "INSERT INTO productos VALUES (?, ?, ?)", productos_demo)
        cursor.executemany(
            "INSERT INTO buscar_productos VALUES (?, ?, ?)", productos_demo)
        conn.commit()
        print(
            "✅ [SERVIDOR MCP] ¡Éxito! 100,000 productos creados e indexados correctamente.", file=sys.stderr)

    conn.close()


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


# Ejecución inmediata al importar el moódulo()
inicializar_base_de_datos()

if __name__ == "__main__":
    # main solo se ejecutará si se corre el script directamente con: python servidor_catalogo.py
    print("Corriendo servidor_catalogo de forma directa...", file=sys.stderr)
    mcp.run()
