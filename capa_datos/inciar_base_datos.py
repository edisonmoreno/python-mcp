import os
import sys
import random
import sqlite3

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
        "CREATE TABLE IF NOT EXISTS productos (codigo TEXT PRIMARY KEY, nombre TEXT NOT NULL, categoria TEXT, precio REAL NOT NULL)")
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS buscar_productos USING fts5(
            codigo, nombre, categoria, precio, tokenize="porter unicode61 remove_diacritics 1"
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
            ("001", "Coca Cola Original 350ml", "Bebidas", 2100),
            ("002", "Coca Cola sin Azúcar 350ml", "Bebidas", 1900),
            ("003", "Postobón Manzana 1.5L", "Bebidas Locales", 4000),
            ("004", "Papas Fritas Margaritas Naturales", "Snacks", 2500),
            ("005", "Cerveza Aguila Original", "Bebidas Locales", 3000),
            ("006", "Pan Aliñado", "Panaderia", 3100),
            ("007", "Yuquitas Fritas", "Snacks", 2800),
            ("008", "Chocolativa", "Dulces", 1500),
            ("009", "Chororamo", "Panaderia", 1600),
            ("010", "Pan Trenza", "Panaderia", 3200),
            ("011", "Cerveza Pilsen", "Panaderia", 3100),
            ("012", "Cerveza Aguila Ligth", "Panaderia", 2900),
            ("013", "Manzana Chilena", "Frutas", 500),
            ("014", "Chocolate sin Azúcar", "Despensa", 1300),
        ]

        # Generar masivamente los 100k registros en lote
        for i in range(15, 100001):
            productos_demo.append((
                f"PROD_{i:06d}",
                f"Producto de Limpieza Número {i} Multiusos",
                "Limpieza",
                round(random.uniform(100.0, 10000.0), 2)
            ))

        cursor.execute("BEGIN TRANSACTION")
        cursor.executemany(
            "INSERT INTO productos VALUES (?, ?, ?, ?)", productos_demo)
        cursor.executemany(
            "INSERT INTO buscar_productos VALUES (?, ?, ?, ?)", productos_demo)
        conn.commit()
        print(
            "✅ [SERVIDOR MCP] ¡Éxito! 100,000 productos creados e indexados correctamente.", file=sys.stderr)

    conn.close()


if __name__ == "__main__":
    inicializar_base_de_datos()
