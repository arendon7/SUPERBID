from __future__ import annotations
import hmac,os
from fastapi import Request,HTTPException
ADMIN_TOKEN=os.getenv("SUPERBID_ADMIN_TOKEN","").strip(); DASHBOARD_TOKEN=os.getenv("SUPERBID_DASHBOARD_TOKEN","").strip()
def _token_from_request(request:Request)->str:
    auth=request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):return auth[7:].strip()
    return (request.headers.get("x-superbid-token") or request.query_params.get("token") or "").strip()
def require_admin(request:Request):
    if not ADMIN_TOKEN:raise HTTPException(status_code=503,detail="SUPERBID_ADMIN_TOKEN no configurado")
    supplied=_token_from_request(request)
    if not supplied or not hmac.compare_digest(supplied,ADMIN_TOKEN):raise HTTPException(status_code=401,detail="No autorizado")
def dashboard_allowed(request:Request)->bool:
    if not DASHBOARD_TOKEN:return True
    supplied=_token_from_request(request); return bool(supplied and hmac.compare_digest(supplied,DASHBOARD_TOKEN))
