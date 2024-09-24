version = "1.0.6"
import os
import sys
import requests
import time
import json
from datetime import datetime
from SendEmbed import send_embed_group

# Define file names for local data storage
# Dynamic directories
script_directory = os.path.dirname(__file__)
local_data_file = os.path.join(script_directory, "LocalData")
last_run_time_file = os.path.join(script_directory, "LastRunTime.txt")
JSON_file = os.path.join(script_directory, "config.json")

# Load settings from config.json file
def load_config():
    """Load configuration settings from config.json file."""
    with open(JSON_file, 'r') as file:
        config = json.load(file)
    return config

# Load configuration settings
config = load_config()

# Extract configuration values from the config dictionary
discord_webhook_url = config["discord_webhook_url"]
guilded_webhook_url = config["guilded_webhook_url"]
relationship_type_endpoint  = config["relationshipType"]
target_user_id = config["Your_User_ID"]
send_discord_log = config["send_discord_log"]
send_guilded_log = config["send_guilded_log"]
send_new_entries = config["send_new_entries"]
send_removed_entries = config["send_removed_entries"]
embed_wait_HTTP = config["embed_wait_HTTP"]

# This module defines a function to validate webhook URLs for Discord and Guilded.
def check_webhook_urls(discord_webhook_url, guilded_webhook_url, send_discord_log, send_guilded_log):
    """
    Validate webhook URLs for Discord and Guilded.
    If a URL is invalid, set the corresponding logging flag to False and print a warning message.
    """
    # Check Discord webhook URL
    if not discord_webhook_url.startswith("https://discord.com/api/webhooks/"):
        print("Warning: The Discord webhook URL is invalid. Sending webhooks is disabled.")
        send_discord_log = False
    else:
        print("Discord webhook URL is valid.")

    # Check Guilded webhook URL
    if not guilded_webhook_url.startswith("https://media.guilded.gg/webhooks/"):
        print("Warning: The Guilded webhook URL is invalid. Sending webhooks is disabled.")
        send_guilded_log = False
    else:
        print("Guilded webhook URL is valid.")

    return send_discord_log, send_guilded_log

def check_relationship_type_endpoint_configuration(relationship_type_endpoint):
    # List of valid endpoints
    valid_endpoints = ['friends', 'followers', 'followings']
    
    # Check if the entered endpoint is in the list of valid ones
    if relationship_type_endpoint not in valid_endpoints:
        print(f"Warning: '{relationship_type_endpoint}' is not a valid relationship type endpoint.")
        print("Valid options are: 'friends', 'followers', 'followings'.")
        
        # Termination of the script after 5 seconds if the endpoint is invalid
        time.sleep(5)
        sys.exit(1)
    


# Validate webhook URLs and update flags
send_discord_log, send_guilded_log = check_webhook_urls(discord_webhook_url, guilded_webhook_url, send_discord_log, send_guilded_log)

# Validate the relationship type endpoint and terminate if invalid
check_relationship_type_endpoint_configuration(relationship_type_endpoint)

# Print initial configuration and webhook status
Print_initial_configuration = True
if Print_initial_configuration:
    print("\nInitial configuration and webhook status")
    print(f"Guilded: {guilded_webhook_url} \nEnabled? {send_guilded_log}")
    print(f"Discord: {discord_webhook_url} \nEnabled? {send_discord_log}")
    print(f"Current Relationship Type: {relationship_type_endpoint}")
    print(f"Send new entries: {send_new_entries} \nSend removed entries: {send_removed_entries}")
    print(f"Embed wait: {embed_wait_HTTP} \n")

# Write the last run time to a file
def write_last_run_time(last_run_time_file):
    """Write the current date and time to the last run time file."""
    with open(last_run_time_file, 'w') as file:
        file.write(f"The last execution of the script: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")

# Append data to a file
def write_to_file_append(file_path, data):
    """Append data to the specified file."""
    with open(file_path, 'a') as file:
        for item in data:
            file.write(f"{item}\n")

# Check if specified files exist
def check_files_exist(files):
    """Check if each file in the provided list exists. If any file is missing, exit the program."""
    for file in files:
        if not os.path.isfile(file):
            print(f"File {file} does not exist")
            sys.exit()

# Fetch data from Roblox API
def get_RBLX_Users_API(target, cursor=None):
    """Fetch user data from Roblox API for a given target user ID."""
    url = f"https://friends.roblox.com/v1/users/{target}/{relationship_type_endpoint}?limit=100&sortOrder=Asc"
    if cursor:
        url += f"&cursor={cursor}"
    #print(f"Fetching data from URL: {url}")  # Debug URL
    response = requests.get(url)
    if response.status_code != 200:
        print(f"HTTP Error {response.status_code}: Failed to fetch data")
        sys.exit()

    data = response.json()

    if 'data' in data and 'nextPageCursor' in data:
        HTTP_Data_Server = [{'id': str(user['id']), 'name': user['name']} for user in data['data']]
        next_cursor = data['nextPageCursor']
        total_count_server = data.get('total', len(HTTP_Data_Server))  # Get total number of users if available
        return HTTP_Data_Server, next_cursor, total_count_server
    elif 'data' in data:
        HTTP_Data_Server = [{'id': str(user['id']), 'name': user['name']} for user in data['data']]
        total_count_server = len(HTTP_Data_Server)  # Determine number of users
        return HTTP_Data_Server, None, total_count_server
    else:
        return [], None, 0

