from pydantic import EmailStr, Field

from app.lib.schema import CamelizedBaseSchema


class MagicLinkRequest(CamelizedBaseSchema):
    email: EmailStr
    return_to: str | None = Field(None)


class MagicLinkRequestResponse(CamelizedBaseSchema):
    ok: bool = True
    # Only returned in debug mode to make local/dev flows and tests easier.
    debug_token: str | None = Field(None)


class LogoutResponse(CamelizedBaseSchema):
    ok: bool = True
