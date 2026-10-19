import asyncio
import sys
import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# 1. Inicializamos el servidor MCP
app = Server("servidor-clima-mcp")

# 2. Definimos la herramienta y lo que necesita (Latitud y Longitud)


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="consultar_clima_coordenadas",
            description="Consulta la temperatura actual y la velocidad del viento en tiempo real usando coordenadas geográficas (latitud y longitud).",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitud": {"type": "number", "description": "Latitud de la ubicación (ej. 6.25 para Medellín, 4.60 para Bogotá)."},
                    "longitud": {"type": "number", "description": "Longitud de la ubicación (ej. -75.56 para Medellín, -74.07 para Bogotá)."}
                },
                "required": ["latitud", "longitud"]
            }
        )
    ]

# 3. Conectamos la lógica con la API pública de Open-Meteo


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "consultar_clima_coordenadas":
        raise ValueError("Herramienta no encontrada")

    lat = arguments.get("latitud")
    lon = arguments.get("longitud")

    # URL oficial de la API de Open-Meteo para datos actuales
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m"

    async with httpx.AsyncClient() as client:
        try:
            respuesta = await client.get(url)
            datos = respuesta.json()

            # Extraemos las lecturas del clima actual
            actual = datos.get("current", {})
            temp = actual.get("temperature_2m", "No disponible")
            viento = actual.get("wind_speed_10m", "No disponible")

            resultado = (
                f"=== CLIMA EN TIEMPO REAL ===\n"
                f"Coordenadas consultadas: Lat {lat}, Lon {lon}\n"
                f"Temperatura Actual: {temp}°C\n"
                f"Velocidad del Viento: {viento} km/h"
            )
            return [TextContent(type="text", text=resultado)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error al conectar con el satélite meteorológico: {str(e)}")]

# 4. Canal de comunicación stdio


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
