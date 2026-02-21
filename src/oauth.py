"""
MCP OAuth 2.1 Authorization Server

Implements the MCP Authorization spec (2025-03-26) with:
- RFC 8414  Metadata discovery (.well-known/oauth-authorization-server)
- RFC 7591  Dynamic client registration (POST /register)
- OAuth 2.1 Authorization endpoint with PKCE (GET/POST /authorize)
- OAuth 2.1 Token endpoint (POST /token)
- Backward-compatible with static API key auth (Layer 1)

Reference: https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization
"""

import os
import time
import json
import secrets
import hashlib
import base64
import logging
from typing import Optional
from urllib.parse import urlencode, parse_qs, urlparse

import jwt  # PyJWT

logger = logging.getLogger("qradar-mcp")

# ---------------------------------------------------------------------------
# Configuration (from environment)
# ---------------------------------------------------------------------------

OAUTH_JWT_SECRET = os.environ.get("OAUTH_JWT_SECRET", "")
OAUTH_USERNAME = os.environ.get("OAUTH_USERNAME", "admin")
OAUTH_PASSWORD = os.environ.get("OAUTH_PASSWORD", "")
MCP_API_KEY = os.environ.get("MCP_API_KEY", "")

ACCESS_TOKEN_TTL = 3600        # 1 hour
REFRESH_TOKEN_TTL = 604800     # 7 days
AUTH_CODE_TTL = 300            # 5 minutes

JWT_ALGORITHM = "HS256"

# ---------------------------------------------------------------------------
# In-memory stores (no DB — simple, single-instance server)
# ---------------------------------------------------------------------------

# Registered clients: {client_id: {client_secret, redirect_uris, client_name, created_at}}
_client_registry: dict = {}

# Pending auth codes: {code: {client_id, redirect_uri, code_challenge, code_challenge_method, expires_at, user}}
_auth_codes: dict = {}

# Refresh tokens: {token_hash: {client_id, user, expires_at}}
_refresh_tokens: dict = {}


def _hash(value: str) -> str:
    """SHA-256 hash a string."""
    return hashlib.sha256(value.encode()).hexdigest()


def _clean_expired():
    """Remove expired auth codes and refresh tokens."""
    now = time.time()
    expired_codes = [k for k, v in _auth_codes.items() if v["expires_at"] < now]
    for k in expired_codes:
        del _auth_codes[k]
    expired_tokens = [k for k, v in _refresh_tokens.items() if v["expires_at"] < now]
    for k in expired_tokens:
        del _refresh_tokens[k]


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _create_access_token(client_id: str, user: str) -> str:
    """Create a signed JWT access token."""
    now = time.time()
    payload = {
        "sub": user,
        "client_id": client_id,
        "iat": int(now),
        "exp": int(now + ACCESS_TOKEN_TTL),
        "type": "access_token",
    }
    return jwt.encode(payload, OAUTH_JWT_SECRET, algorithm=JWT_ALGORITHM)


def _create_refresh_token(client_id: str, user: str) -> str:
    """Create an opaque refresh token and store it."""
    token = secrets.token_urlsafe(48)
    _refresh_tokens[_hash(token)] = {
        "client_id": client_id,
        "user": user,
        "expires_at": time.time() + REFRESH_TOKEN_TTL,
    }
    return token


