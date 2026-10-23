from typing import Protocol


class TenantRepository(Protocol):
    """Protocol for tenant persistence operations."""

    def find_by_id(self, tenant_id: str) -> list[str]:
        """Find a tenant by its ID."""

    def save(self, document):
        """Save a tenant."""
