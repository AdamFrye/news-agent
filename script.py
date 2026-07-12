from apscheduler.schedulers.blocking import BlockingScheduler
from chatWithModel import chatWithModel
from collections import defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
from freshrss_api import FreshRSSAPI
from git import Repo
import argparse
import os
import sys
import trafilatura
import yaml


# Fixed in-container working copy of the news repo. Mount a volume here to
# persist it across restarts; otherwise it lives for the container's lifetime.
NEWS_REPO_PATH = '/data/news'


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


def syncRepo(config):
    """Ensure the news repo working copy exists and is up to date.

    On first run the mounted volume is empty, so we clone into it. On every
    later run (including after a container restart) the clone already lives on
    the volume, so we just pull to avoid diverging from the remote.
    """
    pat = os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN')
    authenticatedUrl = config['gitHubNewsRepoUrl'].replace(
        'https://', f'https://{pat}@',
    )
    workdir = NEWS_REPO_PATH

    if os.path.isdir(os.path.join(workdir, '.git')):
        repo = Repo(workdir)
        repo.remotes.origin.set_url(authenticatedUrl)
        repo.remotes.origin.pull()
    else:
        os.makedirs(workdir, exist_ok=True)
        repo = Repo.clone_from(authenticatedUrl, workdir)

    # a fresh container has no git identity — set one so commits succeed
    repo.git.config('user.email', 'agent@news-agent')
    repo.git.config('user.name', 'News Agent')
    return repo, workdir


def publishSummary(config, summary):
    """Write the summary into the synced repo, then commit and push it."""
    repo, workdir = syncRepo(config)

    today = datetime.now().strftime('%Y-%m-%d')
    filename = f'{today}.md'
    with open(os.path.join(workdir, filename), 'w') as file:
        file.write(f'# News Summary — {today}\n\n{summary}\n')

    repo.git.add(filename)
    repo.git.commit('-m', f'News summary {today}')
    repo.git.push('origin', 'HEAD')


def runService(config):
    start = datetime.now()
    load_dotenv()
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

    publishSummary(config, summary)
    print(f'Summarized and Pushed in {datetime.now() - start}')


def main():
    config = loadConfig()

    if len(sys.argv) > 1 and sys.argv[1] == 'trigger':
        runService(config)
        return
    
    scheduler = BlockingScheduler()
    time = config['runTime'].split(':')
    scheduler.add_job(runService, 'cron', args=[config], hour=int(time[0]), minute=int(time[1]))

    print(f"News Agent Service started. Waiting for {config['runTime']}")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == '__main__':
    main()
