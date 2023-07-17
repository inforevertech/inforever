from flask import Flask, render_template, request, redirect, make_response, abort, g
from flask_optional_routes import OptionalRoutes
from flask_mail import Mail, Message
from werkzeug.exceptions import HTTPException
from bit import Key, PrivateKeyTestnet
from bit import exceptions as bitExceptions
from bit.network import get_fee_cached
from db import *
import datetime
import asyncio
import os.path
import re
from avatar_generator import generate_avatar_by_address


app = Flask(__name__)
optional = OptionalRoutes(app)
mail = Mail(app)  # TODO: configure email server

NET_LIST = [
    { 'tag': 'btc', 'name': 'Bitcoin Blockchain' },
    { 'tag': 'btc-test', 'name': 'Bitcoin Testnet'},
]
DEFAULT_NET = NET_LIST[0]['tag']


# main page
# @app.route('/', methods=['GET', 'POST'])
@optional.routes('/<net>?/')
def index(net=None):
    # switch network
    network_switch(net)
    
    if request.method == 'POST':
        # If submit button is pressed get the values from the form: messsage, private key and transaction fee.
        message = request.form['message']
        private_key = request.form['private']
        fee = int(request.form['fee'])

        # Create a key object from the private key.
        if g.net == 'btc':
            key = Key(private_key)
        elif g.net == 'btc-test':
            key = PrivateKeyTestnet(private_key)

        try:
            # Send a transaction to the bitcoin network with the message as the data. Using op_return.
            transaction_id = key.send([], fee=fee, absolute_fee=True, message=message)
        except bitExceptions.InsufficientFunds as e:
            # form insufficient funds description
            errorContent = ["Error message: " + str(e)]
            if g.net == 'btc-test':
                errorContent.append("Use the following faucet to get testnet satoshis: https://testnet-faucet.com/btc-testnet/")
            
            # return page with insufficient funds information
            return response(render_template('error.html',
                                   errorTitle="Insufficient Funds",
                                   additionalInfo=key.address,
                                   errorContent=errorContent))
        except:
            # return page with error description
            return response(render_template('error.html',
                                   errorTitle="Error occured",
                                   additionalInfo=key.address,
                                   errorContent=["Error message: " + str(e)]))

        return redirect("/tr/" + transaction_id)

    return response(render_template('index.html',
                           recommende_fee=get_fee_cached()))


# post explorer page
# @app.route('/post/<hash>', methods=['GET', 'POST'])
@optional.routes('/<net>?/post/<hash>')
def post(hash, net=None):
    post = asyncio.run(db_find_post(hash))

    # switch network according post's network
    network_switch(post.network)
    
    if not post:
        # form transaction not ready or not existent response
        return response(render_template('post.html',
                                post_hash=hash))

    return response(render_template('post.html',
                            post=post,
                            post_hash=hash))


# blockchain messages explorer page
# @app.route('/explorer', methods=['GET', 'POST'])
@optional.routes('/<net>?/explorer/')
def explorer(net=None):
    # switch network
    network_switch(net)
    
    # human-readable format filtration
    human = request.args.get('human')
    if human is None or human == "1":
        human, where = True, { 'nonsense': False }
    else:
        human, where = False, None

    # search
    search = request.args.get('search')
    if search:
        counter, results = asyncio.run(db_search(search, where=where, limit=50))
    else:
        results = asyncio.run(db_read_transactions(where=where, limit=50))
        counter = asyncio.run(db_transactions_count(where=where))

    
    return response(render_template('explorer.html',
                           totalNmberOfPosts=f'{counter:,}',
                           messages=results,
                           search=search if search is not None else '',
                           human=human))


# address/user page
# @app.route('/<id>', methods=['GET', 'POST'])
@optional.routes('/<net>?/<id>')
def address(id, net=None):
    # switch network
    network_switch(net)

    # human-readable format filtration
    human = request.args.get('human')
    if human is None or human == "1":
        human, nonse = True, False
    else:
        human, nonse = False, None
    
    # get a list of posts
    posts = asyncio.run(db_find_posts_by_addresses(id, nonsense=False))

    if posts:
        # generate avatar if not present
        if not os.path.isfile(os.path.dirname(os.path.abspath(__file__)) + '/static/avatars/' + id + '.png'):
            generate_avatar_by_address(id)

    return response(render_template('address.html',
                           address=id,
                           totalNmberOfPosts=f'{len(posts):,}',
                           messages=posts,
                           human=human))
    

# mission page
# @app.route('/about', methods=['GET'])
@optional.routes('/<net>?/mission')
def mission(net=None):
    # switch network
    network_switch(net)
    
    # return static template
    return response(render_template('mission.html'))


# contact us page
# @app.route('/contact', methods=['GET'])
@optional.routes('/<net>?/contact', methods=['GET', 'POST'])
def contact(net=None):
    # switch network
    network_switch(net)

    status = 'none'
    # check post parameters
    if request.method == 'POST':
        name, email, message = request.form['name'], request.form['email'], request.form['message']
        if name and email and message and re.match(r"[^@]+@[^@]+\.[^@]+", email):
            # send an email to contact us
            msg = Message(message + "\nfrom " + request.form['name'] + " " + email,
                          sender=email,
                          recipients=[])
            # mail.send(msg)

            status = 'success'
        else:
            status = 'error'

    
    # return static template
    return response(render_template('contact.html', status=status))


# proccess url network switch
def network_switch(net):
    # switch network
    if correct_cookie('net', net):
        g.net = net
    elif net is not None:  # wrong network chosen
        abort(400, 'No blockchain "' + str(net) + '" found.') 
        

# check cookie correctness
def correct_cookie(name, value):
    if name == 'net':
        if value is not None and value in [network['tag'] for network in NET_LIST]:
            return True
    elif name == 'recent':
        if value is not None and value in ['D', 'W', 'M', 'Y', 'A']:
            return True
   
    return False


# form http response with optional cookies
def response(template, cookies=None, **parameters):
    # create a response
    resp = make_response(template)
    
    # set current network cookie
    resp.set_cookie('net', g.net)
        
    return resp


# share some variables with templates through global variables
@app.before_request
def set_global_variables():
    g.nets = NET_LIST

    # recent filter
    if correct_cookie('recent', request.args.get('recent')):
        g.recent = request.args.get('recent')
    else:
        g.recent = "A"  # default

    # set default blockchain network
    if correct_cookie('net', request.args.get('net')):
        g.net = request.args.get('net')
    elif correct_cookie('net', request.cookies.get('net')):
        g.net = request.cookies.get('net')
    else:
        g.net = DEFAULT_NET
        

# Template fields format functions
@app.context_processor
def utility_processor():
    # Return only 4 last character of an address
    def format_shorten_address(address):
        return address[:4] + '...' + address[-5:]
    
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
    return response(render_template('error.html',
                            errorTitle="Sorry, this page was not found.",
                            additionalInfo="Error 404",
                            errorContent=[str(e)])), 404

# other HTTP exceptions
@app.errorhandler(HTTPException)
def page_error(e):
    return response(render_template('error.html',
                            errorTitle="Sorry, a problem occured.",
                            additionalInfo="Error " + str(e.code),
                            errorContent=[str(e)])), e.code


if __name__ == '__main__':
    app.run(debug=True)

