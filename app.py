from flask import Flask, render_template, request, redirect
from bit import Key, PrivateKeyTestnet
from bit import exceptions as bitExceptions
from bit.network import get_fee_cached
import requests
import datetime


app = Flask(__name__)


# main page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # If submit button is pressed get the values from the form: messsage, private key and transaction fee.
        message = request.form['message']
        private_key = request.form['private']
        fee = int(request.form['fee'])

        # Create a key object from the private key.
        key = PrivateKeyTestnet(private_key)

        try:
            # Send a transaction to the bitcoin network with the message as the data. Using op_return.
            transaction_id = key.send([], fee=fee, absolute_fee=True, message=message)
        except bitExceptions.InsufficientFunds as e:
            # form insufficient funds description
            errorContent = ["Error message: " + str(e),
                            "Use the following faucet to get testnet satoshis: https://testnet-faucet.com/btc-testnet/"]
            
            # return page with insufficient funds information
            return render_template('error.html',
                                   errorTitle="Insufficient Funds",
                                   address=key.address,
                                   errorContent=errorContent)
        except:
            # return page with error description
            return render_template('error.html',
                                   errorTitle="Error occured",
                                   address=key.address,
                                   errorContent=["Error message: " + str(e)])

        return redirect("/tr/" + transaction_id)

    return render_template('index.html',
                           recommende_fee=get_fee_cached())


# transaction explorer page
@app.route('/tr/<transaction_id>', methods=['GET', 'POST'])
def transaction(transaction_id):
    transaction_url = request.base_url  # current page url
    blockchain_url = "https://live.blockcypher.com/btc-testnet/tx/" + transaction_id + "/"
    transaction_data = requests.get("https://blockstream.info/testnet/api/tx/" + transaction_id)
    post_date = ""
    status_code = transaction_data.status_code

    if status_code == 200:
        # form success response with decryped OP_RETURN data
        transaction_data = transaction_data.json()

        # get posted datetime
        try:
            post_date = datetime.datetime.fromtimestamp(transaction_data.get('status').get('block_time')).strftime("%-I:%M %p on %A, %B %-d, %Y")
        except:
            post_date = ""

        # form output message
        outputs = []
        for line in transaction_data.get('vout'):
            if line['scriptpubkey_type'] == 'op_return':  # process only op_return statements
                # decode hex to utf-8
                hex_value = line['scriptpubkey'][4:]
                utf8_value = bytes.fromhex(hex_value).decode("utf-8")
                outputs.append(utf8_value)

        transaction_data = '\n'.join(outputs)

    elif status_code == 404:
        # form transaction not ready or not existent response
        transaction_data = "Still waiting for acceptance into mempool or not existent."
    else:
        # form generic status code response
        transaction_data = "Transaction explorer response code: " + str(transaction_data.status_code)

    return render_template('transaction.html',
                           transactionId=transaction_id,
                           transactionUrl=transaction_url,
                           transactionData=transaction_data,
                           postDate=post_date,
                           blockchainUrl=blockchain_url,
                           statusCode=status_code)


# blockchain messages explorer page
@app.route('/explorer', methods=['GET', 'POST'])
def explorer():
    outputs = []
    messageCounter = 0

    # latest block on the blockchain
    height_of_latest_block = int(requests.get('https://blockstream.info/testnet/api/blocks/tip/height').text)

    while messageCounter < 10:
        # find current block hash
        current_block = requests.get('https://blockstream.info/testnet/api/block-height/' + str(height_of_latest_block)).text

        # get up to 25 transactions in the current block
        transactions = requests.get('https://blockstream.info/testnet/api/block/' + str(current_block) + '/txs')

        # find transactions with op_return statements
        transactions = transactions.json()
        for tr in transactions:
            for line in tr.get('vout'):
                if line['scriptpubkey_type'] == 'op_return':  # process only op_return statements
                    try:
                        # decode hex to utf-8
                        hex_value = line['scriptpubkey'][4:]
                        utf8_value = bytes.fromhex(hex_value).decode("utf-8")
                        outputs.append(utf8_value + '<br>' + line['scriptpubkey_asm'])
                        messageCounter += 1
                    except:
                        # just ignore op_returns in alternative formats
                        continue
        
        # decrease height to find previous messages/transactions
        height_of_latest_block -= 1

    # if nothing found
    if not outputs:
        return 'nothing was found'
    
    return '<br><br>'.join(outputs)


if __name__ == '__main__':
    app.run(debug=True)

