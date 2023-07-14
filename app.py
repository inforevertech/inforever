from flask import Flask, render_template, request, redirect
from werkzeug.exceptions import HTTPException
from bit import Key, PrivateKeyTestnet
from bit import exceptions as bitExceptions
from bit.network import get_fee_cached
from db import *
import requests
import datetime
import asyncio
import os.path

from avatar_generator import generate_avatar_by_address

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
                                   additionalInfo=key.address,
                                   errorContent=errorContent)
        except:
            # return page with error description
            return render_template('error.html',
                                   errorTitle="Error occured",
                                   additionalInfo=key.address,
                                   errorContent=["Error message: " + str(e)])

        return redirect("/tr/" + transaction_id)

    return render_template('index.html',
                           recommende_fee=get_fee_cached())


# transaction explorer page
@app.route('/post/<transaction_id>', methods=['GET', 'POST'])
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
            post_date = datetime.datetime.fromtimestamp(transaction_data.get('status').get('block_time'))
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
    transactions = asyncio.run(db_read_human_messages(limit=100))
    
    return render_template('explorer.html',
                           totalNmberOfPosts=f'{asyncio.run(db_transactions_count()):,}',
                           messages=transactions)


# address/user page
@app.route('/<id>', methods=['GET', 'POST'])
def address(id):
    # get a list of posts
    posts = asyncio.run(db_find_posts_by_addresses(id))

    if posts:
        # generate avatar if not present
        if not os.path.isfile(os.path.dirname(os.path.abspath(__file__)) + '/static/avatars/' + id + '.png'):
            generate_avatar_by_address(id)

    return render_template('address.html',
                           address=id,
                           totalNmberOfPosts=f'{len(posts):,}',
                           messages=posts)
    

# about us page
@app.route('/about', methods=['GET'])
def about():
    # return static template
    return render_template('about.html')


# Template fields format functions
@app.context_processor
def utility_processor():
    # Return only 4 last character of an address
    def format_shorten_address(address):
        return address[:3] + '...' + address[-5:]
    
    # Return timestamp in user-friendly date format
    def format_date(post_datetime):
        if post_datetime.date() == datetime.datetime.now().date():  # post_datetime is today
            return post_datetime.strftime("%-I:%M %p Today")
        elif post_datetime.date() == (datetime.datetime.now() - datetime.timedelta(days=1)).date():  # post_datetime is yesterday
            return post_datetime.strftime("%-I:%M %p Yesterday")
        else:  # post_datetime is any other day
            return post_datetime.strftime("%-I:%M %p on %A, %B %-d, %Y")
    
    # Return url for transaction avatar
    def find_address_avatar(address):
        # if avatar was NOT generated
        if not os.path.isfile(os.path.dirname(os.path.abspath(__file__)) + '/static/avatars/' + address + '.png'):
            return 'avatars/profile.png'
        return 'avatars/' + address + '.png'  # otherwise
    
    return dict(format_shorten_address=format_shorten_address,
                format_date=format_date,
                find_address_avatar=find_address_avatar)


# 404 page not found
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html',
                            errorTitle="Sorry, this page was not found.",
                            additionalInfo="Error 404",
                            errorContent=[str(e)]), 404

# other HTTP exceptions
@app.errorhandler(HTTPException)
def page_error(e):
    return render_template('error.html',
                            errorTitle="Sorry, a problem occured.",
                            additionalInfo="Error " + str(e.code),
                            errorContent=[str(e)]), e.code


if __name__ == '__main__':
    app.run(debug=True)

