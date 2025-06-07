# pylint: disable=W1203 # Use lazy % formatting...
# pylint: disable=C0114 # Missing module docstring
# pylint: disable=C0301 # Line too long

import os
import sys
import time
import json
import logging
from datetime import datetime
import requests
from sendembed import send_embed_group

APP_VERSION = "2.0.0"  # APP_VERSION of the script
LOG_LEVEL = "DEBUG" # INFO, DEBUG, WARNING, ERROR, CRITICAL
# --- Logging ---
#os.system("") # Forces cmd (or other terminal) to support ANSI escape sequences for colors - UNSTABLE!
ENABLE_LOG_COLORS = True  # Set to False if your terminal does not support ANSI colors

class ColoredFormatter(logging.Formatter):
    '''Custom formatter to add colors to log messages based on their level.'''
    GRAY = "\033[90m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    LEVEL_COLORS = {
        'DEBUG': "\033[94m",     # Blue
        'INFO': "\033[96m",      # Light cyan
        'WARNING': "\033[93m",   # Yellow
        'ERROR': "\033[91m",     # Red
        'CRITICAL': "\033[95m",  # Magenta
    }
    def format(self, record):
        if ENABLE_LOG_COLORS:
            level_color = self.LEVEL_COLORS.get(record.levelname, self.WHITE)
            time_str = f"{self.GRAY}{self.formatTime(record)}{self.RESET}"
            level_str = f"{level_color}[{record.levelname}]{self.RESET}"
            msg_str = f"{self.WHITE}{record.getMessage()}{self.RESET}"
            return f"{time_str} {level_str} {msg_str}"
        else:
            time_str = self.formatTime(record)
            level_str = f"[{record.levelname}]"
            msg_str = record.getMessage()
            return f"{time_str} {level_str} {msg_str}"

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ColoredFormatter())

logger = logging.getLogger("RobloxTracker")
logger.setLevel(LOG_LEVEL) # Set level
logger.handlers.clear()
logger.addHandler(handler)
logger.propagate = False

# --- Constants ---
SHOW_LOADED_SETTINGS = False  # Set to False to disable initial settings printout

# --- API Limits ---
FRIENDS_LIMIT = 50 # API limit for friends
FOLLOWERS_FOLLOWINGS_LIMIT = 100 # API limit for followers and followings
ROBLOX_API_WAIT_SECONDS = 1.2  # Wait time between Roblox API requests

# --- API settings ---
# For more sizes, see: https://thumbnails.roblox.com//docs/index.html in /v1/users/avatar
AVATAR_SIZE = "720x720"
AVATAR_HEADSHOT_SIZE = "100x100"
AVATAR_BATCH_LIMIT = 100  # Adjust this value if the API supports a different limit
USERNAME_BATCH_LIMIT = 100  # API supports up to 25 user IDs at once for username requests

# --- Progress Info Settings ---
PROGRESS_INFO_EVERY = 5  # Show info every N operations, set negative to disable
SHOW_PROGRESS_INFO = True  # Set to False to disable all progress info

# --- Settings ---
def load_settings():
    """Load settings from the config.json file."""
    script_directory = os.path.dirname(__file__)
    config_path = os.path.join(script_directory, "SECRET.json")
    with open(config_path, 'r', encoding='utf-8') as file:
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
        "config_file": config_path
    }
    return settings

SETTINGS = load_settings()

# --- Helper functions ---
def print_initial_configuration(settings):
    """Print the initial configuration and webhook status."""
    logger.info("Initial configuration and webhook status")
    logger.info(f"Guilded: {settings['guilded_webhook_url']} | Enabled? {settings['send_guilded_log']}")
    logger.info(f"Discord: {settings['discord_webhook_url']} | Enabled? {settings['send_discord_log']}")
    logger.info(f"Current Relationship Type: {settings['relationship_type_endpoint']}")
    logger.info(f"Send new entries: {settings['send_new_entries']} | Send removed entries: {settings['send_removed_entries']}")
    logger.info(f"Embed wait: {settings['embed_wait_HTTP']}\n")

def check_webhook_urls(settings):
    """Check if the webhook URLs are valid."""
    if not settings["discord_webhook_url"].startswith("https://discord.com/api/webhooks/"):
        logger.warning("The Discord webhook URL is invalid. Sending webhooks is disabled.")
        settings["send_discord_log"] = False
    if not settings["guilded_webhook_url"].startswith("https://media.guilded.gg/webhooks/"):
        logger.warning("The Guilded webhook URL is invalid. Sending webhooks is disabled.")
        settings["send_guilded_log"] = False

