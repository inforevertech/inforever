from app import app
from flask_apscheduler import APScheduler
import logging
from logging.config import dictConfig
from scrape_blockchain import BlockchainScraper


# configure logging to a file
dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            },
            "file": {
                "class": "logging.FileHandler",
                "filename": "scheduler.log",
                "formatter": "default",
            },
        },
        "root": {"level": "INFO", "handlers": ["console", "file"]},
    }
)

# initialize scheduler
scheduler = APScheduler()
scheduler.init_app(app)

# init btc blockchain scraper
collectorBTC = BlockchainScraper(network='btc')
collectorBTC.set_height()  # start from the block of this hight in the blockchain
# init btc-test blockchain scraper
collectorBTCTest = BlockchainScraper(network='btc-test')
collectorBTCTest.set_height()  # start from the block of this hight in the blockchain

# launch interval scraping
@scheduler.task('interval', id='do_blockchain_scraping', seconds=60)
def blockchain_scraping():
    # run one latest block collector for each network
    logging.info('START: Collecting OP_RETURN statements from latest blocks...')
    collectorBTC.collect_block()
    collectorBTCTest.collect_block()
    logging.info('DONE: Collecting OP_RETURN statements from latest blocks...')


if __name__ == '__main__':
    scheduler.start()