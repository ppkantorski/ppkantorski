#!/usr/bin/env python3
"""
Keeps the profile's badges as SVG files in this repo (.github/badges/), so the README never
depends on img.shields.io while someone is viewing it.

  - Dynamic badges (latest / downloads / issues / stars): the values come from the GitHub API;
    the SVG is rendered by shields.io once, here, and only when its value changed (or its file
    is missing). The .json files are still written for anything that reads them.
    "latest" is also rendered with its label (<repo>-latest-label.svg) for the repos' own
    READMEs, which link these files by their raw.githubusercontent.com URL.
  - Static badges (STATIC_BADGES below): rendered once, and again only if the file is missing.
    To change one, edit its URL here and delete its .svg (or set FORCE_STATIC=1).

If shields.io or the API can't be reached, the existing file is kept, so a badge never
disappears; it just updates on a later run.
"""
import os
import json
import math
import time
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote, urlsplit, urlunsplit
from urllib.error import URLError

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
FORCE_STATIC = os.environ.get('FORCE_STATIC', '') == '1'
OWNER = 'ppkantorski'
BADGES_DIR = '.github/badges'
STATIC_DIR = os.path.join(BADGES_DIR, 'static')

REPOS = [
    {'name': 'Ultrahand-Overlay',      'has_releases': True},
    {'name': 'libultrahand',           'has_releases': True},
    {'name': 'nx-ovlloader',           'has_releases': True},
    {'name': 'Ultrahand-Packages',     'has_releases': False},
    {'name': 'UltraGB-Overlay',        'has_releases': True},
    {'name': 'Tetris-Overlay',         'has_releases': True},
    {'name': 'sys-tune',               'has_releases': True},
    {'name': 'ovl-sysmodules',         'has_releases': True},
    {'name': 'sys-clk',                'has_releases': True},
    {'name': 'Status-Monitor-Overlay', 'has_releases': True},
    {'name': 'FPSLocker',              'has_releases': True},
    {'name': 'ReverseNX-RT',           'has_releases': True},
    {'name': 'Fizeau',                 'has_releases': True},
    {'name': 'QuickNTP',               'has_releases': True},
    {'name': 'sysdvr-overlay',         'has_releases': True},
    {'name': 'NX-FanControl',          'has_releases': True},
    {'name': 'HOC-Toolkit',            'has_releases': True},
    {'name': 'Alchemist',              'has_releases': True},
    {'name': 'Memory-Kit',             'has_releases': True},
    {'name': '7th-Heaven-NX',          'has_releases': True},
]

# Static badges: file name (in .github/badges/static/) -> the shields.io URL it is rendered from
STATIC_BADGES = {
    'skill-c.svg':           'https://img.shields.io/badge/C-A8B9CC?style=flat&logo=c&logoColor=black',
    'skill-cpp.svg':         'https://img.shields.io/badge/C%2B%2B-00599C?style=flat&logo=cplusplus&logoColor=white',
    'skill-python.svg':      'https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white',
    'skill-embedded.svg':    'https://img.shields.io/badge/Embedded_Systems-00C1DE?style=flat&logo=arm&logoColor=white',
    'skill-systems.svg':     'https://img.shields.io/badge/Systems_Design-025E8C?style=flat&logo=dependabot&logoColor=white',
    'skill-dsp.svg':         'https://img.shields.io/badge/Signal_Processing-8CAAE6?style=flat&logo=scipy&logoColor=white',
    'skill-ml.svg':          'https://img.shields.io/badge/ML-FF6F00?style=flat&logo=tensorflow&logoColor=white',
    'skill-ai.svg':          'https://img.shields.io/badge/AI-EE4C2C?style=flat&logo=pytorch&logoColor=white',
    'skill-uiux.svg':        'https://img.shields.io/badge/UI%2FUX-A259FF?style=flat&logo=figma&logoColor=white',
    'download.svg':          'https://img.shields.io/badge/-⬇-2ea043?style=flat',
    'platform-switch.svg':   'https://img.shields.io/badge/platform-Switch-898c8c?logo=C++.svg',
    'language-c.svg':        'https://img.shields.io/badge/language-C-ba1632?logo=C.svg',
    'language-cpp.svg':      'https://img.shields.io/badge/language-C++-ba1632?logo=C++.svg',
    'language-python.svg':   'https://img.shields.io/badge/language-Python-ba1632?logo=Python.svg',
    'language-ultrascript.svg': 'https://img.shields.io/badge/language-UltraScript-ba1632.svg',
    'license-gplv2.svg':     'https://img.shields.io/badge/license-GPLv2-189c11.svg',
    'license-gplv3.svg':     'https://img.shields.io/badge/license-GPLv3-189c11.svg',
    'license-isc.svg':       'https://img.shields.io/badge/license-ISC-189c11.svg',
    'kofi.svg':              'https://img.shields.io/badge/Support_me_on_Ko--fi!-FF5E5B?style=flat&logo=ko-fi&logoColor=white',
    'sponsor.svg':           'https://img.shields.io/badge/Sponsor-1a1a2e?style=flat&logo=githubsponsors&logoColor=ff69b4',
}

