#!/usr/bin/env python3
import os
import json
from urllib.request import urlopen, Request
from urllib.error import URLError

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
OWNER = 'ppkantorski'
BADGES_DIR = '.github/badges'

REPOS = [
    {'name': 'Ultrahand-Overlay',     'has_releases': True},
    {'name': 'libultrahand',           'has_releases': True},
    {'name': 'nx-ovlloader',           'has_releases': True},
    {'name': 'Ultrahand-Packages',     'has_releases': False},
    {'name': 'Tetris-Overlay',         'has_releases': True},
    {'name': 'ovl-sysmodules',         'has_releases': True},
    {'name': 'Status-Monitor-Overlay', 'has_releases': True},
    {'name': 'FPSLocker',              'has_releases': True},
    {'name': 'sys-clk',                'has_releases': True},
    {'name': 'Fizeau',                 'has_releases': True},
    {'name': 'QuickNTP',               'has_releases': True},
    {'name': 'Alchemist',              'has_releases': True},
    {'name': 'Memory-Kit',             'has_releases': True},
]

def github_api(endpoint):
    url = f'https://api.github.com{endpoint}'
    req = Request(url)
    if GITHUB_TOKEN:
        req.add_header('Authorization', f'token {GITHUB_TOKEN}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except URLError as e:
        print(f'  API error for {endpoint}: {e}')
        return None

def github_api_all_pages(endpoint):
    """Fetch all pages of a paginated GitHub API endpoint."""
    results = []
    page = 1
    while True:
        sep = '&' if '?' in endpoint else '?'
        data = github_api(f'{endpoint}{sep}per_page=100&page={page}')
        if not data:
            break
        results.extend(data)
        if len(data) < 100:
            break
        page += 1
    return results

def format_downloads(n):
    if n >= 1_000_000:
        return f'{n / 1_000_000:.1f}M'
    elif n >= 1_000:
        return f'{n / 1_000:.1f}k'
    return str(n)

def write_badge(repo, badge_type, label, message, color):
    """Write a shields.io endpoint-compatible JSON file."""
    path = os.path.join(BADGES_DIR, f'{repo}-{badge_type}.json')
    data = {
        'schemaVersion': 1,
        'label': label,
        'message': message,
        'color': color
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f'  Wrote {path}  →  {label}: {message}')

def main():
    os.makedirs(BADGES_DIR, exist_ok=True)

    for repo_config in REPOS:
        repo = repo_config['name']
        print(f'\n{repo}')

        # issues
        repo_info = github_api(f'/repos/{OWNER}/{repo}')
        if repo_info:
            issues = repo_info.get('open_issues_count', 0)
            write_badge(repo, 'issues', 'issues', f'{issues} open', '222222')

        if repo_config['has_releases']:
            # latest release
            latest = github_api(f'/repos/{OWNER}/{repo}/releases/latest')
            if latest:
                tag = latest.get('tag_name', 'unknown')
                write_badge(repo, 'latest', 'latest', tag, '0075ca')

            # total downloads across ALL releases and ALL pages
            releases = github_api_all_pages(f'/repos/{OWNER}/{repo}/releases')
            if releases:
                total = sum(
                    asset['download_count']
                    for release in releases
                    for asset in release.get('assets', [])
                )
                write_badge(repo, 'downloads', 'downloads', format_downloads(total), '6f42c1')
                print(f'  Total releases fetched: {len(releases)}')

    print('\nDone.')

if __name__ == '__main__':
    main()
