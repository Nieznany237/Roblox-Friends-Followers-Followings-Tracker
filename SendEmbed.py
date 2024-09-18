import requests
from datetime import datetime

# Default icon URL used when no avatar or headshot URL is provided
default_icon_url = "https://github.com/Nieznany237/-Public_Images/blob/main/Roblox/RobloxDeletedContent.png?raw=true"

# Function to send an embed message to Discord or Guilded webhook
def send_embed(platform, webhook_url, relationship_type_endpoint, username, user_id, avatar_url, headshot_url, version, removed=False, total_count=None):
    # Check and set default icon if avatar_url is None or empty
    if avatar_url is None or not avatar_url:
        avatar_url = default_icon_url
    
    # Check and set default icon if headshot_url is None or empty
    if headshot_url is None or not headshot_url:
        headshot_url = default_icon_url

    # Determine title and description based on the relationship type
    if relationship_type_endpoint == 'friends':
        if removed:
            title = "Friend removedy"
            description = f"[{username}](https://roblox.com/users/{user_id}/profile) is no longer your friend."
            color = 16711680  # Red color for removal
        else:
            title = "New friend"
            description = f"[{username}](https://roblox.com/users/{user_id}/profile) is now your friend."
            color = 2330091  # Green color for new friend

    elif relationship_type_endpoint == 'followers':
        if removed:
            title = "User stopped following you"
            description = f"[{username}](https://roblox.com/users/{user_id}/profile) stopped following you."
            color = 16711680  # Red color for removal
        else:
            title = "New follower"
            description = f"[{username}](https://roblox.com/users/{user_id}/profile) started following you."
            color = 2330091  # Green color for new follower

    elif relationship_type_endpoint == 'followings':
        if removed:
            title = "You are no longer following this user"
            description = f"[{username}](https://roblox.com/users/{user_id}/profile) was removed from your followings."
            color = 16711680  # Red color for removal
        else:
            title = "New followed user"
            description = f"You are now following [{username}](https://roblox.com/users/{user_id}/profile)."
            color = 2330091  # Green color for new following

    # Append total count information if available
    if total_count is not None:
        description += f"\nYou currently have: {total_count}"

    # Create the embed data structure
    embed_data = {
        "embeds": [
            {
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
                },
                "fields": []
            }
        ]
    }

    # Set the request headers for JSON content
    headers = {
        "Content-Type": "application/json"
    }

    # Send the POST request to the webhook URL
    response = requests.post(webhook_url, json=embed_data, headers=headers)
    
    # Check the response status code to determine success or failure
    if response.status_code == 204 or response.status_code == 200:
        print(f'[{platform.capitalize()}] - OK')
    else:
        print(f'[{platform.capitalize()}] - Error: {response.status_code}, {response.text}')