from flask import Flask, render_template, request, redirect, make_response, abort, g, url_for, send_file, session
from flask_optional_routes import OptionalRoutes
from flask_mail import Mail, Message
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from bit import Key, PrivateKeyTestnet
from bit import exceptions as bitExceptions
from bit.network import get_fee_cached
from dotenv import load_dotenv, find_dotenv
import logging
from logging.config import dictConfig
import datetime
import pytz
from tzlocal import get_localzone
import asyncio
import os.path
import sys
import re
from db import *
from scrape_blockchain import BlockchainScraper
from avatar_generator import generate_avatar_by_address


# configure logging to a file
dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            },
            "file": {
                "class": "logging.FileHandler",
                "filename": "inforever.log",
                "formatter": "default",
            },
        },
        "root": {"level": "INFO", "handlers": ["console", "file"]},
    }
)


NET_LIST = [
    { 'tag': 'btc', 'name': 'Bitcoin Blockchain' },
    { 'tag': 'btc-test', 'name': 'Bitcoin Testnet'},
]
DEFAULT_NET = NET_LIST[0]['tag']
REACTIONS = {
    "love": "&#x1F60D;",
    # "applause": "&#x1F44F;",
    "fire": "&#x1F525;",
    "brain": "&#x1F9E0;",
    "laugh": "&#x1F602;",
    "alarm": "&#x1F6A8;",
    "money": "&#x1F4B0;"
}  # correspond to reactions in db


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
        # if reply to a post
        if request.args.get('reply'):
            # find post in the database
            post = asyncio.run(db_find_post(request.args.get('reply')))
            if post:  # switch network according post's network
                network_switch(post.network)
            else:  # abort because post is not found
                abort(400, f"Post #{request.args.get('reply')} was not found.")

        return response(render_template('create.html',
                                        recommende_fee=get_fee_cached(fast=False),
                                        replyToHash=request.args.get('reply')))
    
    elif request.method == 'POST':  # save a post
        # If submit button is pressed get the values from the form: messsage, private key and transaction fee.
        message = request.form['message']
        private_key = request.form['private']
        fee = int(request.form['fee'])

        # post is replying to another one or not
        if request.form['replyToHash'] and asyncio.run(db_find_post(request.form['replyToHash'])):
            replyToHash = request.form['replyToHash']
            # optional donation for the author
            btc_donation_reply = request.form['btc_donation_reply']
            try:
                if btc_donation_reply and float(btc_donation_reply) > 0:
                    btc_donation_reply = float(btc_donation_reply)
            except Exception as e:
                btc_donation_reply = None
        else:
            replyToHash = None
            btc_donation_reply = None

        # process attached media files
        files = request.files.getlist("file[]")
        media = {}
        for file in files:
            # if file is in not acceptable format
            if not allowed_file(file.filename):
                abort(500)
                continue
            # insert info about the file into the database
            media_record = asyncio.run(db_insert_media(secure_filename(file.filename), str(file.content_type)))
            media[str(media_record.id)] = file

        # add media information to the post
        if media:
            message += '${' + ','.join(media.keys()) + '}$'


        # Create a key object from the private key.
        # TODO: put intermediary addresses into .env
        if g.net == 'btc':
            key = Key(private_key)
            # outputs = [('bc1qr2cytjzexpt0fvvldddxsaryfdu0u0nya807sm', 1, 'satoshi')]
            # fee -= 1
        elif g.net == 'btc-test':
            key = PrivateKeyTestnet(private_key)
            # outputs = [('mz53tFLDVHv1btvuVxtKZnr7KLRaQwXpGf', 1, 'satoshi')]
            # fee -= 1

        try:
            if btc_donation_reply is None:
                # Send a transaction to the bitcoin network with the message as the data. Using op_return.
                post_hash = key.send([], fee=fee, absolute_fee=True, message=message)
            else:
                # Send a transaction with a donation to the address of the replied post author
                replied_post = asyncio.run(db_find_post(replyToHash))
                if not replied_post.author:
                    abort(400, "Address of post's author is not found. Cannot send a donation.") 
                post_hash = key.send([(replied_post.author, btc_donation_reply, 'btc')], fee=fee, absolute_fee=True, message=message)

            # insert new post into the database
            asyncio.run(db_insert_transaction(post_hash, None, message, int(datetime.datetime.now().timestamp()), g.net,
                                              replyToHash=replyToHash, postedLocally=True, author=key.address, donation=btc_donation_reply, fee=fee))
            # add sender addresses information to the db
            asyncio.run(db_insert_sent_address(post_hash, [(key.address, False)], g.net))

            # upload media files to the server
            for file_id, file in media.items():
                # save file within the folder named as its id
                folder_path = os.path.join(app.config['UPLOAD_FOLDER'], str(file_id))
                os.mkdir(folder_path)
                file.save(os.path.join(folder_path, secure_filename(file.filename)))
                # update media database
                asyncio.run(db_update_media(int(file_id), post_hash))

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
        return redirect(url_for('post', hash=post_hash))


