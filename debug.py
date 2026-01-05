import pandas as pd
from bs4 import BeautifulSoup
import os
import glob

print("Script starting...")

# Define the columns you want in the CSV
columns = [
    "Player Name", "Server", "Crew Rank", "Crew MMR", "Crew Played", "Crew Won", "Crew Lost", "Crew Win %",
    "Imp Rank", "Imp MMR", "Imp Played", "Imp Won", "Imp Lost", "Imp Win %",
    "Overall Rank", "Overall MMR", "Overall Played", "Overall Won", "Overall Lost", "Overall Win %"
]

data_rows = []

# Find all HTML files in current directory
html_files = glob.glob("*.html")
print(f"Found {len(html_files)} HTML files: {html_files}")

if not html_files:
    print("No HTML files found in current directory!")
    print("Current directory:", os.getcwd())
    exit(1)

# Loop through each HTML file
for file_name in html_files:
    print(f"\nProcessing {file_name}...")
    
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Extract player name
        h1_tag = soup.find("h1")
        player_name = h1_tag.text.strip() if h1_tag else "Unknown"
        print(f"  Player: {player_name}")

        # Extract server from title
        title_tag = soup.find("title")
        title_text = title_tag.text.strip() if title_tag else "Unknown"
        server = title_text.split("-")[0].strip() if "-" in title_text else "Unknown"
        print(f"  Server: {server}")

        # Find the main stats table
        table = soup.find("table", class_="matchResults")
        if not table:
            print(f"  WARNING: No stats table found in {file_name}")
            continue

        rows = table.find_all("tr")[1:]  # Skip header row
        print(f"  Found {len(rows)} stat rows")

        # Initialize stats
        crew_stats = {}
        imp_stats = {}
        overall_stats = {}

        for row in rows:
            cols = row.find_all(["th", "td"])
            if len(cols) < 7:
                continue
            
            # Check what role this row represents
            role_cell = cols[0]
            role_text = role_cell.text.strip().lower()
            
            # Look for images or text to identify role
            crew_img = role_cell.find("img", src="/images/AmongUs/steam_AboutCrew_v2.png")
            imp_img = role_cell.find("img", src="/images/AmongUs/steam_AboutImpostor_v2.png")
            
            if crew_img or "crew" in role_text:
                crew_stats = {
                    "rank": cols[1].text.strip(),
                    "mmr": cols[2].text.strip(),
                    "played": cols[3].text.strip(),
                    "won": cols[4].text.strip(),
                    "lost": cols[5].text.strip(),
                    "win_pct": cols[6].text.strip()
                }
                print(f"  Found Crew stats")
                
            elif imp_img or "impostor" in role_text:
                imp_stats = {
                    "rank": cols[1].text.strip(),
                    "mmr": cols[2].text.strip(),
                    "played": cols[3].text.strip(),
                    "won": cols[4].text.strip(),
                    "lost": cols[5].text.strip(),
                    "win_pct": cols[6].text.strip()
                }
                print(f"  Found Impostor stats")
                
            elif "overall" in role_text:
                overall_stats = {
                    "rank": cols[1].text.strip(),
                    "mmr": cols[2].text.strip(),
                    "played": cols[3].text.strip(),
                    "won": cols[4].text.strip(),
                    "lost": cols[5].text.strip(),
                    "win_pct": cols[6].text.strip()
                }
                print(f"  Found Overall stats")

        # Build row for CSV
        row_data = [
            player_name,
            server,
            crew_stats.get("rank", "N/A"),
            crew_stats.get("mmr", "N/A"),
            crew_stats.get("played", "N/A"),
            crew_stats.get("won", "N/A"),
            crew_stats.get("lost", "N/A"),
            crew_stats.get("win_pct", "N/A"),
            imp_stats.get("rank", "N/A"),
            imp_stats.get("mmr", "N/A"),
            imp_stats.get("played", "N/A"),
            imp_stats.get("won", "N/A"),
            imp_stats.get("lost", "N/A"),
            imp_stats.get("win_pct", "N/A"),
            overall_stats.get("rank", "N/A"),
            overall_stats.get("mmr", "N/A"),
            overall_stats.get("played", "N/A"),
            overall_stats.get("won", "N/A"),
            overall_stats.get("lost", "N/A"),
            overall_stats.get("win_pct", "N/A")
        ]

        data_rows.append(row_data)
        print(f"  Successfully processed {player_name}")
        
    except Exception as e:
        print(f"  ERROR processing {file_name}: {e}")

# Create DataFrame and save to CSV
if data_rows:
    df = pd.DataFrame(data_rows, columns=columns)
    df.to_csv("players_stats.csv", index=False)
    print(f"\nSuccessfully created CSV with {len(data_rows)} players")
    print("File saved as: players_stats.csv")
else:
    print("\nNo data was processed. CSV not created.")

print("\nScript finished!")