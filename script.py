from chatWithModel import chatWithModel
from collections import defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
from freshrss_api import FreshRSSAPI
from git import Repo
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
        if datetime.fromtimestamp(float(article.created_on_time)) < since:
            continue
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


def writeSummary(config, summary):
    """Write the summary to a dated markdown file under .tmp/ in the repo."""
    today = datetime.now().strftime('%Y-%m-%d')
    relativePath = os.path.join('.tmp', f'{today}.md')
    filepath = os.path.join(config['obsidianRepoFilePath'], relativePath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as file:
        file.write(f'# News Summary — {today}\n\n{summary}\n')
    return relativePath


def pushToGitHub(config, filename):
    """Commit the summary file and push it to the news repo on GitHub."""
    pat = os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN')
    authenticatedUrl = config['gitHubNewsRepoUrl'].replace(
        'https://', f'https://{pat}@',
    )
    repo = Repo(config['obsidianRepoFilePath'])

    repo.git.add(filename)
    repo.git.commit('-m', f'News summary {datetime.now():%Y-%m-%d}')

    repo.git.push(authenticatedUrl, 'HEAD')


def main():
    start = datetime.now()
    load_dotenv()
    config = loadConfig()
    client = FreshRSSAPI()

    feedToGroup = buildFeedToGroupMap(client)
    articlesByGroup = groupArticlesByGroup(
        client, feedToGroup, since=(start - timedelta(days=1)),
    )

    selectedIds = selectArticleIds(config, articlesByGroup)
    selectedArticles = client.get_items_from_ids(ids=selectedIds)

    summary = summarizeArticles(config, selectedArticles)
    if not summary:
        print('No summary produced; nothing to push.')
        return

    filename = writeSummary(config, summary)
    pushToGitHub(config, filename)
    print(f'Summarized and Pushed in {datetime.now() - start}')


if __name__ == '__main__':
    main()
