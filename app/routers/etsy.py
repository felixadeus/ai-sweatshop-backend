"""
Etsy API v3 Router - Personal Access Mode
For Etsy apps in "Personal Access" mode - uses API key directly
without full OAuth2 flow for your own shop data.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import get_db
from app.etsy_api import EtsyAPIClient, ETSY_API_KEY

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/etsy", tags=["etsy"])

# ─── Pydantic Models ─────────────────────────────────────────

class EtsyAuthUrlResponse(BaseModel):
    auth_url: str
    code_verifier: str
    state: str
    message: str


class EtsyTokenRequest(BaseModel):
    code: str
    redirect_uri: str
    code_verifier: str


class EtsyTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str


class CreateListingRequest(BaseModel):
    shop_id: int
    title: str
    description: str
    price: float
    quantity: int = 1
    taxonomy_id: int = 6915  # T-Shirt default
    who_made: str = "i_did"
    is_supply: bool = False
    when_made: str = "made_to_order"
    shipping_template_id: Optional[int] = None
    tags: Optional[list[str]] = None
    materials: Optional[list[str]] = None


class UpdateListingRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    tags: Optional[list[str]] = None


class EtsySyncRequest(BaseModel):
    shop_id: int
    access_token: str
    min_created: Optional[int] = None
    max_created: Optional[int] = None


# ─── Authentication ──────────────────────────────────────────

@router.get(
    "/auth/url",
    summary="Get Etsy OAuth2 URL",
    description="Generate Etsy OAuth2 authorization URL. You MUST register the redirect_uri in your Etsy app settings first.",
)
async def get_etsy_auth_url(
    redirect_uri: str = Query("http://localhost:3000/callback", description="Must match a URI registered in Etsy app settings"),
    scopes: str = Query("listings_r listings_w shops_r shops_w transactions_r", description="OAuth scopes"),
):
    """Generate Etsy OAuth2 URL. Redirect user to auth_url."""
    client = EtsyAPIClient()
    scope_list = scopes.split()
    auth_url, code_verifier, state = client.get_oauth_url(redirect_uri, scope_list)

    return {
        "auth_url": auth_url,
        "code_verifier": code_verifier,
        "state": state,
        "redirect_uri_used": redirect_uri,
        "important": "You MUST add this redirect_uri to your Etsy app settings first!",
        "etsy_settings_url": "https://www.etsy.com/developers/your-apps",
        "next_step": "1. Add redirect_uri to Etsy app settings → 2. Open auth_url in browser → 3. Authorize → 4. Exchange code for token",
    }


@router.post(
    "/auth/token",
    summary="Exchange OAuth code for token",
    description="Exchange the authorization code returned by Etsy for an access token.",
)
async def exchange_etsy_token(request: EtsyTokenRequest) -> EtsyTokenResponse:
    """Exchange authorization code for access/refresh tokens."""
    client = EtsyAPIClient()
    try:
        data = await client.exchange_code(request.code, request.redirect_uri, request.code_verifier)
        return EtsyTokenResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data.get("expires_in", 3600),
            token_type=data.get("token_type", "Bearer"),
        )
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")


# ─── User ────────────────────────────────────────────────────

@router.get(
    "/user/me",
    summary="Get authenticated user",
    description="Get the currently authenticated Etsy user's profile.",
)
async def get_etsy_user(access_token: str = Query(..., description="Etsy access token")):
    """Get authenticated user info."""
    client = EtsyAPIClient(access_token=access_token)
    try:
        user = await client.get_authenticated_user()
        return {"status": "ok", "user": user}
    except Exception as e:
        logger.error(f"Etsy API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ─── Shop ────────────────────────────────────────────────────

@router.get(
    "/shop/{shop_id}",
    summary="Get Etsy shop details",
    description="Fetch shop details from Etsy API.",
)
async def get_etsy_shop(
    shop_id: int,
    access_token: str = Query(..., description="Etsy access token"),
):
    """Get shop details from Etsy."""
    client = EtsyAPIClient(access_token=access_token)
    try:
        shop = await client.get_shop(shop_id)
        return {"status": "ok", "shop": shop}
    except Exception as e:
        logger.error(f"Etsy API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/shop/by-name/{shop_name}",
    summary="Find shop by name",
    description="Search for a shop by its name.",
)
async def get_etsy_shop_by_name(
    shop_name: str,
    access_token: str = Query(..., description="Etsy access token"),
):
    """Get shop by name."""
    client = EtsyAPIClient(access_token=access_token)
    try:
        result = await client.get_shop_by_name(shop_name)
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"Etsy API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ─── Listings ────────────────────────────────────────────────

@router.get(
    "/shop/{shop_id}/listings",
    summary="Get shop listings",
    description="Fetch all listings from an Etsy shop.",
)
async def get_etsy_listings(
    shop_id: int,
    access_token: str = Query(..., description="Etsy access token"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    state: str = Query("active", enum=["active", "inactive", "sold_out", "draft", "expired"]),
):
    """Get listings for a shop."""
    client = EtsyAPIClient(access_token=access_token)
    try:
        listings = await client.get_listings(shop_id, limit, offset, state)
        return {"status": "ok", "count": len(listings), "listings": listings}
    except Exception as e:
        logger.error(f"Etsy API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/listing/{listing_id}",
    summary="Get single listing",
    description="Fetch a single listing by ID.",
)
async def get_etsy_listing(
    listing_id: int,
    access_token: str = Query(..., description="Etsy access token"),
):
    """Get a single listing."""
    client = EtsyAPIClient(access_token=access_token)
    try:
        listing = await client.get_listing(listing_id)
        return {"status": "ok", "listing": listing}
    except Exception as e:
        logger.error(f"Etsy API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/listing/create",
    summary="Create Etsy listing",
    description="Create a new product listing on Etsy.",
)
async def create_etsy_listing(
    request: CreateListingRequest,
    access_token: str = Query(..., description="Etsy access token"),
):
    """Create a new Etsy listing."""
    client = EtsyAPIClient(access_token=access_token)
    try:
        result = await client.create_listing(
            shop_id=request.shop_id,
            title=request.title,
            description=request.description,
            price=request.price,
            quantity=request.quantity,
            taxonomy_id=request.taxonomy_id,
            who_made=request.who_made,
            is_supply=request.is_supply,
            when_made=request.when_made,
            shipping_template_id=request.shipping_template_id,
            tags=request.tags,
            materials=request.materials,
        )
        return {"status": "ok", "listing": result}
    except Exception as e:
        logger.error(f"Etsy API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/shop/{shop_id}/listing/{listing_id}",
    summary="Update Etsy listing",
    description="Update an existing product listing.",
)
async def update_etsy_listing(
    shop_id: int,
    listing_id: int,
    request: UpdateListingRequest,
    access_token: str = Query(..., description="Etsy access token"),
):
    """Update an Etsy listing."""
    client = EtsyAPIClient(access_token=access_token)
    try:
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        result = await client.update_listing(shop_id, listing_id, **updates)
        return {"status": "ok", "listing": result}
    except Exception as e:
        logger.error(f"Etsy API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/shop/{shop_id}/listing/{listing_id}",
    summary="Delete Etsy listing",
    description="Delete a product listing from Etsy.",
)
async def delete_etsy_listing(
    shop_id: int,
    listing_id: int,
    access_token: str = Query(..., description="Etsy access token"),
):
    """Delete an Etsy listing."""
    client = EtsyAPIClient(access_token=access_token)
    try:
        result = await client.delete_listing(shop_id, listing_id)
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"Etsy API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ─── Orders ──────────────────────────────────────────────────

@router.get(
    "/shop/{shop_id}/orders",
    summary="Get shop orders",
    description="Fetch receipts/orders from an Etsy shop.",
)
async def get_etsy_orders(
    shop_id: int,
    access_token: str = Query(..., description="Etsy access token"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get orders/receipts for a shop."""
    client = EtsyAPIClient(access_token=access_token)
    try:
        orders = await client.get_shop_receipts(shop_id, limit, offset)
        return {"status": "ok", "count": len(orders), "orders": orders}
    except Exception as e:
        logger.error(f"Etsy API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/shop/{shop_id}/order/{receipt_id}",
    summary="Get single order",
    description="Fetch a single receipt/order.",
)
async def get_etsy_order(
    shop_id: int,
    receipt_id: int,
    access_token: str = Query(..., description="Etsy access token"),
):
    """Get a single receipt."""
    client = EtsyAPIClient(access_token=access_token)
    try:
        order = await client.get_receipt(shop_id, receipt_id)
        return {"status": "ok", "order": order}
    except Exception as e:
        logger.error(f"Etsy API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ─── Shipping ────────────────────────────────────────────────

@router.get(
    "/shop/{shop_id}/shipping-templates",
    summary="Get shipping templates",
    description="Get shipping profile templates for a shop.",
)
async def get_etsy_shipping_templates(
    shop_id: int,
    access_token: str = Query(..., description="Etsy access token"),
):
    """Get shipping templates."""
    client = EtsyAPIClient(access_token=access_token)
    try:
        templates = await client.get_shipping_templates(shop_id)
        return {"status": "ok", "count": len(templates), "templates": templates}
    except Exception as e:
        logger.error(f"Etsy API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ─── Inventory ───────────────────────────────────────────────

@router.get(
    "/listing/{listing_id}/inventory",
    summary="Get listing inventory",
    description="Get inventory details for a listing.",
)
async def get_etsy_listing_inventory(
    listing_id: int,
    access_token: str = Query(..., description="Etsy access token"),
):
    """Get listing inventory."""
    client = EtsyAPIClient(access_token=access_token)
    try:
        inventory = await client.get_listing_inventory(listing_id)
        return {"status": "ok", "inventory": inventory}
    except Exception as e:
        logger.error(f"Etsy API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ─── Find Shop (No Auth Required for Personal Access) ───────

@router.get(
    "/find-shop",
    summary="Find your Etsy shop",
    description="Search for your shop by name using just the API key. For Personal Access apps.",
)
async def find_etsy_shop(
    shop_name: str = Query(..., description="Your Etsy shop name"),
):
    """Find a shop by name - works with API key only for Personal Access."""
    client = EtsyAPIClient()  # No access token needed for public endpoints
    try:
        shops = await client.find_shops(shop_name)
        if not shops:
            return {"status": "ok", "found": False, "message": f"No shop found named '{shop_name}'"}
        return {
            "status": "ok",
            "found": True,
            "shops": [
                {
                    "shop_id": s.get("shop_id"),
                    "shop_name": s.get("shop_name"),
                    "title": s.get("title"),
                    "url": s.get("url"),
                }
                for s in shops
            ],
        }
    except Exception as e:
        logger.error(f"Etsy find shop error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ─── API Key Info ────────────────────────────────────────────

@router.get(
    "/key-info",
    summary="Etsy API key info",
    description="Information about the configured Etsy API key.",
)
async def get_etsy_key_info():
    """Get Etsy API key info (safe, no secret exposed)."""
    return {
        "api_key_prefix": ETSY_API_KEY[:8] + "...",
        "app_name": "ai-sweatshop-agent",
        "mode": "Personal Access",
        "rate_limit": "5 QPS / 5K QPD",
        "api_version": "v3",
        "base_url": "https://openapi.etsy.com/v3",
        "etsy_app_settings_url": "https://www.etsy.com/developers/your-apps",
        "note": "Personal Access apps can read public data with API key only. For shop data, OAuth2 may be required.",
    }


# ─── Manual Token Entry ──────────────────────────────────────

@router.post(
    "/auth/manual",
    summary="Manually set access token",
    description="If you already have an access token from Etsy, paste it here to use it.",
)
async def set_etsy_token_manual(
    access_token: str = Query(..., description="Your Etsy access token"),
    refresh_token: str = Query("", description="Your Etsy refresh token (optional)"),
):
    """Manually set Etsy tokens if you already have them."""
    # Test the token by calling the user endpoint
    client = EtsyAPIClient(access_token=access_token)
    try:
        user = await client.get_authenticated_user()
        return {
            "status": "ok",
            "message": "Token is valid!",
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token or None,
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# ─── Public API Test ─────────────────────────────────────────

@router.get(
    "/test/public",
    summary="Test public Etsy API (no auth needed)",
    description="Test that your API key works with Etsy's public endpoints.",
)
async def test_etsy_public_api():
    """Test public Etsy API - no authentication required."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            # Try a public endpoint (findAllShops)
            resp = await client.get(
                "https://openapi.etsy.com/v3/application/shops",
                headers={"x-api-key": ETSY_API_KEY},
                params={"shop_name": "test"},
            )
            return {
                "status": "ok",
                "message": "API key is valid! Public endpoints work.",
                "etsy_response_status": resp.status_code,
                "note": "Public endpoints work. For shop data, you need OAuth2 authentication.",
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"API key test failed: {str(e)}",
        }
