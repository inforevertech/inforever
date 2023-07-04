from flask import Flask, render_template, request
from bit import Key, PrivateKeyTestnet
import requests


app = Flask(__name__)


# main page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # If submit button is pressed get the values from the form: messsage and private key.
        message = request.form['message']
        private_key = request.form['private']

        # Create a key object from the private key.
        key = PrivateKeyTestnet(private_key)
        # Send a transaction to the bitcoin network with the message as the data. Using op_return.
        transaction_id = key.send([], message=message)
        transaction_url = "https://live.blockcypher.com/btc-testnet/tx/" + transaction_id + "/"
        transaction_data = requests.get("https://blockstream.info/testnet/api/tx/" + transaction_id)

        return render_template('success.html', transactionId=transaction_id, transactionUrl=transaction_url, transactionData=transaction_data)

    return render_template('index.html')


# transaction explorer page
@app.route('/tr/<transaction_id>', methods=['GET', 'POST'])
def transaction(transaction_id):
    transaction_url = "https://live.blockcypher.com/btc-testnet/tx/" + transaction_id + "/"
    transaction_data = requests.get("https://blockstream.info/testnet/api/tx/" + transaction_id).json()
    
    outputs = []
    for line in transaction_data.get('vout'):
        if line['scriptpubkey_type'] == 'op_return':
            outputs.append(line['scriptpubkey_asm'])
    transaction_data = '\n'.join(outputs)

    # TODO: learn do decipher scriptpubkey to extract text data
    # https://blockstream.info/testnet/api/tx/449f06d324daccfd65711e9856491f17945892491103b497baf4828b388e5c0c

    return render_template('transaction.html', transactionId=transaction_id, transactionUrl=transaction_url, transactionData=transaction_data)


if __name__ == '__main__':
    app.run()

