from flask import Flask, render_template, request, redirect
from bit import Key, PrivateKeyTestnet
from bit import exceptions as bitExceptions
from bit.network import get_fee_cached
from db import db_read_transactions
import requests
import datetime
import asyncio


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
    transactions = asyncio.run(db_read_transactions())

    # if nothing found
    if not transactions:
        return 'Nothing was found in the database.'
    
    return render_template('explorer.html', messages=transactions)


if __name__ == '__main__':
    app.run(debug=True)

