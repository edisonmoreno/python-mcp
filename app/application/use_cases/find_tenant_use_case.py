"""Use case for finding a tenant."""


class FindTenantUseCase:
    """Find a tenant using its identifier."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, tenant_id: str) -> list[str]:
        """Find a tenant by its identifier."""
        return self.repository.find_by_id(tenant_id)
