from collections import defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
from freshrss_api import FreshRSSAPI
from chatWithModel import chatWithModel
import os
import trafilatura
import yaml


def loadConfig(path='config.yaml'):
    with open(path, 'r') as file:
        return yaml.safe_load(file)


def buildFeedToGroupMap(client):
    """Map each feed id to the name of the group it belongs to."""
    groups = client.get_groups()
    groupNames = {group['id']: group['title'] for group in groups['groups']}

    feedToGroup = {}
    for feedGroup in groups['feeds_groups']:
        groupName = groupNames[feedGroup['group_id']]
        for feedId in feedGroup['feed_ids'].split(','):
            feedToGroup[int(feedId)] = groupName
    return feedToGroup


def groupArticlesByGroup(client, feedToGroup, since):
    """Bucket recent articles under the group name of their feed."""
    articlesByGroup = defaultdict(list)
    for article in client.get_items_from_dates(since=since):
        articlesByGroup[feedToGroup[article.feed_id]].append(article)
    return articlesByGroup


def selectArticleIds(config, articlesByGroup):
    """Ask the selector model which articles to keep for each group."""
    token = os.environ.get('OPENWEBUI_TOKEN')

    selectedIds = []
    for feed in config['feeds']:
        articles = articlesByGroup[feed['name']]
        articleList = ''.join(f' {a.id}:({a.title}),' for a in articles)
        prompt = f"limit: {feed['limit']}, articles:{articleList}"
        response = chatWithModel(
            config['openWebUiBaseUrl'], token, config['selectorModel'],
            prompt, systemPrompt=config['selectorPrompt'],
        )
        if response:
            selectedIds.extend(int(id) for id in response.split(','))
    return selectedIds


def getArticleText(article):
    """Extract the readable body text of an article, with an HTML fallback."""
    downloaded = trafilatura.fetch_url(article.url)
    if downloaded:
        text = trafilatura.extract(downloaded)
        if text and text.strip():
            return text.strip()
    fallback = trafilatura.html2txt(article.html) if article.html else ''
    return fallback.strip()


def summarizeArticles(config, articles):
    """Render the selected articles into one document and summarize it."""
    blocks = [
        f'## {article.title}\nURL: {article.url}\n\n{getArticleText(article)}'
        for article in articles
    ]
    content = '\n\n---\n\n'.join(blocks)
    return chatWithModel(
        config['openWebUiBaseUrl'], os.environ.get('OPENWEBUI_TOKEN'),
        config['summaryModel'], content, config['summaryPrompt'],
    )


def main():
    load_dotenv()
    config = loadConfig()
    client = FreshRSSAPI()

    feedToGroup = buildFeedToGroupMap(client)
    articlesByGroup = groupArticlesByGroup(
        client, feedToGroup, since=datetime.now() - timedelta(days=1),
    )

    selectedIds = selectArticleIds(config, articlesByGroup)
    selectedArticles = client.get_items_from_ids(ids=selectedIds)

    summary = summarizeArticles(config, selectedArticles)
    print(summary)


if __name__ == '__main__':
    main()