def verify_access_token(token: str) -> Optional[dict]:
    """Verify a JWT access token. Returns payload if valid, None otherwise."""
    if not OAUTH_JWT_SECRET:
        return None
    try:
        payload = jwt.decode(token, OAUTH_JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access_token":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("OAuth token expired")
        return None
    except jwt.InvalidTokenError:
        return None


# ---------------------------------------------------------------------------
# Metadata discovery — RFC 8414
# ---------------------------------------------------------------------------

def get_metadata(base_url: str) -> dict:
    """Return OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/authorize",
        "token_endpoint": f"{base_url}/token",
        "registration_endpoint": f"{base_url}/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": ["mcp"],
    }


def get_protected_resource_metadata(base_url: str) -> dict:
    """Return Protected Resource Metadata (RFC 9728)."""
    return {
        "resource": base_url,
        "authorization_servers": [base_url],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["mcp"],
    }


# ---------------------------------------------------------------------------
# Dynamic client registration — RFC 7591
# ---------------------------------------------------------------------------

def register_client(body: dict) -> tuple[dict, int]:
    """Register a new OAuth client. Returns (response_body, status_code)."""
    redirect_uris = body.get("redirect_uris")
    if not redirect_uris or not isinstance(redirect_uris, list):
        return {"error": "invalid_client_metadata", "error_description": "redirect_uris is required"}, 400

    client_id = secrets.token_urlsafe(24)
    client_secret = secrets.token_urlsafe(32)

    _client_registry[client_id] = {
        "client_secret": _hash(client_secret),
        "redirect_uris": redirect_uris,
        "client_name": body.get("client_name", "unknown"),
        "grant_types": body.get("grant_types", ["authorization_code"]),
        "created_at": int(time.time()),
    }

    logger.info(f"OAuth client registered: {body.get('client_name', 'unknown')} (id={client_id[:8]}...)")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_name": body.get("client_name", "unknown"),
        "redirect_uris": redirect_uris,
        "grant_types": body.get("grant_types", ["authorization_code"]),
    }, 201


# ---------------------------------------------------------------------------
# Authorization endpoint — OAuth 2.1 + PKCE
# ---------------------------------------------------------------------------

_LOGIN_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>QRadar MCP — Sign In</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               display: flex; justify-content: center; align-items: center;
               min-height: 100vh; margin: 0; background: #0f1419; color: #e0e0e0; }}
        .card {{ background: #1a1f25; padding: 2rem; border-radius: 12px;
                 box-shadow: 0 4px 24px rgba(0,0,0,0.4); width: 340px; }}
        h2 {{ margin: 0 0 0.5rem; color: #4589ff; font-size: 1.3rem; }}
        .subtitle {{ color: #888; font-size: 0.85rem; margin-bottom: 1.5rem; }}
        label {{ display: block; margin-bottom: 0.3rem; font-size: 0.9rem; color: #aaa; }}
        input {{ width: 100%; padding: 0.6rem; margin-bottom: 1rem; border: 1px solid #333;
                 border-radius: 6px; background: #0f1419; color: #e0e0e0; font-size: 0.95rem;
                 box-sizing: border-box; }}
        button {{ width: 100%; padding: 0.7rem; background: #4589ff; color: white; border: none;
                  border-radius: 6px; font-size: 1rem; cursor: pointer; }}
        button:hover {{ background: #3571e0; }}
        .error {{ color: #ff6b6b; font-size: 0.85rem; margin-bottom: 1rem; }}
        .client {{ color: #666; font-size: 0.8rem; margin-top: 1rem; text-align: center; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>QRadar MCP Server</h2>
        <div class="subtitle">OAuth 2.1 Authorization</div>
        {error}
        <form method="POST" action="/authorize">
            <label>Username</label>
            <input type="text" name="username" required autofocus>
            <label>Password</label>
            <input type="password" name="password" required>
            <input type="hidden" name="client_id" value="{client_id}">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="code_challenge" value="{code_challenge}">
            <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
            <input type="hidden" name="state" value="{state}">
            <input type="hidden" name="response_type" value="code">
            <button type="submit">Authorize</button>
        </form>
        <div class="client">Client: {client_name}</div>
    </div>
</body>
</html>"""


def authorize_get(params: dict) -> tuple[str, int, dict]:
    """
    Handle GET /authorize — show login page.
    Returns (html_body, status_code, headers).
    """
    client_id = params.get("client_id", "")
    redirect_uri = params.get("redirect_uri", "")
    code_challenge = params.get("code_challenge", "")
    code_challenge_method = params.get("code_challenge_method", "S256")
    state = params.get("state", "")

    # Validate client
    if client_id not in _client_registry:
        return "<h1>Error: Unknown client_id</h1>", 400, {"Content-Type": "text/html"}

    client = _client_registry[client_id]
    if redirect_uri not in client["redirect_uris"]:
        return "<h1>Error: Invalid redirect_uri</h1>", 400, {"Content-Type": "text/html"}

    if not code_challenge:
        return "<h1>Error: code_challenge is required (PKCE)</h1>", 400, {"Content-Type": "text/html"}

    html = _LOGIN_HTML.format(
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        state=state,
        client_name=client.get("client_name", "unknown"),
        error="",
    )
    return html, 200, {"Content-Type": "text/html"}


def authorize_post(form: dict) -> tuple[str, int, dict]:
    """
    Handle POST /authorize — validate credentials and redirect with auth code.
    Returns (body, status_code, headers).
    """
    username = form.get("username", "")
    password = form.get("password", "")
    client_id = form.get("client_id", "")
    redirect_uri = form.get("redirect_uri", "")
    code_challenge = form.get("code_challenge", "")
    code_challenge_method = form.get("code_challenge_method", "S256")
    state = form.get("state", "")

    # Validate client
    if client_id not in _client_registry:
        return "<h1>Error: Unknown client_id</h1>", 400, {"Content-Type": "text/html"}

    # Validate credentials
    if username != OAUTH_USERNAME or password != OAUTH_PASSWORD:
        client = _client_registry[client_id]
        html = _LOGIN_HTML.format(
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            state=state,
            client_name=client.get("client_name", "unknown"),
            error='<div class="error">Invalid username or password</div>',
        )
        return html, 401, {"Content-Type": "text/html"}

    # Generate auth code
    _clean_expired()
    code = secrets.token_urlsafe(32)
    _auth_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "user": username,
        "expires_at": time.time() + AUTH_CODE_TTL,
    }

    # Redirect with code
    params = {"code": code}
    if state:
        params["state"] = state
    redirect_url = f"{redirect_uri}?{urlencode(params)}"

    return "", 302, {"Location": redirect_url, "Content-Type": "text/html"}


