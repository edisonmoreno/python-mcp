"""Chat API controller."""
import os
from app.application.use_cases.find_tenant_use_case import FindTenantUseCase
from app.infrastructure.respositories.tenant_repository_adapter import TenantRepositoryAdapter
from app.infrastructure.llm.open_api_sdk import consultar_ia
from app.config.config import settings


def get():
    """Retrieve the tenant."""
    repository = TenantRepositoryAdapter()
    result = FindTenantUseCase(repository).execute("818")
    print(result)


if __name__ == "__main__":
    get()

    payload = {
        "config": {
            "api_key": settings.openai_api_key.get_secret_value(),
            "base_url": str(settings.openai_base_url),
            "timeout": 20.0,
            "max_retries": 5,
        },
        "chat": {
            "model": settings.openai_model,
            "max_completion_tokens": settings.openai_max_completion_tokens,
            "response_format": {"type": "text"},
            "sistema": "Eres un asistente experto en desarrollo de software que responde de forma corta y directa.",
            "usuario": "¿Por qué es buena idea desacoplar el SDK del proveedor en una arquitectura de IA?"
        }
    }

    print("Enviando consulta a la IA configurada...")
    resultado = consultar_ia(payload)
    print("\n--- Respuesta Recibida ---")
    print(resultado)
