import os
import sys
import requests
import time
import json
import logging
from datetime import datetime
from SendEmbed import send_embed_group

# --- Constants ---
FRIENDS_LIMIT = 50
FOLLOWERS_FOLLOWINGS_LIMIT = 100
ROBLOX_API_WAIT_SECONDS = 1.2  # Wait time between Roblox API requests
AVATAR_SIZE = "720x720"
AVATAR_HEADSHOT_SIZE = "720x720"
# Maximum number of user IDs supported by the avatar/headshot API endpoints in one request
AVATAR_BATCH_LIMIT = 100  # Adjust this value if the API supports a different limit
# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RobloxTracker")

# --- Settings ---
def load_settings():
    script_directory = os.path.dirname(__file__)
    config_path = os.path.join(script_directory, "SECRET.json")
    with open(config_path, 'r') as file:
        config = json.load(file)
    settings = {
        "discord_webhook_url": config["discord_webhook_url"],
        "guilded_webhook_url": config["guilded_webhook_url"],
        "relationship_type_endpoint": config["relationshipType"],
        "target_user_id": config["Your_User_ID"],
        "send_discord_log": config["send_discord_log"],
        "send_guilded_log": config["send_guilded_log"],
        "send_new_entries": config["send_new_entries"],
        "send_removed_entries": config["send_removed_entries"],
        "embed_wait_HTTP": config["embed_wait_HTTP"],
        "local_data_file": os.path.join(script_directory, "LocalDataTemp"),
        "last_run_time_file": os.path.join(script_directory, "LastRunTime.txt"),
        "config_file": config_path,
        "version": "1.0.7"
    }
    return settings

SETTINGS = load_settings()

# --- Helper functions ---
def print_initial_configuration(settings):
    logger.info("Initial configuration and webhook status")
    logger.info(f"Guilded: {settings['guilded_webhook_url']} | Enabled? {settings['send_guilded_log']}")
    logger.info(f"Discord: {settings['discord_webhook_url']} | Enabled? {settings['send_discord_log']}")
    logger.info(f"Current Relationship Type: {settings['relationship_type_endpoint']}")
    logger.info(f"Send new entries: {settings['send_new_entries']} | Send removed entries: {settings['send_removed_entries']}")
    logger.info(f"Embed wait: {settings['embed_wait_HTTP']}")

def check_webhook_urls(settings):
    if not settings["discord_webhook_url"].startswith("https://discord.com/api/webhooks/"):
        logger.warning("The Discord webhook URL is invalid. Sending webhooks is disabled.")
        settings["send_discord_log"] = False
    if not settings["guilded_webhook_url"].startswith("https://media.guilded.gg/webhooks/"):
        logger.warning("The Guilded webhook URL is invalid. Sending webhooks is disabled.")
        settings["send_guilded_log"] = False

def check_relationship_type_endpoint(relationship_type_endpoint):
    valid_endpoints = ['friends', 'followers', 'followings']
    if relationship_type_endpoint not in valid_endpoints:
        logger.error(f"'{relationship_type_endpoint}' is not a valid relationship type endpoint. Valid options: {valid_endpoints}")
        time.sleep(5)
        sys.exit(1)

def check_files_exist(files):
    for file in files:
        if not os.path.isfile(file):
            logger.error(f"File {file} does not exist")
            sys.exit()

def write_last_run_time(file_path):
    with open(file_path, 'w') as file:
        file.write(f"The last execution of the script: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")

def read_from_file(filename):
    if os.path.isfile(filename):
        with open(filename, 'r') as file:
            return [line.strip() for line in file]
    else:
        logger.info(f"File {filename} does not exist, returning empty list.")
        return []

def write_to_file(filename, data):
    with open(filename, 'w') as file:
        for item in data:
            file.write(f"{item}\n")

def update_local_data_file(filename, current_data_ids):
    existing_data = set(read_from_file(filename))
    current_data_set = set(current_data_ids)
    if existing_data != current_data_set:
        logger.info("Changes detected, updating local data file.")
        write_to_file(filename, current_data_ids)
    else:
        logger.info("No changes detected, skipping update.")

def chunk_data(data, chunk_size=10):
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

