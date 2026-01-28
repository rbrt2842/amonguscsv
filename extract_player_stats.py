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


def extract_player_data(html_file: Path) -> Optional[Dict[str, str]]:
    """Extract all player data from an HTML file."""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Extract basic info
        server_name = extract_server_name(html_content)
        season = extract_season(html_content)
        discord_id = extract_discord_id(html_content)
        username = extract_username(html_content)
        
        if not discord_id:
            print(f"Warning: Could not extract Discord ID from {html_file.name}")
            return None
        
        # Extract role-specific stats
        combined_stats = extract_role_stats(html_content, 'Combined')
        crew_stats = extract_role_stats(html_content, 'Crewmate')
        imp_stats = extract_role_stats(html_content, 'Impostor')
        
        # Build the data row
        data = {
            'server_name': server_name or 'Unknown',
            'season': season,
            'discord_id': discord_id,
            'username': username or 'Unknown',
            'combined_rank': combined_stats['rank'],
            'combined_mmr': combined_stats['mmr'],
            'combined_games_played_pct': combined_stats['games_played_pct'],
            'combined_wins': combined_stats['wins'],
            'combined_losses': combined_stats['losses'],
            'combined_win_pct': combined_stats['win_pct'],
            'crewmate_rank': crew_stats['rank'],
            'crewmate_mmr': crew_stats['mmr'],
            'crewmate_games_played_pct': crew_stats['games_played_pct'],
            'crewmate_wins': crew_stats['wins'],
            'crewmate_losses': crew_stats['losses'],
            'crewmate_win_pct': crew_stats['win_pct'],
            'impostor_rank': imp_stats['rank'],
            'impostor_mmr': imp_stats['mmr'],
            'impostor_games_played_pct': imp_stats['games_played_pct'],
            'impostor_wins': imp_stats['wins'],
            'impostor_losses': imp_stats['losses'],
            'impostor_win_pct': imp_stats['win_pct'],
        }
        
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
        'season',
        'discord_id',
        'username',
        'combined_rank',
        'combined_mmr',
        'combined_games_played_pct',
        'combined_wins',
        'combined_losses',
        'combined_win_pct',
        'crewmate_rank',
        'crewmate_mmr',
        'crewmate_games_played_pct',
        'crewmate_wins',
        'crewmate_losses',
        'crewmate_win_pct',
        'impostor_rank',
        'impostor_mmr',
        'impostor_games_played_pct',
        'impostor_wins',
        'impostor_losses',
        'impostor_win_pct',
    ]
    
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
        
        data = extract_player_data(html_file)
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