from freshrss_api import FreshRSSAPI
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables and create API module
load_dotenv()
client = FreshRSSAPI()

# Get articles from now - one day until current time.
articles = client.get_items_from_dates(since=(datetime.now()) - timedelta(days=1))
print(articles)