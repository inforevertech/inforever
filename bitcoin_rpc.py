import time
from bitcoin.rpc import RawProxy, InvalidParameterError

# Create a connection to local Bitcoin Core node
p = RawProxy()

# Request latest block height from the database
block_height = int(p.getblockcount()) - 10
print("Latest block height: %d" % block_height)

while True:
    try:
        # Get the list of transactions in the latest block
        latest_block_hash = p.getblockhash(block_height)
        print(block_height, "hash:", latest_block_hash)
        block_height += 1  # increment block height

        latest_block = p.getblock(latest_block_hash)
        txids = latest_block['tx']

        # Go through each transaction in the block to find OP_RETURNs
        for txid in txids:
            raw_tx = p.getrawtransaction(txid, False, latest_block_hash)
            decoded_tx = p.decoderawtransaction(raw_tx)

            addresses_from = []
            for line in decoded_tx['vin']:
                if 'txid' in line:
                    addresses_from.append(line['txid'])

            addresses_to = []
            for line in decoded_tx['vout']:
                if 'scriptPubKey' in line and 'address' in line['scriptPubKey']:
                    addresses_to.append((line['scriptPubKey']['address'], line['value']))

            print(addresses_from, "=>", addresses_to, ", BTC value:", sum([item[1] for item in addresses_to]))


            message = ''
            for line in decoded_tx['vout']:
                if 'scriptPubKey' in line and 'asm' in line['scriptPubKey'] and line['scriptPubKey']['asm'][:10] == 'OP_RETURN ':
                    try:
                        # decode hex to utf-8 plaintext
                        hex_value = line['scriptPubKey']['hex'][4:]
                        utf8_value = bytes.fromhex(hex_value).decode('utf-8')
                        message += utf8_value
                    except:
                        continue

            # remove leading and trailing whitespace
            message = message.strip()
            if message:
                print(message)
                print(decoded_tx)

    except InvalidParameterError as e:
        print(block_height, "InvalidParameterError: %s" % e)
        time.sleep(10)

