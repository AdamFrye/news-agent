import os

from .llm import chatWithModel
from .fetcher import getArticleText


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


def summarizeArticles(config, articles):
    """Render the selected articles into one document and summarize it."""
    token = os.environ.get('OPENWEBUI_TOKEN')

    blocks = [
        f'## {article.title}\nURL: {article.url}\n\n{getArticleText(article)}'
        for article in articles
    ]
    numArticles = len(articles)
    summaries = []
    for i, block in enumerate(blocks, start=1):
        print(f'Summarizing article: {i}/{numArticles}')
        summaries.append(chatWithModel(
            config['openWebUiBaseUrl'], token,
            config['summaryModel'], block, config['summaryPrompt'],
        ))
    return '\n\n---\n\n'.join(summaries)
