import sys
import os
import pandas as pd
from capa_cliente.chat_local_spacy import motor_interpretacion

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "capa_datos", "entrenamiento.xlsx")
print(f"Ruta.excel: {DB_PATH}", file=sys.stderr)


def _excel_disponible(archivo):
    try:
        with open(archivo, "r+b"):
            return True
    except PermissionError:
        print(
            f"ERROR: El archivo está abierto o bloqueado:\n{archivo}\n"
            "Ciérralo en Excel e intenta nuevamente."
        )
        return False
    except FileNotFoundError:
        print(f"ERROR: No existe el archivo:\n{archivo}")
        return False


def evaluar(archivo=DB_PATH):
    if not _excel_disponible(archivo):
        return

    df = pd.read_excel(archivo)

    for indice, fila in df.iterrows():
        if pd.isna(fila["Entrada"]):
            continue

        entrada = str(fila["Entrada"]).strip()

        # Ejecutar tu interpretador sobre Entrada
        obtenido = motor_interpretacion(entrada)

        if not obtenido:
            df.at[indice, "Producto"] = None
            df.at[indice, "Cantidad"] = None
            continue

        df.at[indice, "Producto"] = obtenido[0]["nombre"]
        df.at[indice, "Cantidad"] = obtenido[0]["cantidad"]

        print(f"{entrada} -> {obtenido}")

    df.to_excel(archivo, index=False)
    print("\nExcel actualizado.")


if __name__ == "__main__":
    evaluar()
