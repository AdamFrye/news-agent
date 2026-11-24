from .fetcher import getArticleText
import ollama

def selectArticleIds(config, articlesByGroup):
    client = ollama.Client(host=config.get('ollamaHost', config['ollamaBaseUrl']))
    selectedIds = []

    for feed in config['feeds']:
        articles = articlesByGroup.get(feed['name']) or []
        if len(articles) <= feed['limit']:
            selectedIds.extend(a.id for a in articles)
            continue

        rankedArticles = []
        for article in articles:
            response = client.systemone(
                model=config['selectorModel'],
                state=article.title,
                questions={
                    'interest': {
                        'type': 'score',
                        'instructions': 'Rate how interesting this article might be to a curious general reader, based on the headline alone.',
                        'criteria': [
                            "Dull",
                            "Very low interest",
                            "Low interest",
                            "Below average interest",
                            "Average interest",
                            "Above average interest",
                            "Interesting",
                            "Very interesting",
                            "Fascinating",
                            "Exceptional",
                        ]
                    }
                }
            )
            rankedArticles.append({"id": article.id, "rank": response.answers['interest'].score})
        rankedArticles = sorted(rankedArticles, key=lambda item: item["rank"], reverse=True)
        selectedIds.extend(r["id"] for r in rankedArticles[:feed['limit']])

    return selectedIds


def summarizeArticles(config, articles):
    """Render the selected articles into one document and summarize it."""
    client = ollama.Client(host=config.get('ollamaHost', config['ollamaBaseUrl']))

    blocks = [
        f'## {article.title}\nURL: {article.url}\n\n{getArticleText(article)}'
        for article in articles
    ]
    numArticles = len(articles)
    summaries = []
    for i, block in enumerate(blocks, start=1):
        print(f'Summarizing article: {i}/{numArticles}')
        response = client.chat(
            model=config['summaryModel'],
            messages=[
                {'role': 'system', 'content': config['summaryPrompt']},
                {'role': 'user', 'content': block},
            ],
        )
        summaries.append(response.message.content)

    return '\n\n---\n\n'.join(summaries)
