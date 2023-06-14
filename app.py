from flask import Flask, render_template, request
from bit import Key

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def hello_world():
    if request.method == 'POST':
        # If submit button is pressed get the values from the form: messsage and private key.
        message = request.form['message']
        private_key = request.form['private']
        # Create a key object from the private key.
        key = Key(private_key)
        # Send a transaction to the bitcoin network with the message as the data. Using op_return.
        key.send("123123123", message=message)
    return render_template('index.html')


if __name__ == '__main__':
    app.run()
