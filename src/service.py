from datetime import datetime, timedelta

from freshrss_api import FreshRSSAPI

from .fetcher import buildFeedToGroupMap, groupArticlesByGroup
from .processor import selectArticleIds, summarizeArticles
from .publisher import publishSummary


def runService(config):
    """Execute one full fetch → select → summarize → publish cycle."""
    start = datetime.now()

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
    print(f'Summarized and pushed in {datetime.now() - start}')
