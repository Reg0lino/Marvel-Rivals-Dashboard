# Setting Up Your Google AI API Key for the Marvel Rivals Updater

The Marvel Rivals Updater tool uses the Google Generative AI (Gemini) API to automatically generate structured character data from scraped web text and apply patch notes. To use the features on the "Generate/Update JSON" and "Fine-Tune JSON" tabs, you need to provide your own Google AI API key.

**IMPORTANT: Prerequisites**

1.  **Python Installation:** You **MUST** have Python installed on your computer to run the `updater_v3.py` script. If you don't have it, download and install it from [python.org](https://www.python.org/) (version 3.9 or higher recommended).
2.  **Required Python Packages:** You also need to install a couple of Python packages. Open your terminal or command prompt, navigate to the `scraper` folder, and run:
    ```bash
    pip install google-generativeai python-dotenv
    ```
    *(Use `pip3` if `pip` is linked to an older Python version)*

**Steps to Set Up Your API Key:**

1.  **Get Your API Key:**
    *   Go to the Google AI Studio website: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
    *   You may need to sign in with your Google account.
    *   Follow the instructions to "Create API key in new project" (or use an existing project).
    *   Google offers a free tier which is usually sufficient for this tool's usage, but be aware of potential usage limits.
    *   Once created, **copy** your API key. It will be a long string of letters and numbers.

2.  **Locate the Template File:**
    *   Inside the `scraper` folder (where `updater_v3.py` is located), you will find a file named `.env.template`.

3.  **Rename the Template File:**
    *   Rename the file from `.env.template` to **`.env`** (remove the `.template` part).
    *   **Note:** Files starting with a dot might be hidden by default in some operating systems. Make sure your file explorer is set to show hidden files if you can't see it.

4.  **Edit the `.env` File:**
    *   Open the newly renamed `.env` file with a simple text editor (like Notepad, TextEdit, or VS Code).
    *   You will see a line like this:
        ```
        GOOGLE_API_KEY=YOUR_API_KEY_HERE
        ```

5.  **Paste Your Key:**
    *   **Delete** the text `YOUR_API_KEY_HERE`.
    *   **Paste** your actual Google AI API key directly after the equals sign (`=`). There should be no spaces around the equals sign. It should look like this (DO NOT use this example key):
        ```
        GOOGLE_API_KEY=AIzaSyBq...YourVeryLongKeyString...fd789a
        ```

6.  **Save the File:**
    *   Save the changes you made to the `.env` file.

7.  **Verification (Optional):**
    *   Run the `updater_v3.py` script (`python updater_v3.py` in the terminal from the `scraper` folder).
    *   Go to the "Generate/Update JSON" tab.
    *   If the "Select AI Model" dropdown successfully populates with models like "gemini-1.5-flash-latest" or "gemini-1.5-pro-latest" after a few seconds, your API key is likely working correctly!
    *   If the dropdown stays empty or shows an error in the status bar/logs about the API key, double-check steps 3-5 (file name, file location, variable name `GOOGLE_API_KEY`, and the pasted key itself).

**SECURITY WARNING:**

*   Treat your `.env` file like a password!
*   **DO NOT** share your `.env` file or your API key with anyone.
*   **DO NOT** commit your `.env` file to Git or upload it to public places like GitHub. The `.gitignore` file (if included) should already be configured to prevent this, but be careful.

---

You should now be able to use the AI-powered features of the Marvel Rivals Updater!