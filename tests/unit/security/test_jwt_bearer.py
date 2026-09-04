import os
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException

from app.jwt_bearer import HTTPBearer, JWTBearer
from app.models.jwt import JWTToken


def _jwt_secret() -> str:
    return os.getenv("JWT_SECRET_SSM_PARAM_VALUE")


def _audience() -> str:
    return f"{os.getenv('STAGE')}-{os.getenv('APP_NAME')}"


def _encode_token(
    secret: str | None = None,
    drop: tuple[str, ...] = (),
    **overrides,
) -> str:
    """Sign a well-formed token; ``drop`` removes required claims, ``overrides`` mutates."""
    now = datetime.now(UTC)
    payload = {
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
        "aud": _audience(),
        "jti": str(uuid.uuid4()),
        "sub": "e2e-user",
    }
    payload.update(overrides)
    for claim in drop:
        payload.pop(claim)
    return jwt.encode(payload, secret or _jwt_secret(), algorithm="HS256")


class _Request:
    """Minimal stand-in exposing only the headers JWTBearer reads."""

    def __init__(self, authorization: str | None = None):
        self.headers = (
            {"Authorization": authorization} if authorization is not None else {}
        )


class TestHTTPBearer:
    def test_missing_authorization_header_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            HTTPBearer()(_Request())
        assert exc.value.status_code == 403
        assert exc.value.detail == "Not authenticated"

    def test_missing_authorization_header_returns_none_without_auto_error(self):
        assert HTTPBearer(auto_error=False)(_Request()) is None

    def test_empty_authorization_header_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            HTTPBearer()(_Request(authorization=""))
        assert exc.value.status_code == 403
        assert exc.value.detail == "Not authenticated"

    def test_empty_authorization_header_returns_none_without_auto_error(self):
        assert HTTPBearer(auto_error=False)(_Request(authorization="")) is None

    def test_non_bearer_scheme_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            HTTPBearer()(_Request(authorization="Basic dXNlcjpwYXNz"))
        assert exc.value.status_code == 403
        assert exc.value.detail == "Invalid authentication credentials"

    def test_non_bearer_scheme_returns_none_without_auto_error(self):
        assert HTTPBearer(auto_error=False)(_Request(authorization="Basic x")) is None

    def test_valid_credentials_are_returned(self):
        credentials = HTTPBearer()(_Request(authorization="Bearer some-token"))
        assert credentials.scheme == "Bearer"
        assert credentials.credentials == "some-token"


class TestJWTBearer:
    def test_valid_token_returns_decoded_token(self):
        bearer = JWTBearer()
        token = bearer(_Request(authorization=f"Bearer {_encode_token()}"))
        assert isinstance(token, JWTToken)
        assert token.sub == "e2e-user"
        assert token.aud == _audience()

    def test_valid_token_returns_decoded_token_without_auto_error(self):
        bearer = JWTBearer(auto_error=False)
        token = bearer(_Request(authorization=f"Bearer {_encode_token()}"))
        assert isinstance(token, JWTToken)

    def test_missing_authorization_header_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            JWTBearer()(_Request())
        assert exc.value.status_code == 403
        assert exc.value.detail == "Not authenticated"

    def test_missing_authorization_header_returns_none_without_auto_error(self):
        assert JWTBearer(auto_error=False)(_Request()) is None

    def test_non_bearer_scheme_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            JWTBearer()(_Request(authorization="Basic dXNlcjpwYXNz"))
        assert exc.value.status_code == 403
        assert exc.value.detail == "Invalid authentication credentials"

    def test_non_bearer_scheme_returns_none_without_auto_error(self):
        assert JWTBearer(auto_error=False)(_Request(authorization="Basic x")) is None

    def test_token_with_invalid_signature_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            JWTBearer()(
                _Request(
                    authorization=f"Bearer {_encode_token(secret='N7f2Qp9Lm4Tx8Vb1Rc6Zd0Hs3Jy5KwEa')}"
                )
            )
        assert exc.value.status_code == 403
        assert exc.value.detail == "Not authenticated"

    def test_token_with_invalid_signature_returns_none_without_auto_error(self):
        bearer = JWTBearer(auto_error=False)
        token = bearer(
            _Request(
                authorization=f"Bearer {_encode_token(secret='N7f2Qp9Lm4Tx8Vb1Rc6Zd0Hs3Jy5KwEa')}"
            )
        )
        assert token is None

    def test_expired_token_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            JWTBearer()(_Request(authorization=f"Bearer {_encode_token(exp=0, iat=0)}"))
        assert exc.value.status_code == 403

    def test_token_with_wrong_audience_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            JWTBearer()(
                _Request(
                    authorization=f"Bearer {_encode_token(aud='dev-user-service')}"
                )
            )
        assert exc.value.status_code == 403

    def test_token_without_audience_claim_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            JWTBearer()(
                _Request(authorization=f"Bearer {_encode_token(drop=('aud',))}")
            )
        assert exc.value.status_code == 403

    def test_token_without_exp_claim_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            JWTBearer()(
                _Request(authorization=f"Bearer {_encode_token(drop=('exp',))}")
            )
        assert exc.value.status_code == 403
        assert exc.value.detail == "Not authenticated"
