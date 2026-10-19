import os
import time
import shutil
import sys
import asyncio
import json
import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client


async def main():
    print("Conectando al servidor MCP a través de SSE...")
    try:
        # 1. Conectamos al servidor web (asegúrate de que sigue corriendo en la otra terminal)
        async with sse_client("http://localhost:8000/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # 2. Inicializamos el protocolo MCP
                await session.initialize()
                print(
                    "\n🤖 Arquitectura Activa: [Ollama] ➔ [MCP vía SSE] ➔ [SQLite FTS5 100K]")
                print(
                    "Escribe tu pedido (ej: '2 cocas y un limpiador 500') o 'salir'.\n")

                historial_conversacion = []

                # 3. AQUÍ ESTÁ EL BUCLE INTERACTIVO:
                while True:
                    user_input = input("👤 Mesero: ")
                    if user_input.lower() == 'salir':
                        break
                    if not user_input.strip():
                        continue

                    historial_conversacion.append({
                        "role": "user",
                        "content": user_input
                    })

                    iteration_start = time.perf_counter()
                    # Llamada a Ollama con tu modelo mesero-bot
                    response = ollama.chat(
                        model='mesero-bot',
                        messages=historial_conversacion,
                        options={
                            # Elimina la creatividad; va directo a la regla estructurada
                            'temperature': 0.0,
                            # Limita la cantidad de tokens que puede generar (evita bucles infinitos)
                            'num_predict': 100,
                            # Reduce el abanico de opciones de palabras a evaluar
                            'top_k': 10,
                            # Evalúa solo las respuestas más probables
                            'top_p': 0.5,
                        },
                        tools=[{
                            'type': 'function',
                            'function': {
                                'name': 'validar_catalogo',
                                'description': 'Valida productos contra el catálogo de la empresa.',
                                'parameters': {
                                    'type': 'object',
                                    'properties': {
                                        'data': {
                                            'type': 'array',
                                            'description': 'Lista de productos seleccionados.',
                                            'items': {
                                                'type': 'object',
                                                'properties': {
                                                    'nombre': {'type': 'string', 'description': 'Nombre del producto.'},
                                                    'cantidad': {'type': 'integer', 'description': 'Cantidad.'}
                                                },
                                                'required': ['nombre', 'cantidad']
                                            }
                                        }
                                    },
                                    'required': ['data']
                                }
                            }
                        }]

                    )
                    print(
                        f"  - Fin chat (validar_catalogo) {time.perf_counter() - iteration_start:.6f} seg.")
                    # Si Ollama decide consumir nuestra API Local de MCP
                    if response.get('message', {}).get('tool_calls'):
                        # 1. Guardamos la intención original de Ollama (su solicitud de usar la herramienta)
                        historial_conversacion.append(response['message'])

                        for tool in response['message']['tool_calls']:
                            if tool['function']['name'] == 'validar_catalogo':
                                args = tool['function']['arguments']
                                print(
                                    f"⚙️ [Ollama invocó tu API MCP con]: {args}")

                                # Consulta física en tu servidor por red local
                                resultado_mcp = await session.call_tool("validar_catalogo", arguments=args)
                                print(
                                    f"  - Fin API MCP {time.perf_counter() - iteration_start:.6f} seg.")

                                # Extraemos el texto de la respuesta MCP de forma segura
                                if hasattr(resultado_mcp, 'content') and isinstance(resultado_mcp.content, list):
                                    texto_respuesta = "".join(
                                        [getattr(c, 'text', str(c)) for c in resultado_mcp.content])
                                else:
                                    texto_respuesta = str(resultado_mcp)

                                print(
                                    f"  - json: \n{texto_respuesta}\n")

                                # 2. Agregamos la respuesta REAL de la base de datos a los mensajes
                                historial_conversacion.append({
                                    'role': 'tool',
                                    'content': texto_respuesta,
                                    'name': 'validar_catalogo'
                                })

                                # 3. Le exigimos a Ollama que analice conversación antes de responder
                                respuesta_final = ollama.chat(
                                    model='mesero-bot',
                                    messages=historial_conversacion
                                )
                                print(
                                    f"  - Fin chat (conversación) {time.perf_counter() - iteration_start:.6f} seg.")
                                print(
                                    f"🤖 Bot: {respuesta_final['message']['content']}\n")

                                # Guardamos la respuesta final del bot en el historial para mantener el hilo
                                historial_conversacion.append(
                                    respuesta_final['message']
                                )
                    else:
                        print(f"🤖 Bot: {response['message']['content']}\n")
                        # Guardamos la respuesta directa del bot en el historial
                        historial_conversacion.append(response['message'])

    except Exception as e:
        print(f"❌ Error en la arquitectura cliente SSE: {e}")


if __name__ == "__main__":
    asyncio.run(main())
