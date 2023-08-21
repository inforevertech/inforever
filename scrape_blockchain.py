import requests
import time
import sys
import asyncio
import logging
from db import *
from avatar_generator import generate_avatar_by_address


class BlockchainScraper:
    def __init__(self, height=0, network='btc'):
        self.height = height
        self.network = network
        self.explorer_url = 'https://blockstream.info/' + ('testnet/' if self.network == 'btc-test' else '')

    def set_height(self, height=-1):
        if height == -1:
            self.height = int(requests.get(self.explorer_url + 'api/blocks/tip/height').text) - 10
        else:
            self.height = height
        
    def collection_service(self, past_posts=False, wait_time=100):
        # go through all block starting from the highest
        while self.height >= 0:
            try:
                self.collect_block(past_posts=past_posts)
            except Exception as e:
                logging.info(str(self.height) + ': ' + str(e))
            time.sleep(wait_time)
        
    def collect_block(self, past_posts=False):
        # find current block hash
        current_block = requests.get(self.explorer_url + 'api/block-height/' + str(self.height)).text

        if current_block == 'Block not found':
            logging.info('Block of height ' + str(self.height) + ' was not found.')
            return

        # find total number of transactions in the block
        num_of_transactions = requests.get(self.explorer_url + 'api/block/' + str(current_block)).json().get('tx_count')
        observed_trans_counter = 0

        # go through all transactions in the block
        while observed_trans_counter < num_of_transactions:
            time.sleep(0.1)  # take a pause to prevent 'too many requests' response

            # get up to 25 transactions in the current block
            transactions = requests.get(self.explorer_url + 'api/block/' + str(current_block) + '/txs/' + str(observed_trans_counter))
            transactions = transactions.json()

            observed_trans_counter += len(transactions)

            for tr in transactions:
                # get posted datetime (timestamp)
                post_date = tr.get('status').get('block_time')
                # get transaction hash
                tr_hash = tr.get('txid')
                # get block hash
                block_hash = tr.get('status').get('block_hash')
            
                # get addresses of senders
                addresses = set()
                for line in tr.get('vin'):
                    if line['prevout'] is not None and 'scriptpubkey_address' in line['prevout']:
                        addresses.add((line['prevout']['scriptpubkey_address'], False))
                # get addresses of receivers
                for line in tr.get('vout'):
                    if 'scriptpubkey_address' in line:
                        addresses.add((line['scriptpubkey_address'], True))

                # process only op_return statements
                message = ""
                for line in tr.get('vout'):
                    if line['scriptpubkey_type'] == 'op_return':
                        try:
                            # decode hex to utf-8
                            hex_value = line['scriptpubkey'][4:]
                            utf8_value = bytes.fromhex(hex_value).decode("utf-8")
                            
                            message += utf8_value.strip()
                        except:
                            # just ignore op_returns in alternative formats
                            continue
                
                if message.strip():  # if message is not empty
                    # put data into the database
                    asyncio.run(db_insert_transaction(tr_hash, block_hash, self.height, message, post_date, self.network))

                    addresses = list(addresses)
                    # generate address avatars
                    for address in addresses:
                        generate_avatar_by_address(address[0])

                    # add sender addresses information to the db
                    asyncio.run(db_insert_sent_address(tr_hash, addresses, self.network))
                    
                    logging.info(str(post_date) + ': ' + message)
                else:  # no message found, then just go futher
                    continue

        if past_posts:
            self.height -= 1
        else:
            self.height += 1

        return current_block
            

# starting point
if __name__ == '__main__':
    # set logging level to debug
    logging.basicConfig(level=logging.DEBUG)

    # launch collector of recent posts
    collector = BlockchainScraper(network=sys.argv[1] if len(sys.argv) > 1 else 'btc')
    collector.set_height(height=int(sys.argv[2]) if len(sys.argv) > 2 else -1)  # start from the block of this hight in the blockchain

    if len(sys.argv) > 3 and sys.argv[3] == 'past':
        collector.collection_service(past_posts=True, wait_time=0.01)
    else:
        collector.collection_service(past_posts=False, wait_time=0.01)
