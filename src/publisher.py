import os
from datetime import datetime

from git import Repo

# Fixed in-container working copy of the news repo. Mount a volume here to
# persist it across restarts; otherwise it lives for the container's lifetime.
NEWS_REPO_PATH = '/data/news'


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
    if not repo.git.status('--porcelain'):
        print(f'{filename} unchanged; nothing to commit.')
        return
    repo.git.commit('-m', f'News summary {today}')
    repo.git.push('origin', 'HEAD')