def github_api(endpoint):
    url = f'https://api.github.com{endpoint}'
    req = Request(url)
    if GITHUB_TOKEN:
        req.add_header('Authorization', f'token {GITHUB_TOKEN}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except (URLError, OSError, ValueError) as e:
        print(f'  API error for {endpoint}: {e}')
        return None

def github_api_all_pages(endpoint):
    """Fetch all pages of a paginated GitHub API endpoint. None if any page failed."""
    results = []
    page = 1
    while True:
        sep = '&' if '?' in endpoint else '?'
        data = github_api(f'{endpoint}{sep}per_page=100&page={page}')
        if data is None:
            return None   # a failed page would undercount: keep the old badge
        results.extend(data)
        if len(data) < 100:
            break
        page += 1
    return results

def format_downloads(n):
    if n >= 1_000_000:
        v = n / 1_000_000
        return f'{int(v)}M' if v >= 100 else f'{math.floor(v * 10) / 10:.1f}M'
    elif n >= 1_000:
        v = n / 1_000
        return f'{int(v)}k' if v >= 100 else f'{math.floor(v * 10) / 10:.1f}k'
    return str(n)

def fetch_svg(url):
    """The badge SVG from shields.io, or None. Retried a few times; anything that isn't an SVG
    (an error page, an empty reply) counts as a failure."""
    parts = urlsplit(url)
    url = urlunsplit(parts._replace(path=quote(parts.path, safe='/%')))   # e.g. the ⬇ in a path
    for attempt in range(3):
        try:
            req = Request(url, headers={'User-Agent': 'ppkantorski-badges'})
            with urlopen(req, timeout=20) as resp:
                body = resp.read()
            if resp.status == 200 and body.lstrip().startswith(b'<svg'):
                return body
            print(f'  Not an SVG from {url}')
        except (URLError, OSError) as e:
            print(f'  Fetch error ({attempt + 1}/3) for {url}: {e}')
        time.sleep(2 * (attempt + 1))
    return None

def write_if_changed(path, data):
    """Writes the bytes only if they differ from the file's, so unchanged badges make no commit."""
    try:
        with open(path, 'rb') as f:
            if f.read() == data:
                return False
    except FileNotFoundError:
        pass
    with open(path, 'wb') as f:
        f.write(data)
    return True

def update_badge(repo, badge_type, label, message, color, logo=None, style=None, svg_label=None):
    """Writes the endpoint JSON and renders the SVG when the value changed or the SVG is missing.
    svg_label: the label shown in the SVG, if not `label` ('' hides it)."""
    data = {'schemaVersion': 1, 'label': label, 'message': message, 'color': color}
    if logo:
        data['namedLogo'] = logo
    json_path = os.path.join(BADGES_DIR, f'{repo}-{badge_type}.json')
    svg_path = os.path.join(BADGES_DIR, f'{repo}-{badge_type}.svg')

    json_bytes = (json.dumps(data, indent=2) + '\n').encode('utf-8')
    changed = write_if_changed(json_path, json_bytes)

    # The SVG as the profile shows it, and (when the profile hides the label) a labeled one too
    # for the repos' own READMEs (<repo>-<type>-label.svg)
    variants = [(svg_path, label if svg_label is None else svg_label)]
    if svg_label is not None and svg_label != label:
        variants.append((os.path.join(BADGES_DIR, f'{repo}-{badge_type}-label.svg'), label))

    for path, shown_label in variants:
        if not changed and os.path.exists(path):
            continue
        params = {'label': shown_label, 'message': message, 'color': color}
        if logo:
            params['logo'] = logo
        if style:
            params['style'] = style
        svg = fetch_svg('https://img.shields.io/static/v1?' + urlencode(params))
        if svg is not None:
            write_if_changed(path, svg)
        else:
            print(f'  Kept the old {path}')
    print(f'  {repo}-{badge_type}  →  {label}: {message}{"" if changed else "  (unchanged)"}')

def update_static_badges():
    os.makedirs(STATIC_DIR, exist_ok=True)
    for name, url in STATIC_BADGES.items():
        path = os.path.join(STATIC_DIR, name)
        if os.path.exists(path) and not FORCE_STATIC:
            continue
        svg = fetch_svg(url)
        if svg is not None:
            write_if_changed(path, svg)
            print(f'  static/{name}')
        else:
            print(f'  Could not render static/{name} (will retry next run)')

def main():
    os.makedirs(BADGES_DIR, exist_ok=True)

    print('Static badges')
    update_static_badges()

    for repo_config in REPOS:
        repo = repo_config['name']
        print(f'\n{repo}')

        # issues + stars
        repo_info = github_api(f'/repos/{OWNER}/{repo}')
        if repo_info:
            issues = repo_info.get('open_issues_count', 0)
            stars = repo_info.get('stargazers_count', 0)
            update_badge(repo, 'issues', 'issues', f'{issues} open', '222222')
            update_badge(repo, 'stars', 'Stars', str(stars), 'lightgrey', logo='github', style='social')

        if repo_config['has_releases']:
            # latest release (shown without its label)
            latest = github_api(f'/repos/{OWNER}/{repo}/releases/latest')
            if latest:
                tag = latest.get('tag_name', 'unknown')
                update_badge(repo, 'latest', 'latest', tag, '0075ca', svg_label='')

            # total downloads across ALL releases and ALL pages
            releases = github_api_all_pages(f'/repos/{OWNER}/{repo}/releases')
            if releases:
                total = sum(
                    asset['download_count']
                    for release in releases
                    for asset in release.get('assets', [])
                )
                update_badge(repo, 'downloads', 'downloads', format_downloads(total), '6f42c1')
                print(f'  Total releases fetched: {len(releases)}')

    print('\nDone.')

if __name__ == '__main__':
    main()
