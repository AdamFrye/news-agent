from collections import defaultdict
from datetime import datetime

import trafilatura


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
        if datetime.fromtimestamp(float(article.created_on_time)) < since:
            continue
        articlesByGroup[feedToGroup[article.feed_id]].append(article)
    return articlesByGroup


def getArticleText(article):
    """Extract the readable body text of an article, with an HTML fallback."""
    downloaded = trafilatura.fetch_url(article.url)
    if downloaded:
        text = trafilatura.extract(downloaded)
        if text and text.strip():
            return text.strip()
    fallback = trafilatura.html2txt(article.html) if article.html else ''
    return fallback.strip()
