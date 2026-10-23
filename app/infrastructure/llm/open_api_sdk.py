from openai import OpenAI


def consultar_ia(data_input: dict) -> str:
    """
    Función agnóstica para consultar modelos de IA utilizando el estándar de OpenAI.
    """
    # Inicializar el cliente con la configuración
    client = OpenAI(
        api_key=data_input["config"]["api_key"],
        base_url=data_input["config"]["base_url"],
        timeout=data_input["config"]["timeout"],
        max_retries=data_input["config"]["max_retries"]
    )

    prompt_sistema = data_input["chat"]["sistema"]
    prompt_usuario = data_input["chat"]["usuario"]

    # gemini-embedding-2       $0.20 USD x Millon tokens
    # gemini-3.5-flash-lite    $0.30 USD x Millon tokens

    # ** EMBEDDING **
    # result = client.embeddings.create(
    #     model="gemini-embedding-2",
    #     input="Función agnóstica para consultar modelos de IA utilizando el estándar de OpenAI.",
    #     dimensions=1536,
    # )
    # print(result)
    # FIN PRUEBA

    # Realizar la petición
    respuesta = client.chat.completions.create(
        model=data_input["chat"]["model"],
        max_completion_tokens=data_input["chat"]["max_completion_tokens"],
        response_format=data_input["chat"]["response_format"],
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        temperature=0.3  # Baja temperatura para respuestas más consistentes y lógicas
    )

    # Retornar el texto
    return respuesta.choices[0].message.content