def check_relationship_type_endpoint(relationship_type_endpoint):
    """Check if the relationship type endpoint is valid."""
    valid_endpoints = ['friends', 'followers', 'followings']
    if relationship_type_endpoint not in valid_endpoints:
        logger.error(f"'{relationship_type_endpoint}' is not a valid relationship type endpoint. Valid options: {valid_endpoints}")
        time.sleep(5)
        raise SystemExit("Invalid relationship type endpoint. Please check your configuration.")

def check_files_exist(files):
    """Check if required files exist."""
    for file in files:
        if not os.path.isfile(file):
            logger.error(f"File {file} does not exist")
            raise SystemExit(f"Required file {file} is missing. Please check your setup.")

def write_last_run_time(file_path):
    """Write the last execution time to a file."""
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(f"The last execution of the script: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")

def read_from_file(filename):
    """Read lines from a file and return them as a list."""
    if os.path.isfile(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file]
    else:
        logger.info(f"File {filename} does not exist, returning empty list.")
        return []

def write_to_file(filename, data):
    """Write a list of data to a file, one item per line."""
    with open(filename, 'w', encoding='utf-8') as file:
        for item in data:
            file.write(f"{item}\n")

def update_local_data_file(filename, current_data_ids):
    """Update the local data file with the current data IDs."""
    existing_data = set(read_from_file(filename))
    current_data_set = set(current_data_ids)
    if existing_data != current_data_set:
        logger.info("Changes detected, updating local data file.")
        write_to_file(filename, current_data_ids)
    else:
        logger.info("No changes detected, skipping update.")

