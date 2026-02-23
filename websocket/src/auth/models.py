from dataclasses import dataclass, field


@dataclass(slots=True)
class AuthenticatedUser:
    user_id: str
    permissions: list[str]
    tenant_id: str
    token_exp: int | None = None  # Unix timestamp
