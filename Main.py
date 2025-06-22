# pylint: disable=W1203 # Use lazy % formatting...
# pylint: disable=C0114 # Missing module docstring
# pylint: disable=C0301 # Line too long
# pylint: disable=W0718 # Catching too general exception

import os
import sys
import time
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
import aiohttp
from sendembed import send_embed_group

APP_VERSION = "2.1.0"  # Updated version
LOG_LEVEL = "INFO" # INFO, DEBUG, WARNING, ERROR, CRITICAL
ENABLE_LOG_COLORS = True  # Set to False if your terminal does not support ANSI colors

CONFIG_FILE_NAME = "config.json"

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

class RateLimiter:
    '''Simple rate limiter with exponential backoff'''
    def __init__(self, base_delay: float = 1.2, max_delay: float = 60.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.current_delay = base_delay
        self.last_request_time = 0

    async def wait(self):
        '''Wait for rate limit'''
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.current_delay:
            await asyncio.sleep(self.current_delay - time_since_last)
        self.last_request_time = time.time()

    def reset_delay(self):
        '''Reset delay to base value on successful request'''
        self.current_delay = self.base_delay

    def increase_delay(self):
        '''Increase delay on failed request'''
        self.current_delay = min(self.current_delay * 2, self.max_delay)

# --- Logging Setup ---
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ColoredFormatter())

logger = logging.getLogger("RobloxTracker")
logger.setLevel(LOG_LEVEL)
logger.handlers.clear()
logger.addHandler(handler)
logger.propagate = False

# --- Constants ---
SHOW_LOADED_SETTINGS = False
FRIENDS_LIMIT = 50
FOLLOWERS_FOLLOWINGS_LIMIT = 100
AVATAR_SIZE = "720x720"
AVATAR_HEADSHOT_SIZE = "100x100"
AVATAR_BATCH_LIMIT = 100
USERNAME_BATCH_LIMIT = 100
PROGRESS_INFO_EVERY = 5
SHOW_PROGRESS_INFO = True
MAX_CONCURRENT_REQUESTS = 10  # Limit concurrent requests
REQUEST_TIMEOUT = 30  # Increased timeout for better reliability