# --- API ---
def get_friends_ids(user_id):
    """Get the list of friend IDs for a user."""
    all_friend_ids = []
    cursor = ""
    while True:
        url = f"https://friends.roblox.com/v1/users/{user_id}/friends/find?limit={FRIENDS_LIMIT}&cursor={cursor}&userSort="
        response = requests.get(url)
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Response [{response.status_code}]: {response.text}")
        if response.status_code != 200:
            logger.error(f"HTTP Error {response.status_code}: Failed to fetch friends data")
            sys.exit()
        data = response.json()
        page_items = data.get("PageItems", [])
        all_friend_ids.extend([str(friend["id"]) for friend in page_items])
        next_cursor = data.get("NextCursor")
        if not next_cursor:
            break
        cursor = next_cursor
        time.sleep(ROBLOX_API_WAIT_SECONDS)
    return all_friend_ids

def get_followers_or_followings_ids(user_id, endpoint):
    """Get the list of follower/following IDs for a user."""
    all_ids = []
    cursor = None
    while True:
        url = f"https://friends.roblox.com/v1/users/{user_id}/{endpoint}?limit={FOLLOWERS_FOLLOWINGS_LIMIT}&sortOrder=Asc"
        if cursor:
            url += f"&cursor={cursor}"
        response = requests.get(url)
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Response [{response.status_code}]: {response.text}")
        if response.status_code != 200:
            logger.error(f"HTTP Error {response.status_code}: Failed to fetch {endpoint} data")
            sys.exit()
        data = response.json()
        ids = [str(user["id"]) for user in data.get("data", [])]
        all_ids.extend(ids)
        cursor = data.get("nextPageCursor")
        if not cursor:
            break
        time.sleep(ROBLOX_API_WAIT_SECONDS)
    return all_ids

def get_all_user_ids(settings):
    endpoint = settings["relationship_type_endpoint"]
    user_id = settings["target_user_id"]
    if endpoint == "friends":
        return get_friends_ids(user_id)
    else:
        return get_followers_or_followings_ids(user_id, endpoint)

def get_usernames(user_ids):
    """Get usernames for a list of user IDs."""
    url = 'https://apis.roblox.com/user-profile-api/v1/user/profiles/get-profiles'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    usernames = {}
    for chunk in chunk_data(user_ids, 25):  # API supports up to 25 users at once
        data = {
            "fields": ["names.username"],
            "userIds": chunk
        }
        logger.debug(f"Sending data to API: {json.dumps(data, indent=4)}")
        response = requests.post(url, headers=headers, data=json.dumps(data))
        logger.debug(f"Response [{response.status_code}]: {response.text}")
        if response.status_code == 200:
            response_data = response.json()
            for user_data in response_data.get('profileDetails', []):
                user_id = str(user_data.get('userId'))
                username = user_data.get('names', {}).get('username', None)
                if user_id and username:
                    usernames[user_id] = username
                else:
                    logger.debug(f"User ID {user_id} has an unknown username.")
        else:
            logger.error(f"API response error. Code: {response.status_code} | Content: {response.text}")
            sys.exit("Script terminated due to API response error.")
        time.sleep(ROBLOX_API_WAIT_SECONDS)
    return usernames

def get_avatar_and_headshot_urls(session, user_ids):
    """
    Get avatar and headshot URLs for a list of user IDs using batch API requests.
    Returns a dict: {user_id: {"avatar_url": ..., "headshot_url": ...}}
    """
    results = {}
    # Process in batches to respect the API's batch limit
    for chunk in chunk_data(list(user_ids), AVATAR_BATCH_LIMIT):
        ids_str = ",".join(str(uid) for uid in chunk)
        avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={ids_str}&size={AVATAR_SIZE}&format=Png&isCircular=false"
        headshot_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={ids_str}&size={AVATAR_HEADSHOT_SIZE}&format=Png&isCircular=false"
        avatar_response = session.get(avatar_url)
        headshot_response = session.get(headshot_url)
        logger.debug(f"Avatar batch URL: {avatar_url} | Status: {avatar_response.status_code}")
        logger.debug(f"Headshot batch URL: {headshot_url} | Status: {headshot_response.status_code}")
        avatar_data = avatar_response.json()["data"] if avatar_response.status_code == 200 else []
        headshot_data = headshot_response.json()["data"] if headshot_response.status_code == 200 else []
        # Map userId to avatar/headshot URLs
        for entry in avatar_data:
            user_id = str(entry.get("targetId"))
            results.setdefault(user_id, {})["avatar_url"] = entry.get("imageUrl")
        for entry in headshot_data:
            user_id = str(entry.get("targetId"))
            results.setdefault(user_id, {})["headshot_url"] = entry.get("imageUrl")
        time.sleep(ROBLOX_API_WAIT_SECONDS)
    return results

