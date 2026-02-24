#!/usr/bin/env python3
import re
import os
import json
from urllib.request import urlopen, Request
from urllib.error import URLError

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
OWNER = 'ppkantorski'
README_PATH = 'README.md'

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


def shields_escape(text):
    """Escape text for shields.io static badge URL segment."""
    text = str(text)
    text = text.replace('-', '--')  # literal dash needs doubling
    text = text.replace('_', '__')  # literal underscore needs doubling
    text = text.replace(' ', '_')   # space → underscore
    # URL-encode + and other special chars
    text = text.replace('+', '%2B')
    return text


def format_downloads(n):
    if n >= 1_000_000:
        return f'{n / 1_000_000:.1f}M'
    elif n >= 1_000:
        return f'{n / 1_000:.1f}k'
    return str(n)


def get_latest_tag(repo):
    data = github_api(f'/repos/{OWNER}/{repo}/releases/latest')
    if not data:
        return None
    return data.get('tag_name')


def get_total_downloads(repo):
    releases = github_api(f'/repos/{OWNER}/{repo}/releases')
    if not releases:
        return 0
    return sum(
        asset['download_count']
        for release in releases
        for asset in release.get('assets', [])
    )


def get_open_issues(repo):
    data = github_api(f'/repos/{OWNER}/{repo}')
    if not data:
        return None
    return data.get('open_issues_count', 0)


def replace_badge(content, alt, label, new_value, color, link):
    """Replace a static shields.io badge value by alt text + link URL."""
    pattern = (
        r'(!\[' + re.escape(alt) + r'\]'
        r'\(https://img\.shields\.io/badge/' + re.escape(label) + r'-)'
        r'[^-][^)]*?'
        r'(-' + re.escape(color) + r'\))'
        r'(\(' + re.escape(link) + r'\))'
    )
    replacement = r'\g<1>' + shields_escape(new_value) + r'\g<2>\g<3>'
    new_content, count = re.subn(pattern, replacement, content)
    if count == 0:
        print(f'  WARNING: no match for [{alt}] link={link}')
    else:
        print(f'  Updated [{alt}] → {new_value}')
    return new_content


def main():
    with open(README_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    for repo_config in REPOS:
        repo = repo_config['name']
        print(f'\nProcessing {repo}...')

        # issues
        issues = get_open_issues(repo)
        if issues is not None:
            content = replace_badge(
                content, 'issues', 'issues',
                f'{issues} open', '222222',
                f'https://github.com/{OWNER}/{repo}/issues'
            )

        if repo_config['has_releases']:
            # latest release tag
            tag = get_latest_tag(repo)
            if tag:
                content = replace_badge(
                    content, 'latest', 'latest',
                    tag, 'blue',
                    f'https://github.com/{OWNER}/{repo}/releases/latest'
                )

            # total downloads
            downloads = get_total_downloads(repo)
            content = replace_badge(
                content, 'downloads', 'downloads',
                format_downloads(downloads), '6f42c1',
                f'https://somsubhra.github.io/github-release-stats/?username={OWNER}&repository={repo}'
            )

    if content != original:
        with open(README_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print('\nREADME.md updated successfully.')
    else:
        print('\nNo changes needed.')


if __name__ == '__main__':
    main()
