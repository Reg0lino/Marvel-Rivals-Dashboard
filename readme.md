# Marvel Rivals Dashboard - Unofficial Desktop Companion

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- Add other badges if desired, e.g., latest release version -->

An unofficial desktop companion application ecosystem for the game Marvel Rivals, providing fast, offline-first access to character information, game updates, and related data.

**This project is unofficial and not affiliated with Marvel, NetEase Games, or the Marvel Rivals development team.**

---

## Features

*   **Comprehensive Character Data:** View detailed information including Roles, Tiers (Meta), Health, Difficulty, Abilities, Ultimates, Passives, Teamups, Gameplay Strategy, Balance History, Lore, Comic Background, and more.
*   **Offline First:** Access character data quickly without needing a constant internet connection (after initial data retrieval).
*   **Rich Display:**
    *   Visually distinct character cards with theme colors.
    *   Scrollable and zoomable text areas (Ctrl+Scroll or Middle-Click/Ctrl+R to reset zoom).
    *   Collapsible sections for better organization.
    *   Markdown support in info popups (Headings, Lists, Links).
*   **Easy Navigation:**
    *   **Jump Bar:** Quickly navigate to characters using clickable icons.
    *   **Search:** Find characters by name.
    *   **Sort & Filter:** Organize characters by Name, Role, or Favorites; Filter by specific Role.
*   **Favorites System:** Mark your favorite characters for quick access and sorting.
*   **Info Popups:** Access formatted game News, Announcements, Patch Notes, and Developer Diaries directly within the app.
*   **External Links:** Quick links to RivalsTracker, character-specific YouTube guide searches, and Reddit discussions.
*   **Two Update Methods:** Choose the setup that best suits you (see below).
*   **Launcher:** User-friendly entry point with display options (Monitor selection, Windowed/Fullscreen).

---

## Screenshots

<!-- Add screenshots of the Launcher and Dashboard here -->
*   *Launcher Interface*
*   *Main Dashboard View*
*   *Character Card Example*
*   *Info Popup Example*

---

## Getting Started: Choose Your Version

This project offers two ways to get and update data, catering to different user needs:

**Option 1: Simple Sync Version (Recommended for Most Users)**

