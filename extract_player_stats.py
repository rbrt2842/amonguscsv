#!/usr/bin/env python3
"""
Extract main player stats from Among Us leaderboard HTML files.
Creates player_main_stats.csv with composite key: {discord_id, server_name, season}
"""

import re
import csv
from pathlib import Path
from typing import Dict, Optional, List
import sys
import time
from html.parser import HTMLParser
from html import unescape
from urllib.parse import parse_qs, urlparse


class PageParser(HTMLParser):
    """Collect page elements and table cells without depending on whitespace/attribute order."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.in_title = False
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.avatar_url = None
        self.username = None
        self.in_h1 = False
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title':
            self.in_title = True
        elif tag == 'h1':
            self.in_h1 = True
        elif tag == 'img':
            classes = attrs.get('class', '').split()
            src = attrs.get('src', '')
            if 'avatarTop' in classes:
                self.avatar_url = src
            if self.cell is not None:
                self.cell['images'].append(src)
        elif tag == 'table':
            self.table = {'attrs': attrs, 'rows': []}
        elif tag == 'tr' and self.table is not None:
            self.row = {'attrs': attrs, 'cells': []}
        elif tag in ('th', 'td') and self.row is not None:
            self.cell = {'tag': tag, 'attrs': attrs, 'text': '', 'images': []}
        if tag == 'tr' and attrs.get('data-href'):
            self.links.append(attrs['data-href'])

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        elif tag == 'h1':
            self.in_h1 = False
        elif tag in ('th', 'td') and self.cell is not None:
            self.row['cells'].append(self.cell)
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.table['rows'].append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_h1:
            self.username = (self.username or '') + data
        if self.cell is not None:
            self.cell['text'] += data


def parse_page(html_content: str):
    parser = PageParser()
    parser.feed(html_content)
    title_match = re.match(r'\s*(.*?)\s*-\s*Ranked Among Us Leaderboards\s*$', parser.title, re.I)
    server = title_match.group(1).strip() if title_match else None
    tournament = None
    discord_id = None
    for href in parser.links:
        query = parse_qs(urlparse(unescape(href)).query)
        if tournament is None and query.get('tournament'):
            tournament = query['tournament'][0]
    if parser.avatar_url:
        path = urlparse(parser.avatar_url).path
        match = re.search(r'/avatars/(\d+)/', path)
        if match:
            discord_id = match.group(1)
    if not discord_id:
        for href in parser.links:
            query = parse_qs(urlparse(unescape(href)).query)
            if query.get('id') and query['id'][0].isdigit():
                discord_id = query['id'][0]
                break
    if not discord_id:
        # Some exports have no avatar; the selected profile id remains in its own page URL.
        match = re.search(r'(?:\?|&)id=(\d+)', html_content)
        if match:
            discord_id = match.group(1)
    season_match = re.search(r'Season\s+(\d+)', tournament or '', re.I)
    season = season_match.group(1) if season_match else '0'
    stats_table = next((t for t in parser.tables if 'matchResults' in t['attrs'].get('class', '').split()), None)
    role_stats = {'combined': {}, 'crewmate': {}, 'impostor': {}}
    if stats_table:
        for row in stats_table['rows']:
            if len(row['cells']) < 7:
                continue
            head = row['cells'][0]
            first_image = head['images'][0] if head['images'] else ''
            style = head['attrs'].get('style', '').lower()
            role = 'combined' if 'overall' in head['text'].lower() or 'color: white' in style else (
                'crewmate' if 'crew' in first_image.lower() or 'royalblue' in style else
                'impostor' if 'impostor' in first_image.lower() or 'color: red' in style else None)
            if not role:
                continue
            cells = row['cells']
            values = [re.sub(r'\s+', ' ', c['text']).strip() for c in cells]
            role_stats[role] = {
                'rank': values[1], 'mmr': values[2].split()[0], 'played_pct': values[3].rstrip('%'),
                'wins': values[4].split()[0] if values[4] else '',
                'losses': values[5].split()[0] if values[5] else '',
                'win_pct': values[6].rstrip('%'),
            }
            for ix, key in ((4, 'win'), (5, 'loss')):
                text = values[ix]
                streak = re.search(r'(?:Win|Lose) Streak\s*:\s*(\d+)', text, re.I)
                best = re.search(r'(?:Best|Worst) Streak\s*:\s*(\d+)', text, re.I)
                role_stats[role][key + '_streak'] = streak.group(1) if streak else ''
                role_stats[role][key + '_record_streak'] = best.group(1) if best else ''
    return server, tournament, season, discord_id, (parser.username or '').strip(), parser.avatar_url, role_stats


def extract_server_name(html_content: str) -> Optional[str]:
    """Extract server name from the HTML title."""
    match = re.search(r'<title>\s*(.+?)\s*-\s*Ranked Among Us Leaderboards\s*</title>', html_content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def extract_season(html_content: str) -> str:
    """Extract season/tournament from data-href attributes."""
    match = re.search(r'data-href="[^"]*tournament=([^"&]+)', html_content)
    if match:
        season_str = match.group(1).strip()
        # Try to extract number from "Season X" format
        season_num_match = re.search(r'Season\s+(\d+)', season_str, re.IGNORECASE)
        if season_num_match:
            return season_num_match.group(1)
        else:
            return "0"  # No season number found
    return "0"


def extract_discord_id(html_content: str) -> Optional[str]:
    """Extract player's Discord ID from avatar URL or data-href."""
    # Try from avatar URL first
    match = re.search(r'cdn\.discordapp\.com/avatars/(\d+)/', html_content)
    if match:
        return match.group(1)
    
    # Try from data-href as backup
    match = re.search(r'data-href="[^"]*id=(\d+)', html_content)
    if match:
        return match.group(1)
    
    return None


