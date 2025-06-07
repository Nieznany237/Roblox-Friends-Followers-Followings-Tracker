# pylint: disable=C0301 # Line too long
'''This script sends embed messages to Discord or Guilded webhooks based on user relationships on Roblox.'''
from datetime import datetime
import requests

# Default icon URL used when no avatar or headshot URL is provided
DEFAULT_ICON_URL = "https://github.com/Nieznany237/-Public_Images/blob/main/Roblox/RobloxDeletedContent.png?raw=true"

# Common colors for embed messages
COLOR_REMOVED = 16711680  # Red color for removal
COLOR_NEW = 2330091       # Green color for new entries

# Function to send an embed message to Discord or Guilded webhook
def send_embed_group(platform, webhook_url, relationship_type_endpoint, embed_data_list, version):
    '''Sends an embed message to a specified webhook URL based on user relationship data.
    Args:
        platform (str): The platform for which the webhook is being sent (e.g., 'discord', 'guilded').
        webhook_url (str): The URL of the webhook to send the embed to.
        relationship_type_endpoint (str): The type of relationship endpoint (e.g., 'friends', 'followers', 'followings').
        embed_data_list (list): A list of dictionaries containing user data for the embeds.
        version (str): The version of the script being used.
    '''
    embeds = []

    if not embed_data_list:
        print("No data to send.")
        return  # Prevention of sending an empty message

    for data in embed_data_list:
        username = data.get("username") or "Unknown User"
        user_id = data.get("user_id")
        avatar_url = data.get("avatar_url") or DEFAULT_ICON_URL
        headshot_url = data.get("headshot_url") or DEFAULT_ICON_URL
        removed = data.get("removed")
        total_count = data.get("total_count")

        description = ""  # Initializing the description
        title = None
        color = None

        # Embed creation logic based on relationship type
        if relationship_type_endpoint == 'friends':
            if removed:
                title = "Friend Removed"
                description = f"You and [{username}](https://roblox.com/users/{user_id}/profile) are no longer friends."
                color = COLOR_REMOVED
            else:
                title = "New Friend"
                description = f"You became friends with [{username}](https://roblox.com/users/{user_id}/profile)."
                color = COLOR_NEW

        elif relationship_type_endpoint == 'followers':
            if removed:
                title = "Lost a Follower"
                description = f"[{username}](https://roblox.com/users/{user_id}/profile) has unfollowed you."
                color = COLOR_REMOVED
            else:
                title = "New Follower"
                description = f"[{username}](https://roblox.com/users/{user_id}/profile) is now following you."
                color = COLOR_NEW

        elif relationship_type_endpoint == 'followings':
            if removed:
                title = "Unfollowed a User"
                description = f"You stopped following [{username}](https://roblox.com/users/{user_id}/profile)."
                color = COLOR_REMOVED
            else:
                title = "Now Following"
                description = f"You started following [{username}](https://roblox.com/users/{user_id}/profile)."
                color = COLOR_NEW

        # Checking if the `description`, `title`, or `color` is empty
        if not description or not title or color is None:
            print(f"No description/title/color generated for user {username} - Skipping this entry.")
            continue  # If no description, skip this embed

        description += f"\nYou currently have: {total_count}"  # Adding additional information

        # Create embed
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "footer": {
                "text": f"Automatic script - Version {version} | {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            },
            "author": {
                "name": f"{username} [{user_id}]",
                "url": f"https://www.roblox.com/users/{user_id}/profile",
                "icon_url": headshot_url
            },
            "thumbnail": {
                "url": avatar_url
            }
        }
        embeds.append(embed)

    # Checking to see if any embeds have been generated
    if not embeds:
        print("No embeds generated. Skipping webhook send.")
        return  # Do not send if no embeds have been generated

    payload = {
        "embeds": embeds
    }

    headers = {
        "Content-Type": "application/json"
    }

    # Sending a webhook
    response = requests.post(webhook_url, json=payload, headers=headers, timeout=15)

    # Check the response status code to determine success or failure
    if response.status_code in {204, 200}:
        print(f'[{platform.capitalize()}] - OK')
    else:
        print(f'[{platform.capitalize()}] - Error: {response.status_code}, {response.text}')
