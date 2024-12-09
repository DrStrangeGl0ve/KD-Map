import sys
import requests
import time
import json
import tabulate
from config import Config
from PIL import Image
import matplotlib.pyplot as plt


API_KEY = Config.API_KEY

gameName = sys.argv[1]
tagName = sys.argv[2]
matchCount = sys.argv[3]

# IMPORTANT: Before you run this script, be sure to look at the README for instructions on how to store your API key for it to function properly.



# The URLS for the North America region of the Riot Games API. You can change these to match your region if you're not in NA.
PLAYER_URL = "https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/"
MATCHES_URL = 'https://americas.api.riotgames.com/lol/match/v5/matches/'



# Initialize API call counter
api_call_count = 0

# Function to make a request to the Riot Games API, handle rate limits, and return the JSON response
def make_request(url, headers):
    global api_call_count
    max_retries = 5
    retry_delay = 1  # Initial delay in seconds

    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        api_call_count += 1

        if response.status_code == 200:
            # Extract rate limit headers
            app_rate_limit = response.headers.get("X-App-Rate-Limit", "")
            app_rate_limit_count = response.headers.get("X-App-Rate-Limit-Count", "")
            method_rate_limit = response.headers.get("X-Method-Rate-Limit", "")
            method_rate_limit_count = response.headers.get("X-Method-Rate-Limit-Count", "")

            # Calculate remaining API calls
            app_limits = [int(limit.split(":")[0]) for limit in app_rate_limit.split(",")]
            app_counts = [int(count.split(":")[0]) for count in app_rate_limit_count.split(",")]
            method_limits = [int(limit.split(":")[0]) for limit in method_rate_limit.split(",")]
            method_counts = [int(count.split(":")[0]) for count in method_rate_limit_count.split(",")]

            app_remaining = [limit - count for limit, count in zip(app_limits, app_counts)]
            method_remaining = [limit - count for limit, count in zip(method_limits, method_counts)]

            print(f"App Rate Limit Remaining: {app_remaining}")
            print(f"Method Rate Limit Remaining: {method_remaining}")

            return response.json()
        elif response.status_code == 429:  # Rate limit exceeded
            print("Rate limit exceeded. Retrying...")
            retry_after = int(response.headers.get("Retry-After", retry_delay))
            time.sleep(retry_after)
            retry_delay *= 2  # Exponential backoff
        elif response.status_code == 403:
            print("Error 403: Forbidden. Check your API key and permissions.")
            return None
        else:
            print(f"Error: {response.status_code}")
            print(response.json())
            return None

    print("Max retries exceeded.")
    return None

# This retrieves the player data from Riot using the user's Riot ID and Tag Line (without hashtag)
def get_player_data(gameName, tagName):
    url = f"{PLAYER_URL}{gameName}/{tagName}?api_key={API_KEY}"
    headers = {
        "X-Riot-Token": API_KEY
    }
    return make_request(url, headers)

# This saves the PUUID to a file for future use. I've added this to my .gitignore file out of an abundance of caution, but I'm pretty sure that PUUIDs are safe and app-specific.
def save_puuid_to_file(puuid, filename='puuid_data.txt'):
    with open(filename, 'w') as file:
        file.write(puuid)
    print(f"PUUID saved to {filename}")

# This uses the PUUID to get the specified number of match IDs for the player. The default is 20, but you can use up to 100. The match IDs are used to get the match details.
# WARNING: This can use A LOT of API calls, so be careful with this one.
def get_match_id(puuid, count):
    url = f"{MATCHES_URL}by-puuid/{puuid}/ids?queue=0&start=0&count={count}"
    headers = {
        "X-Riot-Token": API_KEY
    }
    return make_request(url, headers)

# This gets the match details for a specific match ID. It's used to get the participants and other information about the match.
def get_match_details(match_id):
    url = f"{MATCHES_URL}{match_id}?api_key={API_KEY}"
    headers = {
        "X-Riot-Token": API_KEY
    }
    return make_request(url, headers)

