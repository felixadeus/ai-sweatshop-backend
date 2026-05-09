"""
Etsy API v3 Integration Module
Supports BOTH OAuth2 and Personal Access modes.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ─── Etsy API Configuration ─────────────────────────────────

ETSY_API_KEY = "xeexbjf4leouf7p868ypxjdj"
ETSY_API_SECRET = "z32wynsxg0"
ETSY_BASE_URL = "https://openapi.etsy.com/v3"

# Rate limiter
_rate_limit_tokens = 5.0
_rate_limit_last = time.time()
_rate_limit_max = 5.0
_rate_limit_refill = 1.0


def _check_rate_limit():
    global _rate_limit_tokens, _rate_limit_last
    now = time.time()
    elapsed = now - _rate_limit_last
    _rate_limit_tokens = min(_rate_limit_max, _rate_limit_tokens + elapsed * _rate_limit_refill)
    _rate_limit_last = now
    if _rate_limit_tokens < 1.0:
        wait = (1.0 - _rate_limit_tokens) / _rate_limit_refill
        time.sleep(wait)
        _rate_limit_tokens = 0
    _rate_limit_tokens -= 1.0


class EtsyAPIClient:
    """Etsy API client supporting OAuth2 and Personal Access modes."""

    def __init__(self, access_token: Optional[str] = None):
        self.api_key = ETSY_API_KEY
        self.access_token = access_token
        self.client = httpx.AsyncClient(
            base_url=ETSY_BASE_URL,
            headers={"x-api-key": self.api_key},
            timeout=30.0,
        )

    def get_oauth_url(self, redirect_uri: str, scopes: list[str]) -> tuple[str, str, str]:
        """Generate Etsy OAuth2 authorization URL. Returns (auth_url, code_verifier, state)."""
        import secrets, hashlib, base64, urllib.parse
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()
        params = {
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "client_id": self.api_key,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"https://www.etsy.com/oauth/connect?{urllib.parse.urlencode(params)}"
        return auth_url, code_verifier, state

    async def exchange_code(self, code: str, redirect_uri: str, code_verifier: str) -> dict:
        """Exchange authorization code for access token."""
        _check_rate_limit()
        import base64
        auth_string = base64.b64encode(
            f"{ETSY_API_KEY}:{ETSY_API_SECRET}".encode()
        ).decode()
        resp = await self.client.post(
            "https://api.etsy.com/v3/public/oauth/token",
            headers={"Authorization": f"Basic {auth_string}"},
            data={
                "grant_type": "authorization_code",
                "client_id": ETSY_API_KEY,
                "redirect_uri": redirect_uri,
                "code": code,
                "code_verifier": code_verifier,
            },
        )
        resp.raise_for_status()
        return resp.json()

    # ─── Auth Headers ──────────────────────────────────

    def _auth_headers(self) -> dict:
        headers = {"x-api-key": self.api_key}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    # ─── Shop API ──────────────────────────────────────

    async def get_shop(self, shop_id: int) -> dict:
        _check_rate_limit()
        resp = await self.client.get(
            f"/application/shops/{shop_id}",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def find_shops(self, shop_name: str) -> list[dict]:
        _check_rate_limit()
        resp = await self.client.get(
            "/application/shops",
            headers=self._auth_headers(),
            params={"shop_name": shop_name},
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    # ─── Listings API ────────────────────────────────────

    async def get_listings(self, shop_id: int, limit: int = 25, offset: int = 0, state: str = "active") -> list[dict]:
        _check_rate_limit()
        resp = await self.client.get(
            f"/application/shops/{shop_id}/listings",
            headers=self._auth_headers(),
            params={"limit": limit, "offset": offset, "state": state},
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    async def get_listing(self, listing_id: int) -> dict:
        _check_rate_limit()
        resp = await self.client.get(
            f"/application/listings/{listing_id}",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def create_listing(self, shop_id: int, **kwargs) -> dict:
        _check_rate_limit()
        resp = await self.client.post(
            f"/application/shops/{shop_id}/listings",
            headers=self._auth_headers(),
            json=kwargs,
        )
        resp.raise_for_status()
        return resp.json()

    async def update_listing(self, shop_id: int, listing_id: int, **updates) -> dict:
        _check_rate_limit()
        resp = await self.client.patch(
            f"/application/shops/{shop_id}/listings/{listing_id}",
            headers=self._auth_headers(),
            json=updates,
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_listing(self, shop_id: int, listing_id: int) -> dict:
        _check_rate_limit()
        resp = await self.client.delete(
            f"/application/shops/{shop_id}/listings/{listing_id}",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    # ─── Orders API ──────────────────────────────────────

    async def get_shop_receipts(self, shop_id: int, limit: int = 25, offset: int = 0) -> list[dict]:
        _check_rate_limit()
        resp = await self.client.get(
            f"/application/shops/{shop_id}/receipts",
            headers=self._auth_headers(),
            params={"limit": limit, "offset": offset},
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    # ─── Shipping ──────────────────────────────────────

    async def get_shipping_templates(self, shop_id: int) -> list[dict]:
        _check_rate_limit()
        resp = await self.client.get(
            f"/application/shops/{shop_id}/shipping-profiles",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    # ─── Inventory ───────────────────────────────────────

    async def get_listing_inventory(self, listing_id: int) -> dict:
        _check_rate_limit()
        resp = await self.client.get(
            f"/application/listings/{listing_id}/inventory",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    # ─── User ────────────────────────────────────────

    async def get_authenticated_user(self) -> dict:
        _check_rate_limit()
        resp = await self.client.get(
            "/application/users/me",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    # ─── Close ───────────────────────────────────────────

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


# ─── Global Client ──────────────────────────────────────────

etsy_client = EtsyAPIClient()
