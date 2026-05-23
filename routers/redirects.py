"""
Cross-origin and intra-site 301 redirects.

Registered BEFORE static-file mounts in main.py so these routes shadow the
StaticFiles handler for the listed paths. Adopted on 2026-05-23 when the
Caddyfile layer was deprecated and Cloudflare → FastAPI became the only
serving path (no Caddy, no nginx between Cloudflare and the API container).

Any path listed here MUST be removed from web/docs/ on disk; otherwise the
static mount would still serve the old content if this router were ever
re-registered after the mounts.
"""
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


# === Retired pitch documents → research hub ===
@router.get("/docs/bluepaper", include_in_schema=False)
@router.get("/docs/bluepaper/", include_in_schema=False)
@router.get("/docs/bluepaper.pdf", include_in_schema=False)
def bluepaper_redirect():
    return RedirectResponse(url="/research", status_code=301)


@router.get("/docs/executive-summary", include_in_schema=False)
@router.get("/docs/executive-summary.pdf", include_in_schema=False)
def executive_summary_redirect():
    return RedirectResponse(url="/research", status_code=301)


# === Earlier whitepaper drafts → new VMP-1.0 specification ===
@router.get("/docs/whitepaper-v1", include_in_schema=False)
@router.get("/docs/whitepaper-v1.html", include_in_schema=False)
@router.get("/docs/whitepaper-part2", include_in_schema=False)
@router.get("/docs/whitepaper-part2.html", include_in_schema=False)
def whitepaper_legacy_redirect():
    return RedirectResponse(url="/docs/whitepaper/", status_code=301)


# === /project gateway → AgenticEconomy.dev (cross-origin) ===
@router.get("/project", include_in_schema=False)
@router.get("/project/", include_in_schema=False)
def project_gateway():
    return RedirectResponse(url="https://agenticeconomy.dev", status_code=301)
