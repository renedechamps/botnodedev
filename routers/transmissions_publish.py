"""Transmissions Publishing Service.

Accepts a POST with title, content, tag, etc. and automatically:
1. Creates the HTML file from the transmission template
2. Updates the index page
3. Updates the RSS feed
4. Syncs to all serving directories
"""

import os
import re
import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from dependencies import STATIC_ROOT, TRANSMISSIONS_ROOT, require_admin_key

router = APIRouter(tags=["transmissions"], prefix="/v1/transmissions")

# All directories that serve transmissions
SYNC_DIRS = [
    TRANSMISSIONS_ROOT,  # /app/static/transmissions
    os.path.join(os.path.dirname(STATIC_ROOT), "web", "transmissions"),
]

# Add /var/www/botnode_v2/transmissions if it exists (Caddy serves from here)
CADDY_TX_DIR = "/var/www/botnode_v2/transmissions"
if os.path.isdir(os.path.dirname(CADDY_TX_DIR)):
    SYNC_DIRS.append(CADDY_TX_DIR)


class TransmissionPublish(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    content_html: str = Field(..., min_length=10)
    tag: str = Field(default="ecosystem")
    tag_color: str | None = Field(default=None, description="Custom tag color hex, e.g. #ffab00")
    description: str = Field(..., min_length=10, max_length=500)
    author: str = Field(default="rene-dechamps-otamendi")
    author_display: str = Field(default="René Dechamps Otamendi")
    source_url: str | None = Field(default=None, description="Original URL on MoltBook or other platform")
    source_label: str | None = Field(default=None, description="e.g. 'MoltBook', 'renedechamps.com'")


TAG_STYLES = {
    "protocol": 'class="tx-tag protocol"',
    "security": 'class="tx-tag security"',
    "ecosystem": 'class="tx-tag ecosystem"',
    "transmission": 'class="tx-tag transmission"',
    "sync": 'class="tx-tag sync"',
    "analysis": 'class="tx-tag analysis"',
    "bounty": 'class="tx-tag bounty"',
}


def _slugify(title: str) -> str:
    """Convert title to URL-safe slug."""
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')[:80]


def _get_next_transmission_number() -> int:
    """Count existing transmissions to determine the next number."""
    count = 0
    for f in os.listdir(TRANSMISSIONS_ROOT):
        if f.endswith('.html') and f not in ('index.html',):
            count += 1
    return count + 1


def _build_tag_html(tag: str, tag_color: str | None) -> str:
    """Build the tag HTML element."""
    if tag_color:
        bg = tag_color.replace('#', '')
        return f'<span class="tx-tag" style="background:rgba({int(bg[:2],16)},{int(bg[2:4],16)},{int(bg[4:6],16)},.12);color:{tag_color}">{tag}</span>'
    if tag.lower() in TAG_STYLES:
        return f'<span {TAG_STYLES[tag.lower()]}>{tag}</span>'
    return f'<span class="tx-tag ecosystem">{tag}</span>'


def _build_source_block(source_url: str | None, source_label: str | None) -> str:
    """Build the source link block if provided."""
    if not source_url:
        return ""
    label = source_label or "Original post"
    return f'''
<div style="margin:3rem 0;padding:2rem;background:var(--surface-2);border:1px solid var(--border);border-left:3px solid var(--cyan)">
  <p style="font-family:var(--font-mono);font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--cyan);margin-bottom:1rem">Originally published on {label}</p>
  <a href="{source_url}" target="_blank" rel="noopener noreferrer" style="display:inline-flex;align-items:center;gap:8px;padding:12px 24px;background:var(--cyan);color:#000;font-family:var(--font-mono);font-size:13px;font-weight:700;border-radius:6px;text-decoration:none;letter-spacing:0.5px">Read the original post →</a>
</div>'''


def _read_template() -> str:
    """Read the CSS + chrome from an existing transmission."""
    # Find the most recent transmission to use as template
    template_file = os.path.join(TRANSMISSIONS_ROOT, "founder-log-origin-story.html")
    if not os.path.exists(template_file):
        # Fallback: find any .html that isn't index
        for f in sorted(os.listdir(TRANSMISSIONS_ROOT), reverse=True):
            if f.endswith('.html') and f != 'index.html':
                template_file = os.path.join(TRANSMISSIONS_ROOT, f)
                break

    with open(template_file, 'r') as fh:
        return fh.read()


def _extract_css_and_chrome(template_html: str) -> tuple[str, str, str]:
    """Extract the <style> block, header HTML, and footer HTML from template."""
    # Extract everything from <style> to </style>
    style_match = re.search(r'<style>(.*?)</style>', template_html, re.DOTALL)
    style = style_match.group(1) if style_match else ""

    # Extract header
    header_match = re.search(r'(<header.*?</header>)', template_html, re.DOTALL)
    header = header_match.group(1) if header_match else ""

    # Extract footer (from the build-on-grid CTA through </footer>)
    footer_match = re.search(r'(<div style="border-top:1px solid #1e1e1e;margin:4rem.*?</footer>)', template_html, re.DOTALL)
    footer = footer_match.group(1) if footer_match else ""

    return style, header, footer


def _build_transmission_html(data: TransmissionPublish, slug: str, date: str, tx_number: int) -> str:
    """Build the complete HTML file for a transmission."""
    template = _read_template()
    style, header, footer = _extract_css_and_chrome(template)

    tag_html = _build_tag_html(data.tag, data.tag_color)
    source_block = _build_source_block(data.source_url, data.source_label)

    schema_json = (
        '{"@context":"https://schema.org","@type":"Article",'
        f'"headline":"{data.title}",'
        f'"description":"{data.description}",'
        f'"datePublished":"{date}",'
        f'"author":{{"@type":"Person","name":"{data.author_display}"}},'
        '"publisher":{"@type":"Organization","name":"BotNode™",'
        '"logo":{"@type":"ImageObject","url":"https://botnode.io/static/assets/botnode-logo.png"}},'
        f'"url":"https://botnode.io/transmissions/{slug}"}}'
    )

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{data.title} | BotNode™</title>
<meta name="description" content="{data.description}">
<meta property="og:title" content="{data.title} | BotNode™">
<meta property="og:description" content="{data.description}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://botnode.io/transmissions/{slug}">
<meta property="og:image" content="https://botnode.io/static/assets/og-card.png">
<link rel="canonical" href="https://botnode.io/transmissions/{slug}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@BotNodeio">
<link rel="icon" type="image/png" sizes="32x32" href="/static/assets/favicon.png">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="alternate" type="application/rss+xml" title="BotNode™ Transmissions" href="/transmissions/rss.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@300;400;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
<noscript><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@300;400;600;700&display=swap" rel="stylesheet"></noscript>
<script type="application/ld+json">
{schema_json}
</script>
<style>
{style}
</style>
</head>
<body>
{header}

<main class="tx-page">
  <a href="/transmissions" class="tx-back">← All Transmissions</a>
  <div class="tx-post-meta">
    <span class="tx-date">{date}</span>
    {tag_html}
    <a href="/transmissions/author/{data.author}" class="tx-author">{data.author_display}</a>
  </div>
  <h1 class="tx-post-title">{data.title.upper()}</h1>

  <div class="tx-content">

{data.content_html}

{source_block}

<p style="margin-top:3rem;padding-top:2rem;border-top:1px solid var(--border);font-family:var(--font-mono);font-size:12px;color:var(--text-dim);line-height:2">
— Transmission {tx_number:03d}<br>
{date}
</p>

</div>
</main>

{footer}
<script>
document.getElementById('hamburger').addEventListener('click', function() {{
  document.getElementById('navLinks').classList.toggle('open');
}});
document.querySelectorAll('.nav-links a').forEach(function(a) {{
  a.addEventListener('click', function() {{
    document.getElementById('navLinks').classList.remove('open');
  }});
}});
</script>
</body>
</html>'''


def _update_index(slug: str, data: TransmissionPublish, date: str) -> None:
    """Insert a new entry at the top of the transmissions index."""
    index_path = os.path.join(TRANSMISSIONS_ROOT, "index.html")
    if not os.path.exists(index_path):
        return

    with open(index_path, 'r') as fh:
        index_html = fh.read()

    tag_html = _build_tag_html(data.tag, data.tag_color)
    source_html = ""
    if data.source_url:
        label = data.source_label or "Original"
        source_html = f'''
      <div class="tx-source">
        <a href="{data.source_url}" target="_blank" rel="noopener noreferrer">Read the original on {label} →</a>
      </div>'''

    new_entry = f'''    <article class="tx-entry" id="{slug}">
      <div class="tx-entry-meta">
        <span class="tx-date">{date}</span>
        {tag_html}
        <a href="/transmissions/author/{data.author}" class="tx-author">{data.author_display}</a>
      </div>
      <h3><a href="/transmissions/{slug}">{data.title}</a></h3>
      <p>{data.description}</p>{source_html}
    </article>
'''

    # Insert after the first tx-entry or after a known marker
    # Find the first <article class="tx-entry" and insert before it
    marker = '<article class="tx-entry"'
    if marker in index_html:
        index_html = index_html.replace(marker, new_entry + '    ' + marker, 1)
    else:
        # Fallback: insert before </main> or before the old tx-card section
        marker2 = '<article class="tx-card"'
        if marker2 in index_html:
            index_html = index_html.replace(marker2, new_entry + '    ' + marker2, 1)

    with open(index_path, 'w') as fh:
        fh.write(index_html)


def _update_rss(slug: str, data: TransmissionPublish, date: str) -> None:
    """Add a new item to the RSS feed."""
    rss_path = os.path.join(TRANSMISSIONS_ROOT, "rss.xml")
    if not os.path.exists(rss_path):
        return

    with open(rss_path, 'r') as fh:
        rss_xml = fh.read()

    pub_date = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')

    new_item = f'''    <item>
      <title>{data.title}</title>
      <link>https://botnode.io/transmissions/{slug}</link>
      <description>{data.description}</description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="true">https://botnode.io/transmissions/{slug}</guid>
    </item>
'''

    # Insert after <channel> ... first <item> or after </lastBuildDate>
    if '<item>' in rss_xml:
        rss_xml = rss_xml.replace('<item>', new_item + '    <item>', 1)
    elif '</lastBuildDate>' in rss_xml:
        rss_xml = rss_xml.replace('</lastBuildDate>', f'</lastBuildDate>\n{new_item}', 1)

    # Update lastBuildDate
    rss_xml = re.sub(
        r'<lastBuildDate>.*?</lastBuildDate>',
        f'<lastBuildDate>{pub_date}</lastBuildDate>',
        rss_xml
    )

    with open(rss_path, 'w') as fh:
        fh.write(rss_xml)


def _sync_to_all_dirs(slug: str) -> None:
    """Copy the new/updated files to all serving directories."""
    source_dir = TRANSMISSIONS_ROOT
    files_to_sync = [f"{slug}.html", "index.html", "rss.xml"]

    for target_dir in SYNC_DIRS:
        if target_dir == source_dir:
            continue
        os.makedirs(target_dir, exist_ok=True)
        for fname in files_to_sync:
            src = os.path.join(source_dir, fname)
            dst = os.path.join(target_dir, fname)
            if os.path.exists(src):
                shutil.copy2(src, dst)


@router.post("/publish")
async def publish_transmission(data: TransmissionPublish, request: Request):
    """Publish a new transmission. Requires admin key."""
    require_admin_key(request)

    date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    slug = _slugify(data.title)
    tx_number = _get_next_transmission_number()

    # Check slug doesn't already exist
    target_path = os.path.join(TRANSMISSIONS_ROOT, f"{slug}.html")
    if os.path.exists(target_path):
        raise HTTPException(status_code=409, detail=f"Transmission '{slug}' already exists")

    # 1. Create HTML file
    html = _build_transmission_html(data, slug, date, tx_number)
    with open(target_path, 'w') as fh:
        fh.write(html)

    # 2. Update index
    _update_index(slug, data, date)

    # 3. Update RSS
    _update_rss(slug, data, date)

    # 4. Sync to all serving directories
    _sync_to_all_dirs(slug)

    url = f"https://botnode.io/transmissions/{slug}"

    return JSONResponse(status_code=201, content={
        "status": "published",
        "slug": slug,
        "url": url,
        "transmission_number": tx_number,
        "date": date,
    })
