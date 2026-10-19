import time
import re
import json
from capa_negocio.servidor_catalog_spacy import validar_catalogo_directo
import spacy
from text_to_num import alpha2digit
from spacy.language import Language
import json

LANAGUAGE_CODE = "es"
nlp = spacy.load("es_core_news_md")

# Diccionarios de equivalencias para el negocio
CATEGORIAS_MEDIDAS = {
    # Conteo cuantitativo directo
    "CONTEO": {
        "un": 1, "una": 1,
        "par": 2, "pareja": 2,
        "media docena": 6,
        "docena": 12, "docenas": 12
    },
    # Empaques grupales comerciales
    "EMPAQUE": {
        "sixpack": 1, "six pack": 1, "six-pack": 1
    },
    # Magnitudes físicas (Masa y Volumen)
    "MAGNITUD": {
        "libra": 1, "libras": 1,
        "kilo": 1, "kilos": 1,
        "litro": 1, "litros": 1
    }
}


# Palabras ruidosas que ensucian el índice de SQLite FTS5
STOP_WORDS_COMERCIALES = {
    # "de", "del", "para", "por",
    # "unidades", "unidad", "porfa", "favor"
}


def _normalizar_numeros(text: str):
    return alpha2digit(text, LANAGUAGE_CODE)


@Language.component("extractor_cantidades_comerciales")
def extractor_cantidades_comerciales(doc):
    """
    Componente personalizado para spaCy.
    Detecta agrupadores comerciales antes del análisis gramatical general.
    """
    doc.user_data["cantidad_comercial"] = None
    doc.user_data["categoria_medida"] = None
    doc.user_data["indices_ignorados"] = set()

    texto_completo = doc.text.lower()

    for categoria, medidas in CATEGORIAS_MEDIDAS.items():
        # Buscamos si la línea contiene palabras clave de nuestra tabla
        for palabra, valor in medidas.items():
            # Usamos regex para asegurar que sea la palabra exacta aislada
            match = re.search(rf'\b{palabra}\b', texto_completo)
            if match:
                doc.user_data["cantidad_comercial"] = valor
                doc.user_data["categoria_medida"] = categoria
                # Identificamos qué tokens corresponden a esa palabra comercial para quitarlos del producto
                for token in doc:
                    if token.text.lower() == palabra and categoria == "CONTEO":
                        doc.user_data["indices_ignorados"].add(token.i)
                break
    return doc


# 🚀 INYECTAMOS EL COMPONENTE EN EL PIPELINE DE SPACY (Antes del Tagged estadístico)
nlp.add_pipe("extractor_cantidades_comerciales", before="tok2vec")


def motor_interpretacion(texto_usuario: str) -> list:
    pedido_estructurado = []

    # Separamos si el texto contiene varios productos con "y", "+", "también" o comas
    lineas = re.split(
        r'\s+y\s+|\s*,\s*|\s*\+\s*|\s*también\s*', texto_usuario.strip())

    for linea in lineas:
        if not linea.strip():
            continue

        # Convertir números escritos en letras a cifras
        # linea = _normalizar_numeros(linea)
        # spaCy analiza la gramática completa de la frase
        doc = nlp(linea)
        # Recuperamos si nuestro componente interceptó una cantidad comercial
        cantidad = doc.user_data["cantidad_comercial"]
        palabras_producto = []

        for token in doc:
            # Si el componente marcó este token como un agrupador ("docena", "media"), lo saltamos
            if token.i in doc.user_data["indices_ignorados"]:
                continue

            # Captura de números tradicionales (3, 1.5, etc.) si no se detectó agrupador antes
            if token.pos_ == "NUM":
                if cantidad is None and token.is_sent_start:
                    token_cantidad = _normalizar_numeros(token.text)
                    try:
                        cantidad = float(token_cantidad.replace(',', '.'))
                        continue
                    except ValueError:
                        pass

                # Si ya encontramos la cantidad solicitada,
                # conservamos los números posteriores en el nombre.
                palabras_producto.append(token.text)
                continue

            # Ignoramos conectores y stop words de inventario
            if token.text.lower() in STOP_WORDS_COMERCIALES or token.pos_ in ["PUNCT"]:
                continue

            if token.pos_ in ["NOUN", "ADJ", "PROPN", "ADP"] or token.text.isalnum():
                # Lematizamos a singular solo los sustantivos y adjetivos (ej: Quesitos -> quesito)
                if token.pos_ in ["NOUN", "ADJ"]:
                    palabras_producto.append(token.lemma_.lower())
                else:
                    palabras_producto.append(token.text.lower())

        # Si texto no traía números ni agrupadores, por defecto es 1
        if cantidad is None:
            cantidad = 1

        # Si es un número entero estético (ej: 12.0), lo convertimos a int (12)
        if isinstance(cantidad, float) and cantidad.is_integer():
            cantidad = int(cantidad)

        nombre_limpio = " ".join(palabras_producto).strip()

        if nombre_limpio:
            pedido_estructurado.append({
                "cantidad": cantidad,
                "nombre": nombre_limpio,
                "precio": 0
            })

    return pedido_estructurado


# 🏁 BUCLE PRINCIPAL SÍNCRONO Y ULTRA VELOZ
if __name__ == "__main__":
    print("\n🏎️ MOTOR SPACY CONFIGURADO EN PYTHON PURO (0ms)")
    print("──────────────────────────────────────────────────────")
    print("Prueba Estres:")
    ejemplos = [
        "Una garrafa de ron Medellín doce años",
        "media de aguardiente",
        "Media porción de mondongo",
        "Cuarto de aguardiente Néctar",
        "Siete botellas de Aseite",
        "3 Coca cola personal",
        "Postobón 1.5 litros",
        "empanada de 2 carnes",
        "seis empanadas de 2 carnes",
        "diez empanadas de tres carnes",
    ]

    for ej in ejemplos:
        inicio = time.perf_counter()
        resultado = motor_interpretacion(ej)
        fin = time.perf_counter()
        print(
            f"Texto: '{ej}' -> {resultado} -> Tiempo: {(fin - inicio)*1000:.2f} ms")

    while True:
        user_input = input("👤 Mesero: ")
        if user_input.lower() == 'salir':
            break
        if not user_input.strip():
            continue

        # -> mesero-bot
        pedido_parseado = motor_interpretacion(user_input)
        if not pedido_parseado:
            print(
                "🤖 Bot: Formato incorrecto. Usa: [Cantidad] [Producto]\n")
            continue

        # Consulta directa al inventario
        resultado = validar_catalogo_directo(pedido_parseado)

        # Presentación de resultados
        print(
            f"🤖 Bot: {json.dumps(resultado, ensure_ascii=False, indent=2)}\n")
