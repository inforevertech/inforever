from flask import Flask, render_template, request
from bit import PrivateKeyTestnet

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
        print("Transaction id:", key.send([('mqVyyV3bKQpMT59epHwY7zsMiKtweSyDiw', 0.00000001, 'btc')], message=message))

    return render_template('index.html')


if __name__ == '__main__':
    app.run()

