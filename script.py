from collections import namedtuple, defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
from freshrss_api import FreshRSSAPI
import trafilatura
import requests
import yaml
import json
import os

# Load environment variables and create API module
load_dotenv()
client = FreshRSSAPI()

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
groupNameToArticlesRelation = defaultdict(list)
for article in client.get_items_from_dates(since=(datetime.now()) - timedelta(days=1)):
    groupNameToArticlesRelation[feedIdsToGroupNameRelation[article.feed_id]].append(article)

def chatWithModel(url, token, model, content, systemPrompt = None):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    messages = []
    if (systemPrompt):
        messages.append({'role': 'system', 'content': systemPrompt})
    messages.append({'role': 'user', 'content': content})

    data = {
        'model': model,
        'messages': messages,
        'stream': False
    }
    response = requests.post(url + '/api/chat/completions', headers=headers, json=data)
    response.raise_for_status()

    # Some Open WebUI models ignore "stream": false and return a Server-Sent
    # Events stream anyway, so handle both a single JSON body and an SSE stream.
    contentType = response.headers.get('Content-Type', '')
    if 'text/event-stream' in contentType or response.text.lstrip().startswith('data:'):
        parts = []
        for line in response.text.splitlines():
            line = line.strip()
            if not line.startswith('data:'):
                continue
            payload = line[len('data:'):].strip()
            if payload == '[DONE]':
                break
            chunk = json.loads(payload)
            delta = chunk['choices'][0].get('delta', {})
            if delta.get('content'):
                parts.append(delta['content'])
        return ''.join(parts)

    return response.json()['choices'][0]['message']['content']

# Reading config
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# This block of code relates a feed to its limit
groupNameToLimitRelation = {}
for feed in config['feeds']:
    groupNameToLimitRelation[feed['name']] = feed['limit']

url = config['openWebUiBaseUrl']
model = config['selectorModel']
token = os.environ.get('OPENWEBUI_TOKEN')
responses = []
for groupName, limit in groupNameToLimitRelation.items():
    titleIdTuplets = [(article.title, article.id) for article in groupNameToArticlesRelation[groupName]]
    articleList = ''.join(f' {id}:({title}),' for title, id in titleIdTuplets)
    prompt = f'limit: {limit}, articles:{articleList}'
    responses.append(chatWithModel(url, token, model, prompt, systemPrompt = config['selectorPrompt']))

category: str
articleIdsInt = []
for category in responses:
    if not category: continue
    articleIdsStr = category.split(',')
    for id in articleIdsStr:
        articleIdsInt.append(int(id))
selectedArticles = client.get_items_from_ids(ids = articleIdsInt)

def getArticleText(article):
    # Prefer the full article body scraped from the source. Fall back to the
    # feed's own html (stripped) when scraping fails or returns nothing, so an
    # article is never handed to the model empty.
    downloaded = trafilatura.fetch_url(article.url)
    if downloaded:
        text = trafilatura.extract(downloaded)
        if text and text.strip():
            return text.strip()
    fallback = trafilatura.html2txt(article.html) if article.html else ''
    return fallback.strip()

articleBlocks = []
for art in selectedArticles:
    text = getArticleText(art)
    articleBlocks.append(f'## {art.title}\nURL: {art.url}\n\n{text}')

content = '\n\n---\n\n'.join(articleBlocks)
summary = chatWithModel(url, token, config['summaryModel'], content, config['summaryPrompt'])
print(summary)