# ---------------------------------------------------------------------------
# Token endpoint — OAuth 2.1
# ---------------------------------------------------------------------------

def _verify_pkce(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    """Verify PKCE code_verifier against code_challenge."""
    if method != "S256":
        return False
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return computed == code_challenge


def exchange_token(body: dict) -> tuple[dict, int]:
    """
    Handle POST /token — authorization_code or refresh_token grant.
    Returns (response_body, status_code).
    """
    grant_type = body.get("grant_type")

    if grant_type == "authorization_code":
        return _exchange_auth_code(body)
    elif grant_type == "refresh_token":
        return _exchange_refresh_token(body)
    else:
        return {"error": "unsupported_grant_type"}, 400


def _exchange_auth_code(body: dict) -> tuple[dict, int]:
    """Exchange authorization code + PKCE verifier for tokens."""
    code = body.get("code", "")
    client_id = body.get("client_id", "")
    client_secret = body.get("client_secret", "")
    code_verifier = body.get("code_verifier", "")

    _clean_expired()

    # Validate auth code
    if code not in _auth_codes:
        return {"error": "invalid_grant", "error_description": "Invalid or expired authorization code"}, 400

    code_data = _auth_codes[code]

    # Validate client
    if code_data["client_id"] != client_id:
        return {"error": "invalid_grant", "error_description": "client_id mismatch"}, 400

    if client_id not in _client_registry:
        return {"error": "invalid_client"}, 401

    client = _client_registry[client_id]
    if _hash(client_secret) != client["client_secret"]:
        return {"error": "invalid_client", "error_description": "Invalid client_secret"}, 401

    # Validate PKCE
    if not _verify_pkce(code_verifier, code_data["code_challenge"], code_data["code_challenge_method"]):
        return {"error": "invalid_grant", "error_description": "PKCE verification failed"}, 400

    # Consume the code (one-time use)
    del _auth_codes[code]

    # Issue tokens
    user = code_data["user"]
    access_token = _create_access_token(client_id, user)
    refresh_token = _create_refresh_token(client_id, user)

    logger.info(f"OAuth tokens issued for user={user}, client={client_id[:8]}...")

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_TTL,
        "refresh_token": refresh_token,
    }, 200


def _exchange_refresh_token(body: dict) -> tuple[dict, int]:
    """Exchange refresh token for new access + refresh tokens."""
    refresh_token = body.get("refresh_token", "")
    client_id = body.get("client_id", "")
    client_secret = body.get("client_secret", "")

    _clean_expired()

    token_hash = _hash(refresh_token)
    if token_hash not in _refresh_tokens:
        return {"error": "invalid_grant", "error_description": "Invalid or expired refresh token"}, 400

    token_data = _refresh_tokens[token_hash]

    # Validate client
    if token_data["client_id"] != client_id:
        return {"error": "invalid_grant", "error_description": "client_id mismatch"}, 400

    if client_id not in _client_registry:
        return {"error": "invalid_client"}, 401

    client = _client_registry[client_id]
    if _hash(client_secret) != client["client_secret"]:
        return {"error": "invalid_client", "error_description": "Invalid client_secret"}, 401

    # Revoke old refresh token
    del _refresh_tokens[token_hash]

    # Issue new tokens (rotation)
    user = token_data["user"]
    access_token = _create_access_token(client_id, user)
    new_refresh_token = _create_refresh_token(client_id, user)

    logger.info(f"OAuth tokens refreshed for user={user}, client={client_id[:8]}...")

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_TTL,
        "refresh_token": new_refresh_token,
    }, 200


# ---------------------------------------------------------------------------
# WWW-Authenticate header builder
# ---------------------------------------------------------------------------

def www_authenticate_header(base_url: str) -> str:
    """Build the WWW-Authenticate header value per MCP spec (RFC 9728)."""
    return f'Bearer resource_metadata="{base_url}/.well-known/oauth-protected-resource"'


# ---------------------------------------------------------------------------
# Initialization check
# ---------------------------------------------------------------------------

def is_oauth_configured() -> bool:
    """Check if OAuth is properly configured (JWT secret + password set)."""
    return bool(OAUTH_JWT_SECRET and OAUTH_PASSWORD)
