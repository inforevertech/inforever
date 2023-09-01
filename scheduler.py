import schedule
import time
import sys
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


# init btc blockchain scraper
collectorBTC = BlockchainScraper(network='btc')
# init btc-test blockchain scraper
collectorBTCTest = BlockchainScraper(network='btc-test')


# interval scraping
def blockchain_scraping():
    # run one latest block collector for each network
    logging.info('PROCESS: Collecting OP_RETURN statements from BTC block ' + str(collectorBTC.get_height()) + '...')
    collectorBTC.collect_block()

    logging.info('PROCESS: Collecting OP_RETURN statements from BTC-test block ' + str(collectorBTCTest.get_height()) + '...')
    collectorBTCTest.collect_block()


schedule.every().seconds.do(blockchain_scraping)


if __name__ == '__main__':
     # start scraping from specified block height
    collectorBTC.set_height(int(sys.argv[1]) if len(sys.argv) > 1 else -1)  # start from the block of this height in the blockchain
    collectorBTCTest.set_height(int(sys.argv[2]) if len(sys.argv) > 2 else -1)  # start from the block of this height in the blockchain

    # start scheduled work
    while True:
        schedule.run_pending()

        if collectorBTC.get_height() == collectorBTC.get_max_height():
            logging.info('PROCESS: Waiting for new blocks in BTC blockchain...')
            time.sleep(10)
        else:
            time.sleep(0.1)