def extract_username(html_content: str) -> Optional[str]:
    """Extract player username from the header section."""
    # Look for the username in the h1 tag that comes after the avatar
    # The h1 has specific styling attributes and the username is inside
    match = re.search(r'class="avatar avatarTop"[^>]*>.*?<h1[^>]*>\s*([^<]+?)\s*</h1>', html_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def extract_role_stats(html_content: str, role: str) -> Dict[str, Optional[str]]:
    """
    Extract stats for a specific role (Crewmate, Impostor, or Combined).
    
    Returns dict with keys: rank, mmr, games_played_pct, wins, losses, win_pct
    """
    stats = {
        'rank': None,
        'mmr': None,
        'games_played_pct': None,
        'wins': None,
        'losses': None,
        'win_pct': None
    }
    
    if role == 'Crewmate':
        # Look for the crewmate row (blue/royalblue)
        pattern = r'<tr>\s*<th[^>]*color:\s*royalblue[^>]*>.*?steam_AboutCrew.*?</th>\s*<td[^>]*>\s*(\d+)\s*</td>\s*<td[^>]*>\s*(\d+).*?</td>\s*<td[^>]*>\s*(\d+)%\s*</td>\s*<td[^>]*>\s*(\d+).*?</td>\s*<td[^>]*>\s*(\d+).*?</td>\s*<td[^>]*>\s*(\d+)%\s*</td>'
    elif role == 'Impostor':
        # Look for the impostor row (red)
        pattern = r'<th[^>]*color:\s*red[^>]*>.*?steam_AboutImpostor.*?</th>\s*<td[^>]*>\s*(\d+)\s*</td>\s*<td[^>]*>\s*(\d+).*?</td>\s*<td[^>]*>\s*(\d+)%\s*</td>\s*<td[^>]*>\s*(\d+).*?</td>\s*<td[^>]*>\s*(\d+).*?</td>\s*<td[^>]*>\s*(\d+)%\s*</td>'
    elif role == 'Combined':
        # Look for the combined row (white/blueviolet)
        pattern = r'<th[^>]*color:\s*white[^>]*>.*?</th>\s*<td[^>]*>\s*(\d+)\s*</td>\s*<td[^>]*>\s*(\d+).*?</td>\s*<td[^>]*>\s*(\d+)%\s*</td>\s*<td[^>]*>\s*(\d+).*?</td>\s*<td[^>]*>\s*(\d+).*?</td>\s*<td[^>]*>\s*(\d+)%\s*</td>'
    else:
        return stats
    
    match = re.search(pattern, html_content, re.DOTALL)
    if match:
        stats['rank'] = match.group(1)
        stats['mmr'] = match.group(2)
        stats['games_played_pct'] = match.group(3)
        stats['wins'] = match.group(4)
        stats['losses'] = match.group(5)
        stats['win_pct'] = match.group(6)
    
    return stats


def extract_player_data(html_file: Path, input_dir: Path) -> Optional[Dict[str, str]]:
    """Extract all player data from an HTML file."""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        server_name, tournament, season, discord_id, username, _avatar_url, stats = parse_page(html_content)
        if not discord_id:
            filename_match = re.search(r'(\d{17,20})(?=\.html$)', html_file.name, re.I)
            if filename_match:
                discord_id = filename_match.group(1)
        
        if not discord_id:
            print(f"Warning: Could not extract Discord ID from {html_file.name}")
            return None
        
        data = {
            'server_name': server_name or 'Unknown',
            'tournament': tournament or '',
            'season': season,
            'discord_id': discord_id,
            'username': username or 'Unknown',
            'player_key': f"{server_name or 'Unknown'}|{season}|{discord_id}",
            'source_file': str(html_file.relative_to(input_dir)),
        }
        for role in ('combined', 'crewmate', 'impostor'):
            role_values = stats[role]
            for output_key, source_key in (
                ('rank', 'rank'), ('mmr', 'mmr'), ('played_pct', 'played_pct'),
                ('wins', 'wins'), ('losses', 'losses'), ('win_pct', 'win_pct'),
                ('win_streak', 'win_streak'), ('win_streak_record', 'win_record_streak'),
                ('loss_streak', 'loss_streak'), ('loss_streak_record', 'loss_record_streak')):
                data[f'{role}_{output_key}'] = role_values.get(source_key, '')
            wins, losses = role_values.get('wins', ''), role_values.get('losses', '')
            data[f'{role}_games'] = str(int(wins) + int(losses)) if wins.isdigit() and losses.isdigit() else ''
        return data
        
    except Exception as e:
        print(f"Error processing {html_file.name}: {e}")
        return None


def process_html_files(input_dir: Path, output_csv: Path):
    """Process all HTML files in the input directory and create CSV."""
    
    # Get all HTML files recursively from all subdirectories
    html_files = list(input_dir.glob('**/*.html'))
    
    if not html_files:
        print(f"No HTML files found in {input_dir}")
        return
    
    print(f"Found {len(html_files)} HTML files to process...")
    
    # CSV column headers
    fieldnames = [
        'server_name',
        'tournament',
        'season',
        'discord_id',
        'username',
        'player_key',
        'source_file',
    ]
    for role in ('combined', 'crewmate', 'impostor'):
        fieldnames.extend(f'{role}_{key}' for key in ('rank', 'mmr', 'played_pct', 'wins', 'losses', 'games', 'win_pct', 'win_streak', 'win_streak_record', 'loss_streak', 'loss_streak_record'))
    
    # Process files and write to CSV
    all_data = []
    successful = 0
    failed = 0
    
    start_time = time.time()
    batch_start = start_time
    
    for i, html_file in enumerate(html_files, 1):
        if i % 100 == 0:
            batch_time = time.time() - batch_start
            elapsed = time.time() - start_time
            print(f"Processing file {i}/{len(html_files)}... (last 100 took {batch_time:.1f}s, total elapsed: {elapsed/60:.1f}m)")
            batch_start = time.time()
        
        data = extract_player_data(html_file, input_dir)
        if data:
            all_data.append(data)
            successful += 1
        else:
            failed += 1
    
    # Write to CSV
    print(f"\nWriting {len(all_data)} records to {output_csv}...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)
    
    total_time = time.time() - start_time
    print(f"\n✓ Complete!")
    print(f"  Successfully processed: {successful} files")
    print(f"  Failed: {failed} files")
    print(f"  Total time: {total_time/60:.1f} minutes ({total_time:.1f} seconds)")
    print(f"  Output: {output_csv}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python extract_player_stats.py <input_directory> [output_csv]")
        print("\nExample:")
        print("  python extract_player_stats.py /mnt/user-data/uploads player_main_stats.csv")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    output_csv = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('player_main_stats.csv')
    
    if not input_dir.exists():
        print(f"Error: Directory {input_dir} does not exist")
        sys.exit(1)
    
    process_html_files(input_dir, output_csv)


if __name__ == '__main__':
    main()
