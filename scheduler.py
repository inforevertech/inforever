import schedule
import time
import sys
import logging
from logging.config import dictConfig
from scrape_blockchain import BlockchainScraper
import asyncio
from db import db_latest_block_height


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
    logging.info('PROCESS: Collecting OP_RETURN statements from BTC block ' + str(collectorBTC.get_height()) + ' out of ' + str(collectorBTC.get_max_height()))
    try:
        collectorBTC.collect_block()
    except Exception as e:
        logging.info(e.msg)

    logging.info('PROCESS: Collecting OP_RETURN statements from BTC-test block ' + str(collectorBTCTest.get_height()) + ' out of ' + str(collectorBTCTest.get_max_height()))
    try:
        collectorBTCTest.collect_block()
    except Exception as e:
        logging.info(e.msg)


schedule.every().seconds.do(blockchain_scraping)


if __name__ == '__main__':
    # start scraping from specified block height
    latest_btc_height, latest_btc_test_height = asyncio.run(db_latest_block_height())
    
    collectorBTC.set_height(latest_btc_height)  # start from the block of this height in the blockchain
    collectorBTCTest.set_height(latest_btc_test_height)  # start from the block of this height in the blockchain

    # start scheduled work
    while True:
        schedule.run_pending()

        if collectorBTC.get_height() >= collectorBTC.get_max_height():
            logging.info('PROCESS: Waiting for new blocks in BTC blockchain...')
            time.sleep(20)
        else:
            time.sleep(1)