def chunk_data(data, chunk_size=10):
    """Yield successive chunks of data."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

# --- API ---
def get_friends_ids(user_id):
    """Get the list of friend IDs for a user."""
    logger.info("Fetching friends for user ID")
    all_friend_ids = []
    cursor = ""
    fetch_count = 0
    while True:
        url = f"https://friends.roblox.com/v1/users/{user_id}/friends/find?limit={FRIENDS_LIMIT}&cursor={cursor}&userSort="
        response = requests.get(url, timeout=15)
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Response [{response.status_code}]: {response.text}")
        if response.status_code != 200:
            logger.error(f"HTTP Error {response.status_code}: Failed to fetch friends data")
            raise SystemExit(f"Failed to fetch friends data for user {user_id}. Please check the user ID and try again.")
        data = response.json()
        page_items = data.get("PageItems", [])
        all_friend_ids.extend([str(friend["id"]) for friend in page_items])
        fetch_count += 1
        if SHOW_PROGRESS_INFO and PROGRESS_INFO_EVERY > 0 and fetch_count % PROGRESS_INFO_EVERY == 0:
            logger.info(f"Fetched {len(all_friend_ids)} friend IDs so far...")
        next_cursor = data.get("NextCursor")
        if not next_cursor:
            break
        cursor = next_cursor
        time.sleep(ROBLOX_API_WAIT_SECONDS)
    logger.info(f"Fetched total {len(all_friend_ids)} friend IDs.")
    return all_friend_ids

def get_followers_or_followings_ids(user_id, endpoint):
    """Get the list of follower/following IDs for a user."""
    logger.info(f"Fetching {endpoint} for user ID")
    all_ids = []
    cursor = None
    fetch_count = 0
    while True:
        url = f"https://friends.roblox.com/v1/users/{user_id}/{endpoint}?limit={FOLLOWERS_FOLLOWINGS_LIMIT}&sortOrder=Asc"
        if cursor:
            url += f"&cursor={cursor}"
        response = requests.get(url, timeout=15)
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Response [{response.status_code}]: {response.text}")
        if response.status_code != 200:
            logger.error(f"HTTP Error {response.status_code}: Failed to fetch {endpoint} data")
            raise SystemExit(f"Failed to fetch {endpoint} data for user {user_id}. Please check the user ID and try again.")
        data = response.json()
        ids = [str(user["id"]) for user in data.get("data", [])]
        all_ids.extend(ids)
        fetch_count += 1
        if SHOW_PROGRESS_INFO and PROGRESS_INFO_EVERY > 0 and fetch_count % PROGRESS_INFO_EVERY == 0:
            logger.info(f"Fetched {len(all_ids)} {endpoint} IDs so far...")
        cursor = data.get("nextPageCursor")
        if not cursor:
            break
        time.sleep(ROBLOX_API_WAIT_SECONDS)
    logger.info(f"Fetched total {len(all_ids)} {endpoint} IDs.")
    return all_ids

def get_all_user_ids(settings):
    """Get all user IDs based on the relationship type endpoint."""
    endpoint = settings["relationship_type_endpoint"]
    user_id = settings["target_user_id"]
    if endpoint == "friends":
        return get_friends_ids(user_id)
    return get_followers_or_followings_ids(user_id, endpoint)

def get_usernames(user_ids):
    """Get usernames for a list of user IDs."""
    url = 'https://apis.roblox.com/user-profile-api/v1/user/profiles/get-profiles'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    usernames = {}
    total = len(user_ids)
    processed = 0
    for chunk in chunk_data(user_ids, USERNAME_BATCH_LIMIT):
        data = {
            "fields": ["names.username"],
            "userIds": chunk
        }
        logger.debug(f"[Usernames] Sending data to API (chunk {processed + 1}-{processed + len(chunk)}/{total}):\n{json.dumps(data, indent=2)}")
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=15)
        logger.debug(f"[Usernames] Response [{response.status_code}]:\n{response.text}")
        if response.status_code == 200:
            response_data = response.json()
            for user_data in response_data.get('profileDetails', []):
                user_id = str(user_data.get('userId'))
                username = user_data.get('names', {}).get('username', None)
                if user_id and username:
                    usernames[user_id] = username
                else:
                    logger.warning(f"[Usernames] User ID {user_id} has an unknown username.")
        else:
            logger.error(f"API response error. Code: {response.status_code} | Content: {response.text}")
            raise SystemExit("Failed to fetch usernames from Roblox API. Please check your network connection or API status.")
        processed += len(chunk)
        if SHOW_PROGRESS_INFO and PROGRESS_INFO_EVERY > 0 and processed // USERNAME_BATCH_LIMIT % PROGRESS_INFO_EVERY == 0:
            logger.info(f"Fetched usernames for {len(usernames)}/{total} user IDs so far...")
        time.sleep(ROBLOX_API_WAIT_SECONDS)
    logger.info(f"Fetched usernames for {len(usernames)}/{total} user IDs.")
    return usernames

def get_avatar_and_headshot_urls(session, user_ids):
    """
    Get avatar and headshot URLs for a list of user IDs using batch API requests.
    Returns a dict: {user_id: {"avatar_url": ..., "headshot_url": ...}}
    """
    logger.info("Fetching avatars and headshots for user IDs")
    results = {}
    total = len(user_ids)
    processed = 0
    for chunk in chunk_data(list(user_ids), AVATAR_BATCH_LIMIT):
        ids_str = ",".join(str(uid) for uid in chunk)
        avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={ids_str}&size={AVATAR_SIZE}&format=Png&isCircular=false"
        headshot_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={ids_str}&size={AVATAR_HEADSHOT_SIZE}&format=Png&isCircular=false"
        logger.debug(f"[Avatars] Requesting avatars for user IDs: {ids_str}")
        avatar_response = session.get(avatar_url)
        logger.debug(f"[Avatars] Avatar batch URL: {avatar_url} | Status: {avatar_response.status_code}")
        headshot_response = session.get(headshot_url)
        logger.debug(f"[Avatars] Headshot batch URL: {headshot_url} | Status: {headshot_response.status_code}")
        avatar_data = avatar_response.json()["data"] if avatar_response.status_code == 200 else []
        headshot_data = headshot_response.json()["data"] if headshot_response.status_code == 200 else []
        logger.debug(f"[Avatars] Avatar API returned {len(avatar_data)} results. Headshot API returned {len(headshot_data)} results.")
        for entry in avatar_data:
            user_id = str(entry.get("targetId"))
            results.setdefault(user_id, {})["avatar_url"] = entry.get("imageUrl")
        for entry in headshot_data:
            user_id = str(entry.get("targetId"))
            results.setdefault(user_id, {})["headshot_url"] = entry.get("imageUrl")
        processed += len(chunk)
        if SHOW_PROGRESS_INFO and PROGRESS_INFO_EVERY > 0 and processed // AVATAR_BATCH_LIMIT % PROGRESS_INFO_EVERY == 0:
            logger.info(f"Fetched avatars/headshots for {len(results)}/{total} user IDs so far...")
        time.sleep(ROBLOX_API_WAIT_SECONDS)
    logger.info(f"Fetched avatars and headshots for {len(results)}/{total} user IDs.")
    return results

# --- Main logic ---
def main():
    """Main function to run the script."""
    check_webhook_urls(SETTINGS)
    check_relationship_type_endpoint(SETTINGS["relationship_type_endpoint"])
    check_files_exist([SETTINGS["last_run_time_file"], SETTINGS["local_data_file"], SETTINGS["config_file"]])
    if SHOW_LOADED_SETTINGS:
        print_initial_configuration(SETTINGS)

    session = requests.Session()
    all_user_ids = get_all_user_ids(SETTINGS)
    logger.info(f"Fetched {len(all_user_ids)} user IDs from Roblox API.")

    local_data_ids = set(read_from_file(SETTINGS["local_data_file"]))
    current_data_set = set(all_user_ids)

    new_user_ids = [user_id for user_id in all_user_ids if user_id not in local_data_ids]
    removed_user_ids = [user_id for user_id in local_data_ids if user_id not in current_data_set]

    # Only fetch usernames and avatars for new and removed users
    usernames = {}
    avatars = {}
    ids_to_fetch = set(new_user_ids) | set(removed_user_ids)
    if ids_to_fetch:
        usernames = get_usernames(list(ids_to_fetch))
        avatars = get_avatar_and_headshot_urls(session, ids_to_fetch)
    else:
        logger.info("No new or removed users to fetch usernames or avatars for.")

    webhook_sent = 0
    webhook_waiting = 0
    total_webhooks = 0
    # Calculate total webhooks to send
    if SETTINGS["send_new_entries"]:
        total_webhooks += (len(new_user_ids) + 9) // 10 * (SETTINGS["send_discord_log"] + SETTINGS["send_guilded_log"])
    if SETTINGS["send_removed_entries"]:
        total_webhooks += (len(removed_user_ids) + 9) // 10 * (SETTINGS["send_discord_log"] + SETTINGS["send_guilded_log"])
    webhook_waiting = total_webhooks

    # New entries
    if SETTINGS["send_new_entries"]:
        for chunk in chunk_data(new_user_ids, 10):
            embed_data_list = []
            for user_id in chunk:
                embed_data = {
                    "username": usernames.get(user_id, "Unknown"),
                    "user_id": user_id,
                    "avatar_url": avatars.get(user_id, {}).get("avatar_url", None),
                    "headshot_url": avatars.get(user_id, {}).get("headshot_url", None),
                    "removed": False,
                    "total_count": len(all_user_ids)
                }
                embed_data_list.append(embed_data)
                logger.debug(f"New user data: {embed_data}")
            for platform, enabled in [("discord", SETTINGS["send_discord_log"]), ("guilded", SETTINGS["send_guilded_log"])]:
                if enabled:
                    send_embed_group(platform, SETTINGS[f"{platform}_webhook_url"], SETTINGS["relationship_type_endpoint"], embed_data_list, APP_VERSION)
                    webhook_sent += 1
                    webhook_waiting -= 1
                    if webhook_sent % 5 == 0 or webhook_sent == total_webhooks:
                        logger.info(f"Webhooks sent: {webhook_sent} | Webhooks waiting: {webhook_waiting}")
            time.sleep(SETTINGS["embed_wait_HTTP"])

    # Removed entries
    if SETTINGS["send_removed_entries"]:
        for chunk in chunk_data(removed_user_ids, 10):
            embed_data_list = []
            for user_id in chunk:
                embed_data = {
                    "username": usernames.get(user_id, "Unknown"),
                    "user_id": user_id,
                    "avatar_url": avatars.get(user_id, {}).get("avatar_url", None),
                    "headshot_url": avatars.get(user_id, {}).get("headshot_url", None),
                    "removed": True,
                    "total_count": len(all_user_ids)
                }
                embed_data_list.append(embed_data)
                logger.debug(f"Removed user data: {embed_data}")
            for platform, enabled in [("discord", SETTINGS["send_discord_log"]), ("guilded", SETTINGS["send_guilded_log"])]:
                if enabled:
                    send_embed_group(platform, SETTINGS[f"{platform}_webhook_url"], SETTINGS["relationship_type_endpoint"], embed_data_list, APP_VERSION)
                    webhook_sent += 1
                    webhook_waiting -= 1
                    if webhook_sent % 5 == 0 or webhook_sent == total_webhooks:
                        logger.info(f"Webhooks sent: {webhook_sent} | Webhooks waiting: {webhook_waiting}")
            time.sleep(SETTINGS["embed_wait_HTTP"])

    update_local_data_file(SETTINGS["local_data_file"], all_user_ids)
    write_last_run_time(SETTINGS["last_run_time_file"])
    session.close()

if __name__ == "__main__":
    main()