# Fetch all Roblox users data by paginating through the API
def fetch_all_RBLX_Users_Data(target):
    """Fetch all user data for a target user by paginating through Roblox API."""
    HTTP_Data_Server = []
    cursor = None
    total_count_server = 0
    while True:
        part, cursor, count = get_RBLX_Users_API(target, cursor)
        HTTP_Data_Server.extend(part)
        total_count_server += count
        if cursor is None:
            break
    return HTTP_Data_Server, total_count_server

# Write data to a file
def write_to_file(filename, data):
    """Write data to the specified file, overwriting existing content."""
    with open(filename, 'w') as file:
        for item in data:
            file.write(f"{item}\n")
    #print(f"Data saved to file {filename}: {data}")  # Debug data writing

def update_local_data_file(filename, current_data_ids):
    """Update local data file only if there are changes in the user list."""
    # Read existing data from the file
    existing_data = set(read_from_file(filename))
    
    # Convert current data to a set for comparison
    current_data_set = set(current_data_ids)
    
    # Check if there are changes
    if existing_data != current_data_set:
        print("Changes detected, updating local data file.")
        write_to_file(filename, current_data_ids)
    else:
        print("No changes detected, skipping update.")

# Read data from a file
def read_from_file(filename):
    """Read data from the specified file. If the file does not exist, return an empty list."""
    if os.path.isfile(filename):
        with open(filename, 'r') as file:
            data = [line.strip() for line in file]
        #print(f"Data read from file {filename}: {data}")  # Debug data reading
        return data
    else:
        print(f"File {filename} does not exist, returning empty list.")
        return []

# Get avatar and headshot URLs by user ID
def get_avatar_and_headshot_urls(session, user_id):
    """Get avatar and headshot image URLs for a given Roblox user ID."""
    avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=720x720&format=Png&isCircular=false"
    headshot_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=720x720&format=Png&isCircular=false"
    
    avatar_response = session.get(avatar_url)
    headshot_response = session.get(headshot_url)
    
    if avatar_response.status_code == 200 and headshot_response.status_code == 200:
        avatar_data = avatar_response.json()
        headshot_data = headshot_response.json()
        avatar_image_url = avatar_data['data'][0]['imageUrl'] if 'data' in avatar_data and avatar_data['data'] else None
        headshot_image_url = headshot_data['data'][0]['imageUrl'] if 'data' in headshot_data and headshot_data['data'] else None
        return avatar_image_url, headshot_image_url
    return None, None

# Get username by user ID for "send_removed_entries" module
def get_username(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get('name')
    return None

def chunk_data(data, chunk_size=10):
    """Divide data into chunks of the specified size."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

# Main function
def main():
    # For Debug
    def send_embed_group_DEBUG():
        print(f"Sending data to send_embed_group:")
        print(f"Relationship type endpoint: {relationship_type_endpoint}")
        print(f"Embed data list: {embed_data_list}")
        print(f"Version: {version}")
    # Use a session for HTTP connections
    session = requests.Session()
    check_files_exist([last_run_time_file, local_data_file, JSON_file])

    current_data, total_count_server = fetch_all_RBLX_Users_Data(target_user_id)
    local_data_ids = set(read_from_file(local_data_file))

    new_data = [user for user in current_data if user['id'] not in local_data_ids]
    missing_in_local_list = [user_id for user_id in local_data_ids if user_id not in {user['id'] for user in current_data}]

    if send_new_entries:
        # Grouping new users by 10
        for new_users_chunk in chunk_data(new_data, 10):
            embed_data_list = []
            for user in new_users_chunk:
                user_id = user['id']
                username = user['name']
                avatar_url, headshot_url = get_avatar_and_headshot_urls(session, user_id)
                
                if username:
                    embed_data = {
                        "username": username,
                        "user_id": user_id,
                        "avatar_url": avatar_url,
                        "headshot_url": headshot_url,
                        "removed": False,
                        "total_count": total_count_server
                    }
                    embed_data_list.append(embed_data)

            # Sending one request with up to 10 users to Discord and/or Guilded
            if send_discord_log:
                # Debugging - before calling send_embed_group
                #send_embed_group_DEBUG()

                send_embed_group('discord', discord_webhook_url, relationship_type_endpoint, embed_data_list, version)
            if send_guilded_log:
                # Debugging - before calling send_embed_group
                #send_embed_group_DEBUG()

                send_embed_group('guilded', guilded_webhook_url, relationship_type_endpoint, embed_data_list, version)

            time.sleep(embed_wait_HTTP)

    if send_removed_entries:
        # Grouping deleted users by 10
        for removed_users_chunk in chunk_data(missing_in_local_list, 10):
            embed_data_list = []
            for user_id in removed_users_chunk:
                username = get_username(user_id)
                avatar_url, headshot_url = get_avatar_and_headshot_urls(session, user_id)

                embed_data = {
                    "username": username,
                    "user_id": user_id,
                    "avatar_url": avatar_url,
                    "headshot_url": headshot_url,
                    "removed": True,
                    "total_count": total_count_server
                }
                embed_data_list.append(embed_data)

            # Send one request with up to 10 deleted users to Discord and Guilded
            if send_discord_log:
                # Debugging - before calling send_embed_group
                #send_embed_group_DEBUG()

                send_embed_group('discord', discord_webhook_url, relationship_type_endpoint, embed_data_list, version)
            if send_guilded_log:
                # Debugging - before calling send_embed_group
                #send_embed_group_DEBUG()

                send_embed_group('guilded', guilded_webhook_url, relationship_type_endpoint, embed_data_list, version)

            time.sleep(embed_wait_HTTP)

    update_local_data_file(local_data_file, [user['id'] for user in current_data])
    write_last_run_time(last_run_time_file)
    session.close()

# Run the main function if the script is executed directly
if __name__ == "__main__":
    main()
