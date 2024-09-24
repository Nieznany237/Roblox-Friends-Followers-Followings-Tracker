import requests
from datetime import datetime

# Default icon URL used when no avatar or headshot URL is provided
default_icon_url = "https://github.com/Nieznany237/-Public_Images/blob/main/Roblox/RobloxDeletedContent.png?raw=true"

description = ""  # Initializing a variable
# Function to send an embed message to Discord or Guilded webhook
def send_embed_group(platform, webhook_url, relationship_type_endpoint, embed_data_list, version):
    embeds = []

    if not embed_data_list:
        print("No data to send.")
        return  # Prevention of sending an empty message

    for data in embed_data_list:
        username = data.get("username")
        user_id = data.get("user_id")
        avatar_url = data.get("avatar_url") or default_icon_url
        headshot_url = data.get("headshot_url") or default_icon_url
        removed = data.get("removed")
        total_count = data.get("total_count")

        description = ""  # Initializing the description

        # Logika tworzenia embeda na podstawie relacji
        if relationship_type_endpoint == 'friends':
            if removed:
                title = "Friend removed"
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

        # Checking if the `description` is empty
        if not description:
            print(f"No description generated for user {username} - Skipping this entry.")
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

    # Debugging - Display payload before sending
    #print(f"Sending payload: {payload}")

    # Sending a webhook
    response = requests.post(webhook_url, json=payload, headers=headers)

    # Check the response status code to determine success or failure
    if response.status_code == 204 or response.status_code == 200:
        print(f'[{platform.capitalize()}] - OK')
    else:
        print(f'[{platform.capitalize()}] - Error: {response.status_code}, {response.text}')
