from flask import Flask, render_template, request, redirect, make_response, abort, g, url_for, send_file
from flask_optional_routes import OptionalRoutes
from flask_mail import Mail, Message
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from bit import Key, PrivateKeyTestnet
from bit import exceptions as bitExceptions
from bit.network import get_fee_cached
from dotenv import load_dotenv, find_dotenv
import datetime
import asyncio
import os.path
import re
from db import *
from avatar_generator import generate_avatar_by_address


NET_LIST = [
    { 'tag': 'btc', 'name': 'Bitcoin Blockchain' },
    { 'tag': 'btc-test', 'name': 'Bitcoin Testnet'},
]
DEFAULT_NET = NET_LIST[0]['tag']


app = Flask(__name__)
optional = OptionalRoutes(app)
mail = Mail(app)  # TODO: configure email server

# file upload configuration
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/media/'))
app.config['UPLOAD_FORMATS'] = ['jpg', 'jpeg', 'png', 'csv', 'pdf', 'docx', 'doc', 'mp3', 'mov', 'mp4', 'json', 'xslsx', 'pptx']

# local env variables
load_dotenv(find_dotenv())


# post creation page
@optional.routes('/<net>?/create',  methods=['GET', 'POST'])
def create(net=None):
    # switch network
    network_switch(net)

    if request.method == 'GET':  # show page to write a post
        return response(render_template('create.html',
                                        recommende_fee=get_fee_cached(fast=False)))
    
    elif request.method == 'POST':  # save a post
        # If submit button is pressed get the values from the form: messsage, private key and transaction fee.
        message = request.form['message']
        private_key = request.form['private']
        fee = int(request.form['fee'])

        files = request.files.getlist("file[]")
        media = {}
        for file in files:
            # if file is in not acceptable format
            if not allowed_file(file.filename):
                # TODO: cause exception and return error page
                continue
            # insert info about the file into the database
            media_record = asyncio.run(db_insert_media(secure_filename(file.filename), str(file.content_type)))
            media[str(media_record.id)] = file

        # add media information to the message
        if media:
            message += '${' + ','.join(media.keys()) + '}$'


        # Create a key object from the private key.
        if g.net == 'btc':
            key = Key(private_key)
        elif g.net == 'btc-test':
            key = PrivateKeyTestnet(private_key)

        try:
            # Send a transaction to the bitcoin network with the message as the data. Using op_return.
            post_id = key.send([], fee=fee, absolute_fee=True, message=message)

            # insert new post into the database
            asyncio.run(db_insert_transaction(post_id, None, message, int(datetime.datetime.now().timestamp()), g.net))
            # add sender addresses information to the db
            asyncio.run(db_insert_sent_address(post_id, [(key.address, False)], g.net))

            # upload media files to the server
            for file_id, file in media.items():
                # save file within the folder named as its id
                folder_path = os.path.join(app.config['UPLOAD_FOLDER'], str(file_id))
                os.mkdir(folder_path)
                file.save(os.path.join(folder_path, secure_filename(file.filename)))
                # update media database
                asyncio.run(db_update_media(int(file_id), post_id))

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
        except Exception as e:
            # return page with error description
            return response(render_template('error.html',
                                            errorTitle="Error occured",
                                            additionalInfo=key.address,
                                            errorContent=["Error message: " + str(e)]))

        # redirect to its page
        return redirect(url_for('post', hash=post_id))


# main page
@optional.routes('/<net>?/', methods=['GET'])
def index(net=None):
    # switch network
    network_switch(net)

    return response(render_template('index.html',
                                    recommende_fee=get_fee_cached()))


# post explorer page
@optional.routes('/<net>?/post/<hash>')
def post(hash, net=None):
    post = asyncio.run(db_find_post(hash))
    explorer_url = "https://blockstream.info/" + "testnet/" if g.net == 'btc-test' else ""  + "tx/"

    if post:  # post was found
        # switch network according post's network
        network_switch(post.network)

        return response(render_template('post.html',
                                        post=post,
                                        post_hash=hash,
                                        explorer_url=explorer_url))
    
    else:  # post was not found
        # switch network to the chosen global one
        network_switch(net)
        # form transaction not ready or not existent response
        return response(render_template('post.html',
                                        post_hash=hash,
                                        explorer_url=explorer_url))

    
# blockchain messages explorer page
@optional.routes('/<net>?/explorer/')
def explorer(net=None):
    # switch network
    network_switch(net)

    # search
    search = request.args.get('search')
    if search and search.strip():
        counter, results = asyncio.run(db_search(search, limit=50))
    else:
        results = asyncio.run(db_read_transactions(limit=50))
        counter = asyncio.run(db_transactions_count())

    return response(render_template('explorer.html',
                                    totalNmberOfPosts=f'{counter:,}',
                                    messages=results,
                                    search=search if search is not None else ''))


# address/user page
@optional.routes('/<net>?/<id>')
def address(id, net=None):
    # switch network
    network_switch(net)
    
    # get a list of posts
    posts = asyncio.run(db_find_posts_by_addresses(id))

    if posts:
        # generate avatar if not present
        if not os.path.isfile(os.path.dirname(os.path.abspath(__file__)) + '/static/avatars/' + id + '.png'):
            generate_avatar_by_address(id)

    return response(render_template('address.html',
                                    address=id,
                                    totalNmberOfPosts=f'{len(posts):,}',
                                    messages=posts))
    

# mission page
@optional.routes('/<net>?/mission')
def mission(net=None):
    # switch network
    network_switch(net)
    
    # return static template
    return response(render_template('mission.html'))


# media page
@optional.routes('/media/<id>')
def media(id):
    # return static file
    media = asyncio.run(db_read_media(int(id.strip())))

    # TODO: catch file not found exception
    try:
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], str(media.id), media.filename))
    except FileNotFoundError as e:
        return 'File not found.'
    except:
        return 'An error occured.'


# contact us page
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
    return response(render_template('contact.html',
                                    status=status))


# donate page
@optional.routes('/<net>?/donate', methods=['GET', 'POST'])
def donate(net=None):
    # switch network
    network_switch(net)
    
    # return static template
    return response(render_template('donate.html',
                                    address=os.environ.get("BTC_ADDRESS")))


# filter files
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['UPLOAD_FORMATS']


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
    elif name == 'human':
        if value in ['0', '1']:
            return True
   
    return False


# form http response with optional cookies
def response(template, cookies=None, **parameters):
    # create a response
    resp = make_response(template)
    
    # set current cookies
    resp.set_cookie('net', g.net)
    resp.set_cookie('recent', g.recent)
    resp.set_cookie('human', '1' if g.human else '0')
        
    return resp


# share some variables with templates through global variables
@app.before_request
def set_global_variables():
    g.nets = NET_LIST

    # recent filter
    if correct_cookie('recent', request.args.get('recent')):
        g.recent = request.args.get('recent')
    elif correct_cookie('recent', request.cookies.get('recent')):
        g.recent = request.cookies.get('recent')
    else:
        g.recent = "A"  # default

    # human filter
    if correct_cookie('human', request.args.get('human')):
        g.human = request.args.get('human') == '1'
    elif correct_cookie('human', request.cookies.get('human')):
        g.human = request.cookies.get('human') == '1'
    else:
        g.human = False  # default

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
            # return post_datetime.strftime("%-I:%M %p on %A, %B %-d, %Y")
            return post_datetime.strftime("%-I:%M %p on %B %-d, %Y")
    
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

