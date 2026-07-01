from __future__ import annotations

from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.domain.access_scope import ReviewAccessScope


class ReviewAccessScopeRequest(CamelModel):
    tenant_id: str = Field(..., alias="tenantId")
    book_id: str = Field(..., alias="bookId")
    portfolio_id: str = Field(..., alias="portfolioId")
    client_id: str = Field(..., alias="clientId")

    @field_validator("tenant_id", "book_id", "portfolio_id", "client_id")
    @classmethod
    def _scope_field_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("scope fields cannot be blank")
        return value

    def to_domain(self) -> ReviewAccessScope:
        return ReviewAccessScope(
            tenant_id=self.tenant_id,
            book_id=self.book_id,
            portfolio_id=self.portfolio_id,
            client_id=self.client_id,
        )
