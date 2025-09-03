"""
Breeze API Client Template
--------------------------
Copy this file as `breeze_client.py` and insert your own API credentials.

⚠️ WARNING:
- Do NOT commit your real credentials to GitHub.
- The .gitignore file ensures `scripts/breeze_client.py` is not uploaded.
"""

from breeze_connect import BreezeConnect

def get_breeze():
    # Replace these placeholders with your actual keys
    breeze = BreezeConnect(api_key="YOUR_API_KEY")
    breeze.generate_session(
        api_secret="YOUR_API_SECRET",
        session_token="YOUR_SESSION_TOKEN"
    )
    return breeze