# --- Settings ---
def load_settings() -> Dict:
    """Load settings from the config.json file with validation."""
    try:
        script_directory = os.path.dirname(__file__)
        config_path = os.path.join(script_directory, CONFIG_FILE_NAME)

        with open(config_path, 'r', encoding='utf-8') as file:
            config = json.load(file)

        # Validate required fields
        required_fields = ["discord_webhook_url", "guilded_webhook_url", "relationshipType", "Your_User_ID"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")

        # Validate user ID
        try:
            user_id = int(config["Your_User_ID"])
            if user_id <= 0:
                raise ValueError("User ID must be a positive integer")
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid user ID format") from exc

        settings = {
            "discord_webhook_url": config["discord_webhook_url"],
            "guilded_webhook_url": config["guilded_webhook_url"],
            "relationship_type_endpoint": config["relationshipType"],
            "target_user_id": str(user_id),
            "send_discord_log": config.get("send_discord_log", False),
            "send_guilded_log": config.get("send_guilded_log", False),
            "send_new_entries": config.get("send_new_entries", True),
            "send_removed_entries": config.get("send_removed_entries", True),
            "embed_wait_HTTP": max(0.1, config.get("embed_wait_HTTP", 1.0)),
            "local_data_file": os.path.join(script_directory, "LocalDataTemp"),
            "last_run_time_file": os.path.join(script_directory, "LastRunTime.txt"),
            "config_file": config_path
        }

        return settings

    except FileNotFoundError as exc:
        logger.error("Config file not found. Please create config.json")
        raise SystemExit("Configuration file missing") from exc
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        raise SystemExit("Invalid configuration file format") from e
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        raise SystemExit("Failed to load configuration") from e

# --- Helper functions ---
def validate_settings(settings: Dict) -> None:
    """Validate and fix settings."""
    # Check webhook URLs
    if not settings["discord_webhook_url"].startswith("https://discord.com/api/webhooks/"):
        logger.warning("Invalid Discord webhook URL. Discord webhooks disabled.")
        settings["send_discord_log"] = False

    if not settings["guilded_webhook_url"].startswith("https://media.guilded.gg/webhooks/"):
        logger.warning("Invalid Guilded webhook URL. Guilded webhooks disabled.")
        settings["send_guilded_log"] = False

    # Check relationship type
    valid_endpoints = ['friends', 'followers', 'followings']
    if settings["relationship_type_endpoint"] not in valid_endpoints:
        logger.error(f"Invalid relationship type: {settings['relationship_type_endpoint']}")
        raise SystemExit(f"Valid options: {valid_endpoints}")

def ensure_files_exist(files: List[str]) -> None:
    """Ensure required files exist, create empty ones if needed."""
    for file_path in files:
        if not os.path.isfile(file_path):
            logger.info(f"Creating missing file: {file_path}")
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    if file_path.endswith('.txt'):
                        f.write(f"Created: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            except Exception as e:
                logger.error(f"Failed to create file {file_path}: {e}")
                raise SystemExit(f"Cannot create required file: {file_path}") from e

def read_from_file(filename: str) -> List[str]:
    """Read lines from a file safely."""
    try:
        if os.path.isfile(filename):
            with open(filename, 'r', encoding='utf-8') as file:
                return [line.strip() for line in file if line.strip()]
        return []
    except Exception as e:
        logger.error(f"Error reading file {filename}: {e}")
        return []

def write_to_file(filename: str, data: List[str]) -> bool:
    """Write data to file safely."""
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            for item in data:
                file.write(f"{item}\n")
        return True
    except Exception as e:
        logger.error(f"Error writing to file {filename}: {e}")
        return False

def write_last_run_time(file_path: str) -> None:
    """Write the last execution time to a file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(f"Last execution: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
    except Exception as e:
        logger.error(f"Failed to write last run time: {e}")

def chunk_data(data: List, chunk_size: int = 10) -> List[List]:
    """Split data into chunks."""
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

# --- Async API Functions ---
async def make_request_with_retry(session: aiohttp.ClientSession, url: str,
                                  rate_limiter: RateLimiter, max_retries: int = 3) -> Optional[Dict]:
    """Make HTTP request with retry logic and rate limiting."""
    for attempt in range(max_retries):
        try:
            await rate_limiter.wait()

            async with session.get(url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as response:
                if response.status == 200:
                    rate_limiter.reset_delay()
                    return await response.json()
                elif response.status == 429:  # Rate limited
                    logger.warning(f"Rate limited, attempt {attempt + 1}/{max_retries}")
                    rate_limiter.increase_delay()
                    continue
                else:
                    logger.warning(f"HTTP {response.status} for {url}, attempt {attempt + 1}/{max_retries}")

        except asyncio.TimeoutError:
            logger.warning(f"Timeout for {url}, attempt {attempt + 1}/{max_retries}")
        except Exception as e:
            logger.error(f"Request error for {url}: {e}, attempt {attempt + 1}/{max_retries}")

        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    logger.error(f"Failed to fetch data from {url} after {max_retries} attempts")
    return None

async def fetch_friends_ids(session: aiohttp.ClientSession, user_id: str) -> List[str]:
    """Fetch all friend IDs for a user."""
    logger.info("Fetching friends for user ID")
    all_friend_ids = []
    cursor = ""
    rate_limiter = RateLimiter()
    fetch_count = 0

    while True:
        url = f"https://friends.roblox.com/v1/users/{user_id}/friends/find?limit={FRIENDS_LIMIT}&cursor={cursor}&userSort="

        data = await make_request_with_retry(session, url, rate_limiter)
        if not data:
            logger.error("Failed to fetch friends data")
            raise SystemExit(f"Cannot fetch friends for user {user_id}")

        page_items = data.get("PageItems", [])
        all_friend_ids.extend([str(friend["id"]) for friend in page_items])
        fetch_count += 1

        if SHOW_PROGRESS_INFO and PROGRESS_INFO_EVERY > 0 and fetch_count % PROGRESS_INFO_EVERY == 0:
            logger.info(f"Fetched {len(all_friend_ids)} friend IDs so far...")

        next_cursor = data.get("NextCursor")
        if not next_cursor:
            break
        cursor = next_cursor

    logger.info(f"Fetched total {len(all_friend_ids)} friend IDs.")
    return all_friend_ids

async def fetch_followers_or_followings_ids(session: aiohttp.ClientSession,
                                           user_id: str, endpoint: str) -> List[str]:
    """Fetch all follower/following IDs for a user."""
    logger.info(f"Fetching {endpoint} for user ID")
    all_ids = []
    cursor = None
    rate_limiter = RateLimiter()
    fetch_count = 0

    while True:
        url = f"https://friends.roblox.com/v1/users/{user_id}/{endpoint}?limit={FOLLOWERS_FOLLOWINGS_LIMIT}&sortOrder=Asc"
        if cursor:
            url += f"&cursor={cursor}"

        data = await make_request_with_retry(session, url, rate_limiter)
        if not data:
            logger.error(f"Failed to fetch {endpoint} data")
            raise SystemExit(f"Cannot fetch {endpoint} for user {user_id}")

        ids = [str(user["id"]) for user in data.get("data", [])]
        all_ids.extend(ids)
        fetch_count += 1

        if SHOW_PROGRESS_INFO and PROGRESS_INFO_EVERY > 0 and fetch_count % PROGRESS_INFO_EVERY == 0:
            logger.info(f"Fetched {len(all_ids)} {endpoint} IDs so far...")

        cursor = data.get("nextPageCursor")
        if not cursor:
            break

    logger.info(f"Fetched total {len(all_ids)} {endpoint} IDs.")
    return all_ids

async def fetch_all_user_ids(session: aiohttp.ClientSession, settings: Dict) -> List[str]:
    """Fetch all user IDs based on relationship type."""
    endpoint = settings["relationship_type_endpoint"]
    user_id = settings["target_user_id"]

    if endpoint == "friends":
        return await fetch_friends_ids(session, user_id)
    else:
        return await fetch_followers_or_followings_ids(session, user_id, endpoint)

async def fetch_usernames_batch(session: aiohttp.ClientSession, user_ids: List[str]) -> Dict[str, str]:
    """Fetch usernames for user IDs in batches."""
    url = 'https://apis.roblox.com/user-profile-api/v1/user/profiles/get-profiles'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    usernames = {}
    rate_limiter = RateLimiter()
    chunks = chunk_data(user_ids, USERNAME_BATCH_LIMIT)

    for i, chunk in enumerate(chunks):
        data = {
            "fields": ["names.username"],
            "userIds": chunk
        }

        try:
            await rate_limiter.wait()

            async with session.post(url, headers=headers, json=data,
                                  timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as response:
                if response.status == 200:
                    response_data = await response.json()
                    for user_data in response_data.get('profileDetails', []):
                        user_id = str(user_data.get('userId'))
                        username = user_data.get('names', {}).get('username', None)
                        if user_id and username:
                            usernames[user_id] = username
                        else:
                            logger.warning(f"User ID {user_id} has unknown username")
                    rate_limiter.reset_delay()
                else:
                    logger.error(f"Username API error: {response.status}")
                    rate_limiter.increase_delay()

        except Exception as e:
            logger.error(f"Error fetching usernames for chunk {i}: {e}")

        if SHOW_PROGRESS_INFO and PROGRESS_INFO_EVERY > 0 and (i + 1) % PROGRESS_INFO_EVERY == 0:
            logger.info(f"Fetched usernames for {len(usernames)}/{len(user_ids)} user IDs so far...")

    logger.info(f"Fetched usernames for {len(usernames)}/{len(user_ids)} user IDs.")
    return usernames

async def fetch_avatars_batch(session: aiohttp.ClientSession, user_ids: List[str]) -> Dict[str, Dict[str, str]]:
    """Fetch avatar and headshot URLs for user IDs."""
    logger.info("Fetching avatars and headshots")
    results = {}
    rate_limiter = RateLimiter()
    chunks = chunk_data(user_ids, AVATAR_BATCH_LIMIT)

    for i, chunk in enumerate(chunks):
        ids_str = ",".join(chunk)
        avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={ids_str}&size={AVATAR_SIZE}&format=Png&isCircular=false"
        headshot_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={ids_str}&size={AVATAR_HEADSHOT_SIZE}&format=Png&isCircular=false"

        # Fetch both avatar and headshot concurrently
        tasks = [
            make_request_with_retry(session, avatar_url, rate_limiter),
            make_request_with_retry(session, headshot_url, rate_limiter)
        ]

        avatar_data, headshot_data = await asyncio.gather(*tasks)

        if avatar_data:
            for entry in avatar_data.get("data", []):
                user_id = str(entry.get("targetId"))
                results.setdefault(user_id, {})["avatar_url"] = entry.get("imageUrl")

        if headshot_data:
            for entry in headshot_data.get("data", []):
                user_id = str(entry.get("targetId"))
                results.setdefault(user_id, {})["headshot_url"] = entry.get("imageUrl")

        if SHOW_PROGRESS_INFO and PROGRESS_INFO_EVERY > 0 and (i + 1) % PROGRESS_INFO_EVERY == 0:
            logger.info(f"Fetched avatars/headshots for {len(results)}/{len(user_ids)} user IDs so far...")

    logger.info(f"Fetched avatars and headshots for {len(results)}/{len(user_ids)} user IDs.")
    return results

# --- Webhook Processing ---
def process_webhooks(settings: Dict, user_data_chunks: List[List[Dict]], webhook_type: str) -> None:
    """Process webhook sending with better error handling."""
    if not user_data_chunks:
        return

    webhook_count = 0
    total_webhooks = len(user_data_chunks) * (
        int(settings["send_discord_log"]) + int(settings["send_guilded_log"])
    )

    for chunk in user_data_chunks:
        for platform, enabled in [("discord", settings["send_discord_log"]),
                                 ("guilded", settings["send_guilded_log"])]:
            if enabled:
                try:
                    send_embed_group(
                        platform,
                        settings[f"{platform}_webhook_url"],
                        settings["relationship_type_endpoint"],
                        chunk,
                        APP_VERSION
                    )
                    webhook_count += 1

                    if webhook_count % 5 == 0 or webhook_count == total_webhooks:
                        logger.info(f"Sent {webhook_count}/{total_webhooks} {webhook_type} webhooks")

                except Exception as e:
                    logger.error(f"Failed to send {platform} webhook: {e}")

        if settings["embed_wait_HTTP"] > 0:
            time.sleep(settings["embed_wait_HTTP"])

def prepare_embed_data(user_ids: List[str], usernames: Dict[str, str],
                      avatars: Dict[str, Dict], is_removed: bool, total_count: int) -> List[Dict]:
    """Prepare embed data for webhooks."""
    embed_data_list = []
    for user_id in user_ids:
        embed_data = {
            "username": usernames.get(user_id, "Unknown"),
            "user_id": user_id,
            "avatar_url": avatars.get(user_id, {}).get("avatar_url"),
            "headshot_url": avatars.get(user_id, {}).get("headshot_url"),
            "removed": is_removed,
            "total_count": total_count
        }
        embed_data_list.append(embed_data)
    return embed_data_list

# --- Main Logic ---
async def run_tracker() -> None:
    """Main async function to run the tracker."""
    settings = load_settings()
    validate_settings(settings)

    # Ensure required files exist
    ensure_files_exist([
        settings["last_run_time_file"],
        settings["local_data_file"]
    ])

    if SHOW_LOADED_SETTINGS:
        logger.info("=== Configuration ===")
        logger.info(f"Discord: {'✓' if settings['send_discord_log'] else '✗'} | "
                   f"Guilded: {'✓' if settings['send_guilded_log'] else '✗'}")
        logger.info(f"Tracking: {settings['relationship_type_endpoint']}")
        logger.info(f"New entries: {'✓' if settings['send_new_entries'] else '✗'} | "
                   f"Removed entries: {'✓' if settings['send_removed_entries'] else '✗'}")

    # Create session with connection limits
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS, limit_per_host=5)

    async with aiohttp.ClientSession(connector=connector) as session:
        # Fetch current user data
        logger.info("Starting data collection...")
        current_user_ids = await fetch_all_user_ids(session, settings)
        logger.info(f"Found {len(current_user_ids)} current users")

        # Load previous data
        previous_user_ids = set(read_from_file(settings["local_data_file"]))
        current_user_set = set(current_user_ids)

        # Calculate changes
        new_user_ids = [uid for uid in current_user_ids if uid not in previous_user_ids]
        removed_user_ids = [uid for uid in previous_user_ids if uid not in current_user_set]

        logger.info(f"Changes detected - New: {len(new_user_ids)}, Removed: {len(removed_user_ids)}")

        # Only fetch additional data if we need to send webhooks
        need_webhooks = (
            (settings["send_new_entries"] and new_user_ids) or
            (settings["send_removed_entries"] and removed_user_ids)
        ) and (settings["send_discord_log"] or settings["send_guilded_log"])

        if need_webhooks:
            # Fetch usernames and avatars for changed users
            ids_to_fetch = list(set(new_user_ids + removed_user_ids))
            logger.info(f"Fetching additional data for {len(ids_to_fetch)} users...")

            usernames, avatars = await asyncio.gather(
                fetch_usernames_batch(session, ids_to_fetch),
                fetch_avatars_batch(session, ids_to_fetch)
            )

            # Process new entries
            if settings["send_new_entries"] and new_user_ids:
                logger.info(f"Processing {len(new_user_ids)} new entries...")
                new_chunks = chunk_data(new_user_ids, 10)
                new_embed_chunks = [
                    prepare_embed_data(chunk, usernames, avatars, False, len(current_user_ids))
                    for chunk in new_chunks
                ]
                process_webhooks(settings, new_embed_chunks, "new")

            # Process removed entries
            if settings["send_removed_entries"] and removed_user_ids:
                logger.info(f"Processing {len(removed_user_ids)} removed entries...")
                removed_chunks = chunk_data(removed_user_ids, 10)
                removed_embed_chunks = [
                    prepare_embed_data(chunk, usernames, avatars, True, len(current_user_ids))
                    for chunk in removed_chunks
                ]
                process_webhooks(settings, removed_embed_chunks, "removed")

        else:
            logger.info("No webhooks needed or webhooks disabled")

        # Update local data file
        if previous_user_ids != current_user_set:
            logger.info("Updating local data file...")
            if write_to_file(settings["local_data_file"], current_user_ids):
                logger.info("Local data updated successfully")
            else:
                logger.error("Failed to update local data file")
        else:
            logger.info("No changes detected, skipping data file update")

        # Update last run time
        write_last_run_time(settings["last_run_time_file"])
        logger.info("Tracker run completed successfully")

def main():
    """Main synchronous entry point."""
    try:
        asyncio.run(run_tracker())
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise SystemExit("Script failed due to unexpected error") from e

if __name__ == "__main__":
    main()
