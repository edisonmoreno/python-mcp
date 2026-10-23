"""In-memory tenant repository."""


class TenantRepositoryAdapter:
    """Concrete implementation of TenantRepository."""

    def find_by_id(self, tenant_id: str):
        """Find a tenant by its identifier."""
        lista = [
            "Toro SAS",
            "Alcaldia Med",
            "Industria Ink",
            tenant_id
        ]
        return lista