# This gets the timeline for a specific match ID. It's used to get the events that happen during the match. This is where we'll find the champion kill events.
def get_match_timeline(match_id):
    url = f"{MATCHES_URL}{match_id}/timeline?api_key={API_KEY}"
    headers = {
        "X-Riot-Token": API_KEY
    }
    return make_request(url, headers)

# Locates the champion kill events for a specific participant in the match timeline.

def save_champion_kill_events(timeline, participant_id, participant_game_name):
    data_to_save = []
    champion_kill_events = []
    for frame in timeline['info']['frames']:
        for event in frame['events']:
            if event['type'] == 'CHAMPION_KILL':
                # Only include the events where the player is the killer or victim, assists aren't included, but could be added easily.
                if event['killerId'] == participant_id or event['victimId'] == participant_id:
                    champion_kill_events.append(event)
    
    # Marks the position of the player and their opponent at the time of the event.
    for event in champion_kill_events:
        # Convert milliseconds to seconds
        game_time = event['timestamp'] // 1000
        killer_position = event['position']
        victim_position = event['position']
        killer_name = participant_game_name if event['killerId'] == participant_id else next(p['championName'] for p in participants if p['participantId'] == event['killerId'])
        victim_name = participant_game_name if event['victimId'] == participant_id else next(p['championName'] for p in participants if p['participantId'] == event['victimId'])
        # Adds the data to the list to be saved to the JSON file.
        data_to_save.append({
            "game_time": f"{game_time}s",
            "killer_name": killer_name,
            "victim_name": victim_name,
            "killer_position": {"x": killer_position.get('x', 'N/A'), "y": killer_position.get('y', 'N/A')},
            "victim_position": {"x": victim_position.get('x', 'N/A'), "y": victim_position.get('y', 'N/A')},
            "player_name": participant_game_name
        })
    return data_to_save

# Function to scale the coordinates from the original range to a new range
def scale_coordinates(x, y, original_max=32000, new_max=240):
    scale_factor = new_max / original_max
    return x * scale_factor, y * scale_factor

# Function to convert the timestamp from seconds to minutes:seconds format
def convert_timestamp_to_minutes_seconds(timestamp):
    timestamp = int(timestamp.rstrip('s'))
    minutes = timestamp // 60
    seconds = timestamp % 60
    return f"{minutes}:{seconds:02d}"

# Get the player data using the game name and tag name.
playerData = get_player_data(gameName, tagName)

# If it's valid, ask for match count, get match IDs, and get match details
if playerData:
    match_ids= get_match_id(playerData['puuid'], matchCount)
    all_events_data = []
    for match_id in match_ids:
            match_details = get_match_details(match_id)
            # Only process Summoner's Rift matches (mapId 11)
            if match_details and match_details['info']['mapId'] == 11:
                # Find the participant ID that matches the puuid
                participant_id = None
                participant_game_name = None
                participant_champion_name = None
                participants = match_details['info']['participants']
                for participant in participants:
                    if participant['puuid'] == playerData['puuid']:
                        participant_id = participant['participantId']
                        participant_game_name = participant['summonerName']
                        participant_champion_name = participant['championName']
                        break
                print(f"Summoner: {participant_game_name}, Champion: {participant_champion_name}")
                # Get match timeline with match ID
                match_timeline = get_match_timeline(match_id)
                # If it's valid, save the events to our list.
                if match_timeline:
                    events_data = save_champion_kill_events(match_timeline, participant_id, participant_game_name)
                    all_events_data.extend(events_data)
    # Save the data to a JSON file
    with open('champion_kill_events.json', 'w') as f:
        json.dump(all_events_data, f, indent=4)
    print("Champion kill events saved to champion_kill_events.json")

# Function to load the champion kill events from a JSON file
def load_champion_kill_events(filename='champion_kill_events.json'):
    with open(filename, 'r') as f:
        data = json.load(f)
    return data




