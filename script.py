from freshrss_api import FreshRSSAPI

# Initialize the client with direct parameters
client = FreshRSSAPI(
    host="https://freshrss.example.net",
    username="your_username",
    password="your_api_password",
    verify_ssl=True,
    verbose=False
)