# main page
@optional.routes('/<net>?/', methods=['GET'])
def index(net=None):
    # switch network
    network_switch(net)

    return response(render_template('index.html',
                                    recommende_fee=get_fee_cached()))


# post explorer page
@optional.routes('/<net>?/post/<hash>', methods=['GET', 'POST'])
def post(hash, net=None):
    # post interaction
    if request.method == 'POST' and 'comment_post' in request.form:
        # reacted with a button
        if 'comment_reaction' in request.form and request.form['comment_reaction'] in REACTIONS.keys():
            asyncio.run(db_update_reactions(request.form['comment_post'], request.form['comment_reaction']))
        # replied with a comment
        elif 'comment_text' in request.form and request.form['comment_text'].strip():
            asyncio.run(db_insert_comment(request.form['comment_post'], request.form['comment_text']))

    # find post in the database
    post = asyncio.run(db_find_post(hash))
    explorer_url = "https://blockstream.info/" + "testnet/" if g.net == 'btc-test' else ""  + "tx/"
    fullPostReplies = asyncio.run(db_count_full_post_replies([post]))[post.hash]

    if post:  # post was found
        # switch network according post's network
        network_switch(post.network)

        return response(render_template('post.html',
                                        post=post,
                                        post_hash=hash,
                                        explorer_url=explorer_url,
                                        fullPostReplies=fullPostReplies))
    
    else:  # post was not found
        # switch network to the chosen global one
        network_switch(net)
        # form transaction not ready or not existent response
        return response(render_template('post.html',
                                        post_hash=hash,
                                        explorer_url=explorer_url,
                                        fullPostReplies=fullPostReplies))

    
# blockchain posts explorer page
@optional.routes('/<net>?/explorer/', methods=['GET', 'POST'])
def explorer(net=None):
    # switch network
    network_switch(net)

    # post interaction
    if request.method == 'POST' and 'comment_post' in request.form:
        # reacted with a button
        if 'comment_reaction' in request.form and request.form['comment_reaction'] in REACTIONS.keys():
            asyncio.run(db_update_reactions(request.form['comment_post'], request.form['comment_reaction']))
        # replied with a comment
        elif 'comment_text' in request.form and request.form['comment_text'].strip():
            asyncio.run(db_insert_comment(request.form['comment_post'], request.form['comment_text']))

    # search
    search = request.args.get('search')
    if search and search.strip():
        counter, results = asyncio.run(db_search(search, limit=50))
    else:
        results = asyncio.run(db_read_transactions(limit=50))
        counter = asyncio.run(db_transactions_count())

    return response(render_template('explorer.html',
                                    totalNmberOfPosts=f'{counter:,}',
                                    posts=results,
                                    search=search if search is not None else '',
                                    nestedReplies=asyncio.run(db_count_nested_replies(results)),
                                    fullPostReplies=asyncio.run(db_count_full_post_replies(results))))


