# CS2 & Faceit Discord Bot

A custom Discord bot (discord.py) for a gaming community.

---
✨ Core Features & Technologies
---

* **CS2 Server Browser:** Uses the A2S protocol to query live server status, ping, and player count.
* **Faceit API Integration:** Fetches player stats, ELO, daily W/L, and last match stats.
* **Voice Commands:** Joins voice channels to play custom audio clips using FFmpeg & PyNaCl.

---
🤖 Bot Commands
---

* `/mimiajuda`: Opens an interactive menu to find and filter live CS2 servers.
* `/checkmyelo [nickname]`: Shows the general Faceit stats (Elo, K/D, 24h W/L) for a player.
* `/elodorei`: A shortcut command to show the stats for the user "Bichoblamef".
* `/veademo [nickname]`: Shows detailed stats and a link for a player's last played Faceit match.
* `/adoro-te`: The bot joins your voice channel and plays a custom sound (2x).
* `/para`: Makes the bot stop playing audio and leave the voice channel.

---
🚀 How to Run
---

1.  **Install Dependencies:**
    ```bash
    # Install Python libraries
    py -m pip install discord.py a2s aiohttp pynacl python-dotenv
    
    # Install FFmpeg (for voice) - easiest way on Windows:
    winget install "FFmpeg (Essentials Build)"
    ```

2.  **Configure:**
    * Create a `.env` file for your `DISCORD_TOKEN` and `FACEIT_API_KEY`.
    * Edit `servers.json` to add your CS2 server list.
    * Add your audio file (e.g., `adoro-te.mp3`) to the folder.

3.  **Run:**
    ```bash
    py bot.py
    ```

---
👤 Author
---

* CARVALHOCENT