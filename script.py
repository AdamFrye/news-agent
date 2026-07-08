from collections import namedtuple, defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
from freshrss_api import FreshRSSAPI
import yaml

# Load environment variables and create API module
load_dotenv()
client = FreshRSSAPI()

# Reading config
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# This block of code relates group ids to its group name
clientGroups = client.get_groups()
groupIdsToGroupNameRelation = {}
for group in clientGroups['groups']:
    groupIdsToGroupNameRelation[group['id']] = group['title']

# This block of code relates feed ids to its group name
feedIdsToGroupNameRelation = {}
for feedGroup in clientGroups['feeds_groups']:
    groupId = feedGroup['group_id']
    for feedId in feedGroup['feed_ids'].split(','):
        feedIdsToGroupNameRelation[int(feedId)] = groupIdsToGroupNameRelation[groupId]

# This block of code relates an article to its group name
articles = defaultdict(list)
for article in client.get_items_from_dates(since=(datetime.now()) - timedelta(days=1)):
    articles[feedIdsToGroupNameRelation[article.feed_id]].append(article)

# Feed the article titles by group into the small llm along with limit. maybe have some sort of fast lookup so that it doesn't have to sort through every single item to get the guy
# Feed those into the big LLM and then feed its response to something. Don't forget feedback.
