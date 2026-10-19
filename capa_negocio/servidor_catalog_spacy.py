# ./capa_negocio/servidor_catalogo_regex.py
import os
import sqlite3

# 📂 CONFIGURACIÓN DIRECTA DE LA BASE DE DATOS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "catalogo.db")


def _buscar_en_catalogo(termino: str, limite: int = 5):
    """Busca directamente en el índice FTS5 sin pasar por servidores intermedios."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    palabras = [f"{p}*" for p in termino.split() if p]
    query_fts = " AND ".join(palabras)

    if not query_fts:
        conn.close()
        return []

    cursor.execute(
        "SELECT codigo, nombre FROM buscar_productos WHERE buscar_productos MATCH ? LIMIT ?",
        (query_fts, limite)
    )
    filas = cursor.fetchall()
    conn.close()
    return [{"codigo": cod, "nombre": nom} for cod, nom in filas]


def validar_catalogo_directo(pedido: list) -> dict:
    """Procesa la lista extraída contra los 100,000 registros."""
    productos_procesados = []
    hubo_coincidencias_completas = True

    for item in pedido:
        nombre = item["nombre"]
        cantidad = item["cantidad"]

        coincidencias = _buscar_en_catalogo(nombre)

        item_res = {
            "status": "OK",
            "message": "Mapeado correctamente.",
            "data": {
                "busqueda": nombre,
                "codigo": None,
                "nombre": None,
                "cantidad": cantidad
            }}

        if len(coincidencias) == 0:
            item_res.update({
                "status": "NO_ENCONTRADO",
                "message": f"No se encontró '{nombre}'."
            })
            hubo_coincidencias_completas = False
        elif len(coincidencias) > 1:
            item_res.update({
                "status": "REQUIERE_CONFIRMACION",
                "message": f"Múltiples opciones para '{nombre}'."
            })
            item_res["data"]["candidatos"] = coincidencias
            hubo_coincidencias_completas = False
        else:
            producto_unico = coincidencias[0]
            item_res["data"]["codigo"] = producto_unico["codigo"]
            item_res["data"]["nombre"] = producto_unico["nombre"]

        productos_procesados.append(item_res)

    return productos_procesados