# --- Main logic ---
def main():
    check_webhook_urls(SETTINGS)
    check_relationship_type_endpoint(SETTINGS["relationship_type_endpoint"])
    check_files_exist([SETTINGS["last_run_time_file"], SETTINGS["local_data_file"], SETTINGS["config_file"]])
    print_initial_configuration(SETTINGS)

    session = requests.Session()
    all_user_ids = get_all_user_ids(SETTINGS)
    logger.info(f"Fetched {len(all_user_ids)} user IDs from Roblox API.")

    local_data_ids = set(read_from_file(SETTINGS["local_data_file"]))
    current_data_set = set(all_user_ids)

    new_user_ids = [user_id for user_id in all_user_ids if user_id not in local_data_ids]
    removed_user_ids = [user_id for user_id in local_data_ids if user_id not in current_data_set]

    # Get usernames and avatars for ALL users (rate limit!)
    all_needed_ids = set(all_user_ids) | set(removed_user_ids)
    usernames = get_usernames(list(all_needed_ids))
    avatars = get_avatar_and_headshot_urls(session, all_needed_ids)

    # New entries
    if SETTINGS["send_new_entries"]:
        for chunk in chunk_data(new_user_ids, 10):
            embed_data_list = []
            for user_id in chunk:
                embed_data = {
                    "username": usernames.get(user_id, "Unknown"),
                    "user_id": user_id,
                    "avatar_url": avatars[user_id]["avatar_url"],
                    "headshot_url": avatars[user_id]["headshot_url"],
                    "removed": False,
                    "total_count": len(all_user_ids)
                }
                embed_data_list.append(embed_data)
                logger.debug(f"New user data: {embed_data}")
            if SETTINGS["send_discord_log"]:
                send_embed_group('discord', SETTINGS["discord_webhook_url"], SETTINGS["relationship_type_endpoint"], embed_data_list, SETTINGS["version"])
            if SETTINGS["send_guilded_log"]:
                send_embed_group('guilded', SETTINGS["guilded_webhook_url"], SETTINGS["relationship_type_endpoint"], embed_data_list, SETTINGS["version"])
            time.sleep(SETTINGS["embed_wait_HTTP"])

    # Removed entries
    if SETTINGS["send_removed_entries"]:
        for chunk in chunk_data(removed_user_ids, 10):
            embed_data_list = []
            for user_id in chunk:
                embed_data = {
                    "username": usernames.get(user_id, "Unknown"),
                    "user_id": user_id,
                    "avatar_url": avatars[user_id]["avatar_url"],
                    "headshot_url": avatars[user_id]["headshot_url"],
                    "removed": True,
                    "total_count": len(all_user_ids)
                }
                embed_data_list.append(embed_data)
                logger.debug(f"Removed user data: {embed_data}")
            if SETTINGS["send_discord_log"]:
                send_embed_group('discord', SETTINGS["discord_webhook_url"], SETTINGS["relationship_type_endpoint"], embed_data_list, SETTINGS["version"])
            if SETTINGS["send_guilded_log"]:
                send_embed_group('guilded', SETTINGS["guilded_webhook_url"], SETTINGS["relationship_type_endpoint"], embed_data_list, SETTINGS["version"])
            time.sleep(SETTINGS["embed_wait_HTTP"])

    update_local_data_file(SETTINGS["local_data_file"], all_user_ids)
    write_last_run_time(SETTINGS["last_run_time_file"])
    session.close()

if __name__ == "__main__":
    main()