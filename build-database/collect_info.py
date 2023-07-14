import requests
import time
import asyncio
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import *
from avatar_generator import generate_avatar_by_address


# 1. Go through all blocks in the TESTNET blockchain and find all transactions within it.
# 2. Put only OP_RETURN statements and related information into the database.

class Collector:
    def __init__(self, height):
        self.height = height
        
    def collection_service(self, past_posts=True, wait_time=100):
        # go through all block starting from the highest
        while self.height >= 0:
            try:
                self.collect_block(past_posts=past_posts)
                self.height += -1 if past_posts else 1
            except Exception as e:
                print(str(self.height), ': ', str(e), sep='')
            time.sleep(wait_time)
        
    def collect_block(self, past_posts=True):
        # find current block hash
        current_block = requests.get('https://blockstream.info/testnet/api/block-height/' + str(self.height)).text

        # find total number of transactions in the block
        num_of_transactions = requests.get('https://blockstream.info/testnet/api/block/' + str(current_block)).json().get('tx_count')
        observed_trans_counter = 0

        # go through all transactions in the block
        while observed_trans_counter < num_of_transactions:
            time.sleep(0.1)  # take a pause to prevent 'too many requests' response

            # get up to 25 transactions in the current block
            transactions = requests.get('https://blockstream.info/testnet/api/block/' + str(current_block) + '/txs/' + str(observed_trans_counter))
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
                
                if message: 
                    # put data into the database
                    asyncio.run(db_insert_transaction(tr_hash, block_hash, message, post_date))

                    addresses = list(addresses)
                    # generate address avatars
                    for address in addresses:
                        generate_avatar_by_address(address[0])

                    # add sender addresses information to the db
                    asyncio.run(db_insert_sent_address(tr_hash, addresses))
                    
                    print(post_date, ': ', message, sep='')
                else:  # no message found, then just go futher
                    continue
            

# starting point
if __name__ == '__main__':
    # height of the highest block in the blockchain
    top_height = int(requests.get('https://blockstream.info/testnet/api/blocks/tip/height').text) - 2
    
    # launch collector of recent posts
    collector = Collector(top_height)
    collector.collection_service(past_posts=False, wait_time=100)
