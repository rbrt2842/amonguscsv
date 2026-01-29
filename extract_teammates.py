#!/usr/bin/env python3
"""
Extract top 10 common teammates from Among Us leaderboard HTML files.
Creates common_teammates.csv with teammate relationships.
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


def extract_teammates(html_content: str) -> List[Dict[str, str]]:
    """Extract top 10 common teammates data."""
    teammates = []
    
    # Find the "Top 10 Common Teammates" section
    teammates_section = re.search(
        r'Top 10 Common Teammates.*?<table.*?>(.*?)</table>',
        html_content,
        re.DOTALL | re.IGNORECASE
    )
    
    if not teammates_section:
        return teammates
    
    table_content = teammates_section.group(1)
    
    # Find all teammate rows
    # Pattern: <tr class="clickable-row" data-href="./?tournament=Season 1&id=DISCORD_ID">
    #   <th>RANK</th>
    #   <td><img .../> USERNAME</td>
    #   <td>MMR</td>
    #   <td>MATCHES [%]</td>
    
    row_pattern = r'<tr[^>]*data-href="[^"]*id=(\d+)"[^>]*>.*?<th[^>]*>\s*(\d+)\s*</th>.*?<img[^>]*/>([^<]+)</td>.*?<td[^>]*>\s*(\d+)\s*</td>.*?<td[^>]*>\s*(\d+)\s*\[(\d+)%\]\s*</td>'
    
    matches = re.finditer(row_pattern, table_content, re.DOTALL)
    
    for match in matches:
        teammate = {
            'teammate_discord_id': match.group(1),
            'teammate_rank': match.group(2),
            'teammate_username': match.group(3).strip(),
            'teammate_mmr': match.group(4),
            'matches_together_count': match.group(5),
            'matches_together_pct': match.group(6)
        }
        teammates.append(teammate)
    
    return teammates


def extract_all_teammate_data(html_file: Path) -> List[Dict[str, str]]:
    """Extract teammate data from an HTML file, returning one row per teammate."""
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
        
        # Extract teammates
        teammates = extract_teammates(html_content)
        
        # Build data rows - one per teammate
        rows = []
        for teammate in teammates:
            row = {
                'server_name': server_name or 'Unknown',
                'season': season,
                'player_discord_id': discord_id,
                'player_username': username or 'Unknown',
            }
            row.update(teammate)
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
        'teammate_rank',
        'teammate_discord_id',
        'teammate_username',
        'teammate_mmr',
        'matches_together_count',
        'matches_together_pct',
    ]
    
    # Process files and write to CSV
    all_data = []
    successful_files = 0
    total_teammates = 0
    failed = 0
    
    start_time = time.time()
    batch_start = start_time
    
    for i, html_file in enumerate(html_files, 1):
        if i % 100 == 0:
            batch_time = time.time() - batch_start
            elapsed = time.time() - start_time
            print(f"Processing file {i}/{len(html_files)}... (last 100 took {batch_time:.1f}s, total elapsed: {elapsed/60:.1f}m, {total_teammates} teammate relationships found)")
            batch_start = time.time()
        
        rows = extract_all_teammate_data(html_file)
        if rows:
            all_data.extend(rows)
            successful_files += 1
            total_teammates += len(rows)
        elif rows is not None and len(rows) == 0:
            # Successfully processed but no teammates found
            successful_files += 1
        else:
            failed += 1
    
    # Write to CSV
    print(f"\nWriting {len(all_data)} teammate relationships to {output_csv}...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)
    
    total_time = time.time() - start_time
    print(f"\n✓ Complete!")
    print(f"  Successfully processed: {successful_files} files")
    print(f"  Total teammate relationships: {total_teammates}")
    print(f"  Failed: {failed} files")
    print(f"  Total time: {total_time/60:.1f} minutes ({total_time:.1f} seconds)")
    print(f"  Output: {output_csv}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python extract_teammates.py <input_directory> [output_csv]")
        print("\nExample:")
        print("  python extract_teammates.py /mnt/c/Users/rober/Downloads/aznbot common_teammates.csv")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    output_csv = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('common_teammates.csv')
    
    if not input_dir.exists():
        print(f"Error: Directory {input_dir} does not exist")
        sys.exit(1)
    
    process_html_files(input_dir, output_csv)


if __name__ == '__main__':
    main()
