#!/usr/bin/env python3
"""
Extract recent 10 match results from Among Us leaderboard HTML files.
Creates match_history.csv with individual match data.
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
        season_num_match = re.search(r'Season\s+(\d+)', season_str, re.IGNORECASE)
        if season_num_match:
            return season_num_match.group(1)
        else:
            return "0"
    return "0"


def extract_discord_id(html_content: str) -> Optional[str]:
    """Extract player's Discord ID from avatar URL."""
    match = re.search(r'cdn\.discordapp\.com/avatars/(\d+)/', html_content)
    if match:
        return match.group(1)
    return None


def extract_username(html_content: str) -> Optional[str]:
    """Extract player username from the header section."""
    match = re.search(r'class="avatar avatarTop"[^>]*>.*?<h1[^>]*>\s*([^<]+?)\s*</h1>', html_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def extract_map_from_image(img_src: str) -> str:
    """Extract map name from image source."""
    if 'polus' in img_src.lower():
        return 'Polus'
    elif 'mira' in img_src.lower():
        return 'MIRA HQ'
    elif 'skeld' in img_src.lower():
        return 'The Skeld'
    elif 'airship' in img_src.lower():
        return 'Airship'
    return 'Unknown'


def extract_role_from_image(img_src: str) -> str:
    """Extract role from image source."""
    if 'Crew' in img_src or 'crew' in img_src:
        return 'Crewmate'
    elif 'Impostor' in img_src or 'impostor' in img_src:
        return 'Impostor'
    return 'Unknown'


def extract_match_history(html_content: str) -> List[Dict[str, str]]:
    """Extract recent 10 match results from the archiveResults table."""
    matches = []
    
    # Find the "Recent 10 Results" table
    table_match = re.search(
        r'Recent 10 Results.*?<table[^>]*class="archiveResults[^"]*"[^>]*>(.*?)</table>',
        html_content,
        re.DOTALL | re.IGNORECASE
    )
    
    if not table_match:
        return matches
    
    table_content = table_match.group(1)
    
    # Find all match rows
    # Pattern for each row:
    # <tr>
    #   <th>MATCH_ID</th>
    #   <td><img src="...polus.png"/></td>
    #   <td><img src="...steam_AboutCrew_v2.png"/></td>
    #   <td>WIN_PCT%</td>
    #   <td><span ...>Won/Loss</span></td>
    #   <td>+/-MMR (optional: % of total)</td>
    # </tr>
    
    row_pattern = r'<tr>\s*<th[^>]*>\s*(\d+)\s*</th>\s*<td[^>]*>\s*<img[^>]*src="([^"]+)"[^>]*>\s*</td>\s*<td[^>]*>\s*<img[^>]*src="([^"]+)"[^>]*>\s*</td>\s*<td[^>]*>\s*([\d.]+)%\s*</td>\s*<td[^>]*>\s*<span[^>]*>\s*(Won|Loss)\s*</span>\s*</td>\s*<td[^>]*>\s*[+]?([-]?[\d.]+)(.*?)</td>'
    
    row_matches = re.finditer(row_pattern, table_content, re.DOTALL)
    
    for match in row_matches:
        match_id = match.group(1)
        map_img = match.group(2)
        role_img = match.group(3)
        win_pct = match.group(4)
        result = match.group(5)
        mmr_change = match.group(6)
        mmr_extra = match.group(7)
        
        # Extract % of total if present
        pct_of_total = None
        pct_match = re.search(r'([\d.]+)%\s*of\s*total', mmr_extra)
        if pct_match:
            pct_of_total = pct_match.group(1)
        
        match_data = {
            'match_id': match_id,
            'map': extract_map_from_image(map_img),
            'role': extract_role_from_image(role_img),
            'win_probability_pct': win_pct,
            'result': result,
            'mmr_change': mmr_change,
            'mmr_pct_of_total': pct_of_total
        }
        
        matches.append(match_data)
    
    return matches


def extract_all_match_data(html_file: Path) -> List[Dict[str, str]]:
    """Extract match history from an HTML file, returning one row per match."""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Extract basic player info
        server_name = extract_server_name(html_content)
        season = extract_season(html_content)
        discord_id = extract_discord_id(html_content)
        username = extract_username(html_content)
        
        if not discord_id:
            print(f"Warning: Could not extract Discord ID from {html_file.name}")
            return []
        
        # Extract matches
        matches = extract_match_history(html_content)
        
        # Build data rows - one per match
        rows = []
        for match in matches:
            row = {
                'server_name': server_name or 'Unknown',
                'season': season,
                'player_discord_id': discord_id,
                'player_username': username or 'Unknown',
            }
            row.update(match)
            rows.append(row)
        
        return rows
        
    except Exception as e:
        print(f"Error processing {html_file.name}: {e}")
        return []


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
        'player_discord_id',
        'player_username',
        'match_id',
        'map',
        'role',
        'win_probability_pct',
        'result',
        'mmr_change',
        'mmr_pct_of_total',
    ]
    
    # Process files and write to CSV
    all_data = []
    successful_files = 0
    total_matches = 0
    failed = 0
    
    start_time = time.time()
    batch_start = start_time
    
    for i, html_file in enumerate(html_files, 1):
        if i % 100 == 0:
            batch_time = time.time() - batch_start
            elapsed = time.time() - start_time
            print(f"Processing file {i}/{len(html_files)}... (last 100 took {batch_time:.1f}s, total elapsed: {elapsed/60:.1f}m, {total_matches} matches found)")
            batch_start = time.time()
        
        rows = extract_all_match_data(html_file)
        if rows:
            all_data.extend(rows)
            successful_files += 1
            total_matches += len(rows)
        elif rows is not None and len(rows) == 0:
            # Successfully processed but no matches found
            successful_files += 1
        else:
            failed += 1
    
    # Write to CSV
    print(f"\nWriting {len(all_data)} match records to {output_csv}...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)
    
    total_time = time.time() - start_time
    print(f"\n✓ Complete!")
    print(f"  Successfully processed: {successful_files} files")
    print(f"  Total match records: {total_matches}")
    print(f"  Average matches per player: {total_matches/successful_files:.1f}")
    print(f"  Failed: {failed} files")
    print(f"  Total time: {total_time/60:.1f} minutes ({total_time:.1f} seconds)")
    print(f"  Output: {output_csv}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python extract_match_history.py <input_directory> [output_csv]")
        print("\nExample:")
        print("  python extract_match_history.py /mnt/c/Users/rober/Downloads/aznbot match_history.csv")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    output_csv = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('match_history.csv')
    
    if not input_dir.exists():
        print(f"Error: Directory {input_dir} does not exist")
        sys.exit(1)
    
    process_html_files(input_dir, output_csv)


if __name__ == '__main__':
    main()
