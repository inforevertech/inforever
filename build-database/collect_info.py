import requests
import time
import asyncio
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import db_insert_transaction


# 1. Go through all blocks in the TESTNET blockchain and find all transactions within it.
# 2. Put only OP_RETURN statements and related information into the database.

def collect_transactions():
    # hight of latest block on the blockchain
    global current_height

    # go through all block starting from the highest
    while current_height >= 0:
        try:
            # find current block hash
            current_block = requests.get('https://blockstream.info/testnet/api/block-height/' + str(current_height)).text

            # find total number of transactions in the block
            num_of_transactions = requests.get('https://blockstream.info/testnet/api/block/' + str(current_block)).json().get('tx_count')
            observed_trans_counter = 0
        except:
            print('error.\n')
            time.sleep(10)
            collect_transactions()

        # go through all transactions in the block
        while observed_trans_counter < num_of_transactions:
            time.sleep(0.1)  # take a pause to prevent 'too many requests' response

            try:
                # get up to 25 transactions in the current block
                transactions = requests.get('https://blockstream.info/testnet/api/block/' + str(current_block) + '/txs/' + str(observed_trans_counter))
                transactions = transactions.json()
            except:  # may return 'too many requests' response
                print('error.\n')
                print(transactions.text)
                time.sleep(10)
                collect_transactions()

            observed_trans_counter += len(transactions)

            for tr in transactions:
                # get posted datetime (timestamp)
                post_date = tr.get('status').get('block_time')
                # get transaction hash
                tr_hash = tr.get('txid')
                # get block hash
                block_hash = tr.get('status').get('block_hash')
                # get address sent from
                # TODO: many-to-many relation between Posts and Users

                # process only op_return statements
                message = ""
                for line in tr.get('vout'):
                    if line['scriptpubkey_type'] == 'op_return':
                        try:
                            # decode hex to utf-8
                            hex_value = line['scriptpubkey'][4:]
                            utf8_value = bytes.fromhex(hex_value).decode("utf-8")
                            
                            message += utf8_value
                        except:
                            # just ignore op_returns in alternative formats
                            continue
                
                if message:  # put data into the database
                    asyncio.run(db_insert_transaction(tr_hash, block_hash, message, post_date))
                    print(post_date, ': ', message, sep='')
                else:  # no message found, then just go futher
                    continue
            
        # decrease block height to find previous messages/transactions
        current_height -= 1


# starting point
current_height = int(requests.get('https://blockstream.info/testnet/api/blocks/tip/height').text)
collect_transactions()
