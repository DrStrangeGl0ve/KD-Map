import json
import tabulate
import matplotlib.pyplot as plt
from PIL import Image

# This script must be run AFTER game_data.py populates the JSON file.
# This script reads the JSON data from the file champion_kill_events.json and analyzes the kill events.
# It organizes the data into a table and plots the points on a grid representing the Summoner's Rift map.
# It also overlays the points on the Summoner's Rift map image and saves the result as a PNG file.

# Function to load the champion kill events from a JSON file
def load_champion_kill_events(filename='champion_kill_events.json'):
    with open(filename, 'r') as f:
        data = json.load(f)
    return data

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
        if event['killer_name'] == player_name:  # Use the player's name from the JSON data
            player_killer_positions.append((scaled_killer_x, scaled_killer_y))
            player_killer_timestamps.append(timestamp)
        if event['victim_name'] == player_name:  # Use the player's name from the JSON data
            player_victim_positions.append((scaled_victim_x, scaled_victim_y))
            player_victim_timestamps.append(timestamp)
        # Append the data to the table before restarting the loop
        table_data.append([timestamp, event['killer_name'], event['victim_name'], f"({scaled_killer_x}, {scaled_killer_y})", f"({scaled_victim_x}, {scaled_victim_y})",])

    # Display the data in a table using tabulate.
    headers = ["Game Time", "Killer Name", "Victim Name", "Killer Position", "Victim Position", "Assisting Participant IDs"]
    print(tabulate.tabulate(table_data, headers=headers, tablefmt='fancy_grid'))

    # Create the plot using Matplotlib
    fig, ax = plt.figure(figsize=(8, 8)), plt.gca()
    # Make the background transparent
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # Apply the event points to the scatter plot using different colors for kills and deaths. The timestamps are annotated.
    if player_killer_positions:
        plt.scatter(*zip(*player_killer_positions), c='blue', label='Kill')
        for (x, y), timestamp in zip(player_killer_positions, player_killer_timestamps):
            plt.annotate(timestamp, (x, y), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8, color='blue')
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

    # Show the plot
    # Can comment this out if you don't want to display the plot anymore.
    plt.show()
    print("Plot displayed")


    # Rift image is in this directory
    summoners_rift_image_path = 'summoners_rift.png'
    # Creates a path for the overlaid image
    output_image_path = 'overlaid_image.png'

    # Opens both images, covert them to RGBA, and resizes the overlay image to the base image size
    base_image = Image.open(summoners_rift_image_path).convert("RGBA")
    overlay_image = Image.open(transparent_png_path).convert("RGBA")
    overlay_image = overlay_image.resize(base_image.size, Image.LANCZOS)

    # Combine the images
    combined_image = Image.alpha_composite(base_image, overlay_image)

    # Save the combined image and output.
    combined_image.save(output_image_path)
    print(f"Overlaid image saved as {output_image_path}")


# Load and read the data from the json
champion_kill_events = load_champion_kill_events()
# Analyze and output the kill events
analyze_kill_events(champion_kill_events)