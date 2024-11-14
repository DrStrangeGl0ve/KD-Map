import requests
import time
import json
from tabulate import tabulate
from config import API_KEY

# IMPORTANT: Before you run this script, be sure to look at the README for instructions on how to store your API key for it to function properly.
# Run this BEFORE running the analyze_kill_events.py script.

# This is the initial script that you will run to collect the data from the Riot Games API.
# It'll be output to the champion_kill_events.json file, which will be used in the analyze_kill_events.py script.

# By default, this only checks games played on Summoner's rift. If you request 10 game records and only receive 6, it's because the other 4 games were not played on Summoner's Rift.


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
    url = f"{MATCHES_URL}by-puuid/{puuid}/ids?start=0&count={count}"
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

# Request the Riot ID and tag line from the user.
gameName = input("Enter game Riot ID: ")
tagName = input("Enter tag line (no hashtag): ")


# Get the player data and save the PUUID to a file
playerData = get_player_data(gameName, tagName)

# If it's valid, ask for match count, get match IDs, and get match details
if playerData:
    matchCount = int(input("Enter the number of matches you want to see: "))
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



# Print the number of API calls made. This may or may not be accurate. No guarantees on that. Sorry!
print(f"Total API calls made: {api_call_count}")