# address/user page
@optional.routes('/<net>?/<id>', methods=['GET', 'POST'])
def address(id, net=None):
    # switch network
    network_switch(net)

    # post interaction
    if request.method == 'POST' and 'comment_post' in request.form:
        # reacted with a button
        if 'comment_reaction' in request.form and request.form['comment_reaction'] in REACTIONS.keys():
            asyncio.run(db_update_reactions(request.form['comment_post'], request.form['comment_reaction']))
        # replied with a comment
        elif 'comment_text' in request.form and request.form['comment_text'].strip():
            asyncio.run(db_insert_comment(request.form['comment_post'], request.form['comment_text']))
    
    # get a list of posts
    posts = asyncio.run(db_find_posts_by_addresses(id))

    if posts:
        # generate avatar if not present
        if not os.path.isfile(os.path.dirname(os.path.abspath(__file__)) + '/static/avatars/' + id + '.png'):
            generate_avatar_by_address(id)

    return response(render_template('address.html',
                                    address=id,
                                    totalNmberOfPosts=f'{len(posts):,}',
                                    posts=posts,
                                    nestedReplies=asyncio.run(db_count_nested_replies(posts)),
                                    fullPostReplies=asyncio.run(db_count_full_post_replies(posts))))
    

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


# receive user's local timezone from browser's API
@app.route('/set_timezone', methods=['POST'])
def set_timezone():
    '''Get timezone from the browser and store it in the session object.'''
    timezone = request.data.decode('utf-8')
    session['timezone'] = timezone
    return ""


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
    elif name == 'theme':
        if value in ['light', 'dark']:
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
    resp.set_cookie('theme', g.theme)
        
    return resp


# share some variables with templates through global variables
@app.before_request
def set_global_variables():
    g.nets = NET_LIST

    # dark/light theme mode
    if correct_cookie('theme', request.args.get('theme')):
        g.theme = request.args.get('theme')
    elif correct_cookie('theme', request.cookies.get('theme')):
        g.theme = request.cookies.get('theme')
    else:
        g.theme = "light"  # default

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

    # set global list of reactions
    g.reactions = REACTIONS
        

# Template fields format functions
@app.context_processor
def utility_processor():
    # Return only specific character of an address
    def format_shorten_address(address):
        return address[:4] + '...' + address[-5:]
    
    # Return only specific character of an address
    def format_shorten_post_hash(hash):
        return hash[:2] + '...' + hash[-4:]
    
    # Return timestamp in user-friendly date format
    def format_date(post_datetime):
        # convert to local timezone
        # TODO: insted of using 'Asia/Dubai' timezone, convert all datetime objects to UTC in the db
        if 'timezone' in session:
            post_datetime = post_datetime.replace(tzinfo=pytz.timezone('Asia/Dubai')).astimezone(pytz.timezone(session['timezone']))
        else:
            post_datetime = post_datetime.replace(tzinfo=pytz.timezone('Asia/Dubai')).astimezone(get_localzone())

        if post_datetime.date() == datetime.datetime.now().astimezone().date():  # post_datetime is today
            post_datetime = post_datetime.astimezone(tz=None).strftime("%-I:%M %p Today")
        elif post_datetime.date() == (datetime.datetime.now() - datetime.timedelta(days=1)).astimezone().date():  # post_datetime is yesterday
            post_datetime = post_datetime.astimezone(tz=None).strftime("%-I:%M %p Yesterday")
        else:  # post_datetime is any other day
            post_datetime =  post_datetime.astimezone(tz=None).strftime("%-I:%M %p on %B %-d, %Y")

        return post_datetime
    
    # Return url for transaction avatar
    def find_address_avatar(address):
        # if avatar was NOT generated
        if not os.path.isfile(os.path.dirname(os.path.abspath(__file__)) + '/static/avatars/' + address + '.png'):
            return 'avatars/profile.png'
        return 'avatars/' + address + '.png'  # otherwise
    
    # Return whether some of replies are comments
    def comment_replies(replies):
        for reply in replies:
            if not reply.fullPost:
                return True
        return False
    
    # Return whether some of replies are full posts
    def full_post_replies(replies):
        for reply in replies:
            if reply.fullPost:
                return True
        return False
    
    return dict(format_shorten_address=format_shorten_address,
                format_shorten_post_hash=format_shorten_post_hash,
                format_date=format_date,
                find_address_avatar=find_address_avatar,
                full_post_replies=full_post_replies,
                comment_replies=comment_replies)


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
    # set logging level to info
    logging.basicConfig(level=logging.INFO)

    # set secret key for sessions
    app.secret_key = os.environ.get("SESSION_SECRET_KEY")

    # run the app
    app.run(debug=True, host="0.0.0.0")

