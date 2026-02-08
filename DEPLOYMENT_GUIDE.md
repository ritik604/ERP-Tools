# MVP Deployment Options for Free Testing

## Option 1: Ngrok (Fastest, Temporary)
Use this if you want to quickly show the app to someone right now, running from your own computer.

### Steps:
1.  **Download Ngrok**: Go to [ngrok.com](https://ngrok.com/download) and download for Windows.
2.  **Unzip and Authenticate**:
    -   Unzip the file.
    -   Sign up on ngrok.com to get your **Auth Token**.
    -   Run: `ngrok config add-authtoken YOUR_TOKEN` in terminal.
3.  **Start Your Django Server**:
    -   Open a terminal in your project folder.
    -   Run: `.\venv\Scripts\activate` (if not active).
    -   Run: `python manage.py runserver`
4.  **Start Ngrok Tunnel**:
    -   Open a **new** terminal window.
    -   Run: `ngrok http 8000`
5.  **Share the Link**:
    -   Copy the `https://....ngrok-free.app` URL shown in the terminal.
    -   Send this link to your testers.

**Note**: The app stops working when you close the terminal or turn off your computer.

---

## Option 2: PythonAnywhere (Persistent, 24/7)
Use this if you want the app to be available online constantly without your computer running.

### Steps:
1.  **Sign Up**: Go to [pythonanywhere.com](https://www.pythonanywhere.com/) and create a free account.
2.  **Upload Code**:
    -   Zip your entire project folder (excluding `venv` and `__pycache__`).
    -   Go to the PythonAnywhere **Files** tab and upload the zip.
    -   Unzip it using the **Bash Console**: `unzip your_project.zip`.
3.  **Install Dependencies**:
    -   In the Bash Console on PythonAnywhere:
        ```bash
        mkvirtualenv --python=/usr/bin/python3.10 myenv
        pip install -r requirements.txt
        ```
4.  **Configure Web App**:
    -   Go to the **Web** tab.
    -   Click **Add a new web app**.
    -   Choose **Manual Configuration** -> **Python 3.10**.
    -   **Virtualenv section**: Enter the path to your virtualenv (e.g., `/home/yourusername/.virtualenvs/myenv`).
    -   **Code section**:
        -   Source code: `/home/yourusername/path_to_project`
        -   Working directory: `/home/yourusername/path_to_project`
    -   **WSGI Configuration**:
        -   Click the link to edit the WSGI file.
        -   Comment out the "Hello World" part.
        -   Uncomment the Django section and update the path/settings:
            ```python
            import os
            import sys
            path = '/home/yourusername/path_to_project'
            if path not in sys.path:
                sys.path.append(path)
            os.environ['DJANGO_SETTINGS_MODULE'] = 'construction_erp.settings'
            from django.core.wsgi import get_wsgi_application
            application = get_wsgi_application()
            ```
5.  **Static Files**:
    -   In the **Web** tab, under **Static Files**:
        -   URL: `/static/`
        -   Path: `/home/yourusername/path_to_project/staticfiles`
    -   Run `python manage.py collectstatic` in the Bash Console first.
6.  **Reload**:
    -   Click the big green **Reload** button in the Web tab.
    -   Visit your site at `yourusername.pythonanywhere.com`.

## Configuration Changes Made
I have already updated your `settings.py` to be compatible with both options:
-   `ALLOWED_HOSTS` now accepts `*` (any domain) or `.ngrok-free.app`/`.pythonanywhere.com`.
-   `CSRF_TRUSTED_ORIGINS` includes Ngrok and PythonAnywhere domains.
-   `STATIC_ROOT` is configured for `collectstatic`.
-   `requirements.txt` is created with all detected dependencies.
