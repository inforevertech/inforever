from flask import Flask, render_template, request
from bit import Key, PrivateKeyTestnet
import requests


app = Flask(__name__)


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

    # on testnet
    if request.args.get('testnet'):
        return render_template('index.html', testnet=True)
    # on mainnet
    return render_template('index.html', testnet=False)


if __name__ == '__main__':
    app.run()

