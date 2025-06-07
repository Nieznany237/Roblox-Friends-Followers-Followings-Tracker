# Roblox User Relationships Logger

A simple Python tool to track changes in your Roblox account's friends, followers, and followings. Get notified on Discord and/or Guilded when someone is added or removed.

## Features
- **Tracks Friends, Followers, and Followings**
- **Sends Notifications**: Discord and/or Guilded webhooks
- **Works on Windows & Linux**
- **Easy to Set Up & Run Automatically**

## Roblox API Docs
- [Thumbnails API](https://thumbnails.roblox.com/docs/index.html)
- [Friends API](https://friends.roblox.com/docs/index.html)

---

# Quick Setup

1. **Clone or Download the Repository**
   - Download this repo to your computer. All files you need are included.

2. **(Optional) Create a Virtual Environment**
   - Open a terminal in the project folder and run:
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - On Linux/Mac:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependencies**
   - Make sure you have Python 3.11+ installed.
   - Install required packages:
     ```powershell
     pip install -r requirements.txt
     ```
   - Or, if you don't have `requirements.txt`, just:
     ```powershell
     pip install requests
     ```

4. **Configure the Script**
   - Open `config.json` in a text editor.
   - Fill in your details. Example:
     ```json
     {
         "discord_webhook_url": "Your_Discord_URL",
         "guilded_webhook_url": "Your_Guilded_URL",
         "relationshipType": "friends",
         "Your_User_ID": 1,
         "send_discord_log": true,
         "send_guilded_log": true,
         "send_new_entries": true,
         "send_removed_entries": false,
         "embed_wait_HTTP": 1.5
     }
     ```
   - **Fields:**
     - `discord_webhook_url`: Discord webhook for notifications
     - `guilded_webhook_url`: Guilded webhook for notifications
     - `relationshipType`: `friends`, `followers`, or `followings`
     - `Your_User_ID`: Your Roblox user ID
     - `send_discord_log`: Send logs to Discord
     - `send_guilded_log`: Send logs to Guilded
     - `send_new_entries`: Notify about new friends/followers
     - `send_removed_entries`: Notify about removed friends/followers
     - `embed_wait_HTTP`: Wait time between HTTP requests (seconds)

5. **Run the Script**
   - In the terminal, run:
     ```powershell
     python main.py
     ```

6. **(Optional) Schedule Automatic Runs**

  > *Tip: Rename `main.py` to `main.pyw` on Windows to prevent the console window from appearing.*

  - **Windows**: Use Task Scheduler to automate script execution. [Video guide](https://youtu.be/4n2fC97MNac?t=168)
  - **Linux**: Use `cron` jobs to schedule automatic runs.

---

# Examples

![Screenshot 1](./Examples/1.png)
![Screenshot 2](./Examples/2.png)
![Screenshot 3](./Examples/3.png)
![Screenshot 4](./Examples/4.png)
![Screenshot 5](./Examples/5.png)
