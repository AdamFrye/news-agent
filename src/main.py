import sys
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

from .config import loadConfig
from .service import runService


def main():
    load_dotenv()
    config = loadConfig()

    if len(sys.argv) > 1 and sys.argv[1] == 'trigger':
        runService(config)
        return

    scheduler = BlockingScheduler()
    hour, minute = config['runTime'].split(':')
    scheduler.add_job(
        runService, 'cron', args=[config],
        hour=int(hour), minute=int(minute),
    )

    print(f'News Agent Service started. Waiting for {config["runTime"]}')
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == '__main__':
    main()