*   **What it is:** Pre-packaged executables (e.g., `.exe` for Windows) including the Launcher and Dashboard.
*   **Who it's for:** Users who want a simple setup without needing Python installed or managing API keys.
*   **Data Updates:** Uses a built-in "Check for Updates" button within the Dashboard to download official data packs (`characters.zip`) released by the project maintainer on GitHub. Data is only as fresh as the last published release.
*   **Requirements:** Just download the release ZIP and run the Launcher. Requires write permissions to its own installation directory to save favorites and download data updates (installing to Desktop or Documents is recommended over `C:\Program Files`).
*   **Installation:**
    1.  Go to the [**Releases Page**](https://github.com/YOUR_USERNAME/YOUR_REPO/releases) on GitHub. <!-- Replace with your actual link -->
    2.  Download the latest ZIP file labeled something like `MarvelRivalsDashboard_SimpleSync_vX.Y.Z.zip`.
    3.  Extract the ZIP file to a location on your computer (e.g., your Desktop).
    4.  Run `launcher.exe` from the extracted folder.

**Option 2: Full Control Version (Advanced Users)**

*   **What it is:** The full source code, including the `scraper/updater_v3.py` tool.
*   **Who it's for:** Users comfortable with Python, command-line tools, and managing API keys who want the ability to generate the absolute latest data themselves via web scraping and AI processing.
*   **Data Updates:** Requires manually running the `scraper/updater_v3.py` tool. This tool scrapes websites and uses the Google Gemini AI to generate/update the `characters/*.json` files locally. Data freshness depends on when you run the updater and the state of the source websites/AI model.
*   **Requirements:**
    *   Python 3.x installed.
    *   Ability to use `pip` to install dependencies.
    *   A Google AI (Gemini) API Key. See `scraper/SETUP_API_KEY.md` for instructions.
*   **Installation:**
    1.  Clone this repository or download the source code ZIP.
    2.  **Create a virtual environment (Recommended):**
        ```bash
        python -m venv venv
        # Activate (Windows):
        venv\Scripts\activate
        # Activate (macOS/Linux):
        source venv/bin/activate
        ```
    3.  Install dependencies:
        ```bash
        pip install -r requirements.txt
        ```
    4.  **Set up your API Key:**
        *   Navigate to the `scraper` directory.
        *   Rename `.env.template` to `.env`.
        *   Edit the `.env` file and paste your Google AI API Key after `GOOGLE_API_KEY=`.
        *   Follow detailed steps in `scraper/SETUP_API_KEY.md`. **Do not share your `.env` file!**
    5.  Run the application via the launcher:
        ```bash
        python launcher.py
        ```

---

## Usage

1.  **Run `launcher.py` (or `launcher.exe`).**
2.  Select your desired Monitor and Display Mode (Windowed/Fullscreen).
3.  *(Optional)* Check "Start Dashboard in Debug Mode" for detailed console logs (useful for troubleshooting).
4.  Click **"⚡ Launch Dashboard"**.
5.  *(Full Control Version Only)* Click **"⚙️ Launch Updater"** to open the data management tool.

**Dashboard Basics:**

*   Use the **Jump Bar** icons or **Search** bar to find characters.
*   Use the **Sort** and **Filter** dropdowns to organize the view.
*   Click the **Star (☆/★)** on a character card to toggle Favorites.
*   Click buttons in the **Top Bar** (e.g., "News", "Balance Post") to view info popups.
*   Use **Ctrl+Mouse Wheel** inside text areas (like Abilities, Lore) to zoom text. Middle-click or Ctrl+R resets zoom.
*   *(Simple Sync Version Only)* Look for a "Check for Data Updates" button (to be added) to sync with the latest official data pack from GitHub.

---

## Data Sources & AI Usage

*   **Simple Sync Version:** Character data (`characters/*.json`) and info files (`info/*.txt`) are bundled based on the data generated by the maintainer for a specific GitHub Release. Updates occur when the user manually checks and downloads a new `characters.zip` asset from a release.
*   **Full Control Version:** The included Updater tool (`scraper/updater_v3.py`) allows users to regenerate data:
    *   It **scrapes** data from various web sources (official game site, wikis, tracker sites - these can break if site structures change).
    *   It utilizes the **Google Gemini AI** (requiring the user's own API key configured in `scraper/.env`) to process scraped text and generate the structured `characters/*.json` files based on predefined prompts (`scraper/api_prompt_*.txt`).
    *   **AI Reliability:** The accuracy and formatting of the generated JSON data depend on the AI model's performance (e.g., `gemini-1.5-flash` may occasionally produce errors). The Updater includes mechanisms to save failed outputs (`characters/failed/`) for debugging.

---

## Known Issues & Limitations

*   **AI Reliability (Updater Tool):** The AI model can sometimes generate invalid JSON, requiring user intervention (retrying, editing, changing model) in the Updater.
*   **Scraping Fragility (Updater Tool):** Web scraping is inherently brittle. Changes to source website layouts *will* break the Updater's scraping functions, requiring code updates.
*   **Updater Requirements (Full Control Version):** Requires Python installation, `pip install`, and user-provided Google AI API key setup.
*   **Platform Differences:** Minor visual/behavioral differences may occur across Windows/macOS/Linux. Console window hiding during launch is primarily a Windows feature.
*   **Data Latency (Simple Sync Version):** Users only get updates when the maintainer publishes a new data pack to GitHub Releases and the user runs the update check.
*   **Packaging Permissions (Simple Sync Version):** Needs write access to its installation folder (`characters/`, `config/`, AppData) for updates and favorites. Installation to restricted areas (like `C:\Program Files`) may cause issues.

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## Disclaimer

This is an **unofficial fan-made project** and is not endorsed by or affiliated with Marvel, NetEase Games, or the developers of Marvel Rivals in any way. All Marvel characters, names, assets, and related indicia are trademarks of and © Marvel. Game content and materials are trademarks and copyrights of their respective publishers and licensors. Data presented is sourced from publicly available information and AI generation, and may contain inaccuracies. Use at your own discretion.