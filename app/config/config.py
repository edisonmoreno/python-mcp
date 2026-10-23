from pydantic import SecretStr, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    variables de configuración
    """
    # str = Valida que sea texto
    # HttpUrl = Valida que sea una URL válida
    # SecretStr = evita que la clave se imprima por accidente en los logs
    openai_base_url: HttpUrl
    openai_model: str
    openai_api_key: SecretStr
    openai_max_completion_tokens: int

    debug_mode: bool = False  # Valor por defecto si no se define

    # Le indicamos a Pydantic que extraiga los valores desde el archivo .env
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8'
    )


# Única instancia global para toda la app
settings = Settings()
