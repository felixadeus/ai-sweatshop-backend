"""
Etsy OAuth2 - Dead Simple Version
No state validation, correct port, single-tab flow.
"""

import logging
import secrets
import base64
import httpx
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.etsy_api import EtsyAPIClient, ETSY_API_KEY, ETSY_API_SECRET

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/etsy/oauth", tags=["etsy-oauth"])

# ─── Token store ─────────────────────────────────────────────
_etsy_tokens = {}


def _page(title, content, border_color="#1a1a28"):
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0a0a0e;
            color: #e8e6f0;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .card {{
            background: #111118;
            border: 1px solid {border_color};
            border-radius: 16px;
            padding: 40px;
            max-width: 540px;
            width: 100%;
        }}
        .logo {{
            font-family: 'Orbitron', monospace;
            font-weight: 700;
            font-size: 18px;
            color: #FF5E00;
            margin-bottom: 6px;
        }}
        .sub {{ color: #6b6880; font-size: 13px; margin-bottom: 24px; }}
        .btn {{
            display: block;
            width: 100%;
            background: linear-gradient(135deg, #FF5E00, #FFB800);
            color: #050507;
            text-align: center;
            text-decoration: none;
            padding: 16px;
            border-radius: 10px;
            font-weight: 700;
            font-size: 15px;
            border: none;
            cursor: pointer;
            margin: 12px 0;
            transition: transform 0.15s, box-shadow 0.15s;
        }}
        .btn:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px rgba(255,94,0,0.3); }}
        .btn-green {{ background: linear-gradient(135deg, #39FF14, #00cc44); }}
        .btn-green:hover {{ box-shadow: 0 8px 24px rgba(57,255,20,0.3); }}
        .btn-blue {{ background: linear-gradient(135deg, #00F0FF, #0088ff); }}
        .divider {{
            text-align: center;
            color: #3a3750;
            font-size: 12px;
            margin: 20px 0;
            position: relative;
        }}
        .divider::before {{
            content: '';
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 1px;
            background: #1a1a28;
        }}
        .divider span {{ background: #111118; padding: 0 12px; position: relative; }}
        input[type="text"] {{
            width: 100%;
            background: #0a0a0e;
            border: 1px solid #1a1a28;
            border-radius: 8px;
            padding: 12px 14px;
            color: #e8e6f0;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            margin: 8px 0;
        }}
        input:focus {{ outline: none; border-color: #FF5E00; }}
        label {{
            display: block;
            color: #6b6880;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 16px;
        }}
        .msg {{
            background: rgba(0,240,255,0.06);
            border-left: 3px solid #00F0FF;
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            font-size: 12px;
            color: #e8e6f0;
            margin: 12px 0;
        }}
        .msg-error {{ background: rgba(255,0,60,0.08); border-left-color: #FF003C; }}
        .msg-success {{ background: rgba(57,255,20,0.08); border-left-color: #39FF14; }}
        code {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: #39FF14;
            background: #0a0a0e;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        .small {{ font-size: 11px; color: #6b6880; margin-top: 4px; }}
        .token {{
            background: #0a0a0e;
            border: 1px solid #1a1a28;
            border-radius: 8px;
            padding: 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: #00F0FF;
            word-break: break-all;
            margin: 8px 0;
        }}
        h1 {{ font-size: 20px; margin-bottom: 8px; }}
        ul {{ margin: 8px 0 8px 20px; color: #6b6880; font-size: 12px; }}
        li {{ margin: 4px 0; }}
    </style>
</head>
<body>
    <div class="card">
        {content}
    </div>
</body>
</html>""")


# ─── Step 1: Start Page ──────────────────────────────────────

@router.get("/start", response_class=HTMLResponse)
async def oauth_start():
    """Simple start page - click, authorize, done."""

    redirect_uri = "http://localhost:8000/api/etsy/oauth/callback"
    scopes = "listings_r listings_w shops_r shops_w transactions_r"
    scope_list = scopes.split()

    client = EtsyAPIClient()
    auth_url, code_verifier, state = client.get_oauth_url(redirect_uri, scope_list)

    # Store code_verifier
    cv_key = secrets.token_urlsafe(16)
    _etsy_tokens[f"cv_{cv_key}"] = {
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
        "created": datetime.now(timezone.utc).isoformat(),
    }

    content = f"""
        <div class="logo">🔗 CONNECT YOUR ETSY SHOP</div>
        <div class="sub">Link your Etsy store to the AI Sweatshop system</div>

        <a href="{auth_url}" class="btn">→ Authorize with Etsy</a>
        <div class="small">This will open Etsy login in a new tab. After authorizing, you'll be redirected back here.</div>

        <div class="divider"><span>TROUBLESHOOTING</span></div>

        <div class="msg">
            If you see "app not recognized" on Etsy, click the button above anyway, then copy the <code>code=</code> part from the URL and paste it below.
        </div>

        <form action="/api/etsy/oauth/finish" method="GET">
            <label>Or paste authorization code here:</label>
            <input type="text" name="code" placeholder="Paste the code from Etsy redirect URL...">
            <input type="hidden" name="cvk" value="{cv_key}">
            <button type="submit" class="btn btn-blue" style="margin-top:4px;">Complete Connection</button>
        </form>
"""
    return _page("Connect Etsy", content)


# ─── Step 2: Etsy Callback ───────────────────────────────────

@router.get("/callback", response_class=HTMLResponse)
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: str = Query(None),
):
    """Etsy redirects here after authorization."""

    if error:
        content = f"""
            <h1 style="color:#FF003C;">❌ Etsy Error</h1>
            <div class="msg msg-error">{error}</div>
            <ul>
                <li>Make sure you're logged into the same Etsy account that created the app</li>
                <li>Your app is in "Personal Access" mode - try logging in with your developer account</li>
                <li>The callback URL <code>http://localhost:8000/api/etsy/oauth/callback</code> must be saved in your Etsy app settings</li>
            </ul>
            <a href="/api/etsy/oauth/start" class="btn">← Try Again</a>
        """
        return _page("Error", content, "#FF003C")

    # Show code + button to exchange
    content = f"""
        <h1 style="color:#39FF14;">✅ Code Received!</h1>
        <div class="sub">Etsy sent us an authorization code. Click below to exchange it for a token.</div>
        <div class="token">{code[:60]}...</div>
        <form action="/api/etsy/oauth/finish" method="GET">
            <input type="hidden" name="code" value="{code}">
            <button type="submit" class="btn btn-green">Exchange Code for Access Token →</button>
        </form>
        <div class="small">This code expires in 60 seconds - hurry!</div>
    """
    return _page("Code Captured", content, "#39FF14")


# ─── Step 3: Finish (Exchange Code for Token) ────────────────

@router.get("/finish", response_class=HTMLResponse)
async def oauth_finish(
    code: str = Query(...),
    cvk: str = Query(""),
):
    """Exchange authorization code for access token."""

    redirect_uri = "http://localhost:8000/api/etsy/oauth/callback"
    session = _etsy_tokens.get(f"cv_{cvk}") if cvk else None
    code_verifier = session.get("code_verifier") if session else None

    # Fallback: try direct exchange without code_verifier
    try:
        if code_verifier:
            client = EtsyAPIClient()
            data = await client.exchange_code(code, redirect_uri, code_verifier)
        else:
            # Direct exchange attempt
            async with httpx.AsyncClient() as c:
                resp = await c.post(
                    "https://api.etsy.com/v3/public/oauth/token",
                    data={
                        "grant_type": "authorization_code",
                        "client_id": ETSY_API_KEY,
                        "redirect_uri": redirect_uri,
                        "code": code,
                    },
                )
                if resp.status_code != 200:
                    raise Exception(f"HTTP {resp.status_code}: {resp.text[:300]}")
                data = resp.json()

        # Save token
        token = data.get("access_token", "")
        refresh = data.get("refresh_token", "")
        _etsy_tokens["connected"] = {
            "access_token": token,
            "refresh_token": refresh,
            "created": datetime.now(timezone.utc).isoformat(),
        }

        # Cleanup
        if cvk and f"cv_{cvk}" in _etsy_tokens:
            del _etsy_tokens[f"cv_{cvk}"]

        masked = token[:20] + "..." if len(token) > 20 else token
        content = f"""
            <h1 style="color:#39FF14;">✅ Etsy Connected!</h1>
            <div class="sub">Your shop is now linked to the AI Sweatshop.</div>
            <label>Access Token (save this):</label>
            <div class="token">{masked}</div>
            <a href="/api/etsy/oauth/status" class="btn">Check Status</a>
            <a href="/" class="btn" style="background:transparent;border:1px solid #FF5E00;color:#FF5E00;">Dashboard</a>
        """
        return _page("Connected!", content, "#39FF14")

    except Exception as e:
        error_msg = str(e)
        content = f"""
            <h1 style="color:#FF003C;">❌ Token Exchange Failed</h1>
            <div class="msg msg-error">{error_msg[:200]}</div>
            <div class="sub"><b>Why this happens with Personal Access apps:</b></div>
            <ul>
                <li>Personal Access apps use a different authentication flow</li>
                <li>The standard OAuth authorization may not work</li>
                <li>You may need to request "Commercial Access" from Etsy</li>
            </ul>
            <div class="msg">
                <b>Solution:</b> In your Etsy developer dashboard, click the 3 dots on your app and select <b>"Request commercial access"</b>. Once approved, the OAuth flow will work.
            </div>
            <a href="/api/etsy/oauth/start" class="btn">← Try Again</a>
            <a href="https://www.etsy.com/developers/your-apps" class="btn" style="background:transparent;border:1px solid #FF5E00;color:#FF5E00;" target="_blank">Open Etsy Developer →</a>
        """
        return _page("Error", content, "#FF003C")


# ─── Status ──────────────────────────────────────────────────

@router.get("/status", response_class=HTMLResponse)
async def oauth_status():
    connected = _etsy_tokens.get("connected", {})
    has_token = bool(connected.get("access_token"))

    color = "#39FF14" if has_token else "#FF003C"
    title = "✅ CONNECTED" if has_token else "❌ NOT CONNECTED"
    msg = "Your Etsy shop is linked and ready!" if has_token else "Connect your Etsy shop to start managing listings."
    btn = "Reconnect" if has_token else "Connect Now"

    content = f"""
        <h1 style="color:{color};">{title}</h1>
        <div class="sub">{msg}</div>
        <a href="/api/etsy/oauth/start" class="btn">{btn}</a>
        <div class="small" style="margin-top:16px;">
            API Key: <code>{ETSY_API_KEY[:12]}...</code> · App: ai-sweatshop-agent · Mode: Personal Access
        </div>
    """
    return _page("Etsy Status", content, color)