# Print the number of API calls made. This may or may not be accurate. No guarantees on that. Sorry!
print(f"Total API calls made: {api_call_count}")

# Function to analyze the kill events and plot the data
def analyze_kill_events(data):
    # Lists to store scaled coordinates and timestamps
    player_killer_positions = []
    player_victim_positions = []
    player_killer_timestamps = []
    player_victim_timestamps = []

    # Extract player name from the first event
    player_name = data[0]['player_name'] if data else None

    table_data = []
    # Iterate over the champion killed events and translate locations and killer/victim names for each event.
    for event in data:
        scaled_killer_x, scaled_killer_y = scale_coordinates(event['killer_position']['x'], event['killer_position']['y'])
        scaled_victim_x, scaled_victim_y = scale_coordinates(event['victim_position']['x'], event['victim_position']['y'])
        timestamp = convert_timestamp_to_minutes_seconds(event['game_time'])
        #if event['killer_name'] == player_name:  # Use the player's name from the JSON data
            #player_killer_positions.append((scaled_killer_x, scaled_killer_y))
            #player_killer_timestamps.append(timestamp)
        if event['victim_name'] == player_name:  # Use the player's name from the JSON data
            player_victim_positions.append((scaled_victim_x, scaled_victim_y))
            player_victim_timestamps.append(timestamp)
        # Append the data to the table before restarting the loop
        table_data.append([timestamp, event['killer_name'], event['victim_name'], f"({scaled_killer_x}, {scaled_killer_y})", f"({scaled_victim_x}, {scaled_victim_y})",])

    # Display the data in a table using tabulate.
    headers = ["Game Time", "Killer Name", "Victim Name", "Killer Position", "Victim Position"]
    print(tabulate.tabulate(table_data, headers=headers, tablefmt='fancy_grid'))

    # Create the plot using Matplotlib
    fig, ax = plt.figure(figsize=(8, 8)), plt.gca()
    # Make the background transparent
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # Apply the event points to the scatter plot using different colors for kills and deaths. The timestamps are annotated.
    #if player_killer_positions:
       #plt.scatter(*zip(*player_killer_positions), c='blue', label='Kill')
        #for (x, y), timestamp in zip(player_killer_positions, player_killer_timestamps):
           # plt.annotate(timestamp, (x, y), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8, color='blue')
    if player_victim_positions:
        plt.scatter(*zip(*player_victim_positions), c='red', label='Death')
        for (x, y), timestamp in zip(player_victim_positions, player_victim_timestamps):
            plt.annotate(timestamp, (x, y), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8, color='red')
    # Add x/y limits to the plot. I scaled these to my best estimate of the summoners rift proportions, but they need to be adjusted.
    plt.xlim(0, 115)
    plt.ylim(0, 115)

    # Remove inner grid lines, axis numbers, and labels
    plt.grid(False)
    plt.xticks([])
    plt.yticks([])
    plt.xlabel('')
    plt.ylabel('')

    # Save the plot as a transparent PNG image
    transparent_png_path = 'champion_kill_positions.png'
    plt.savefig(transparent_png_path, bbox_inches='tight', pad_inches=0, dpi=200, transparent=True)
    print("Plot saved as champion_kill_positions.png")

    # Rift image is in this directory
    #summoners_rift_image_path = 'summoners_rift.png'
    # Creates a path for the overlaid image
    #output_image_path = 'static/overlaid_image.png'


    # Opens both images, covert them to RGBA, and resizes the overlay image to the base image size
    #base_image = Image.open(summoners_rift_image_path).convert("RGBA")
    #overlay_image = Image.open(transparent_png_path).convert("RGBA")
    #overlay_image = overlay_image.resize(base_image.size, Image.LANCZOS)

    # Combine the images
    #combined_image = Image.alpha_composite(base_image, overlay_image)

    # Save the combined image and output.
    #combined_image.save(output_image_path)
    #print(f"Overlaid image saved as {output_image_path}")


# Analyze and output the kill events
analyze_kill_events(load_champion_kill_events())