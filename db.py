from collections import deque
from prisma import Prisma
from nostril import nonsense
from flask import g
import datetime
import random


# maximum number of nested replies to show
NESTED_REPLIES_LIMIT = 5
# form query part for nested replies
nested_replies = { 'include': { 'repliers': True } }
for _ in range(NESTED_REPLIES_LIMIT):
    nested_replies = { 'include': { 'repliers': nested_replies } }


# Perform explorer search
async def db_search(input, limit=None, where=None, include_addresses=True):
    # seach in posts
    prisma = Prisma()
    await prisma.connect()

    # search only among posts not replies
    if where is None:
        where = { 'isReply': False }
    else:
        where['isReply'] = False

    where['OR'] = [
            {
                'hash': input,
            },
            {
                'block': input,
            },
            {
                'addresses': {
                    'some': {
                        'address': {
                            'equals': input,
                        }
                    }
                }
            },
            {
                'text': {
                    'search': input,
                }
            },
        ]

    # find relevant posts
    posts = await prisma.post.find_many(
        take=limit,
        where=where,
        include={
            'addresses': include_addresses,
            'media': True,
            'repliers': True,
        }
    )

    # how many posts were found
    counter = await prisma.post.count(where=where)
    
    await prisma.disconnect()
    return (counter, posts)


# Add a new transaction into the database
async def db_insert_transaction(tr_hash, block_hash, message, post_date, network):
    post_date = datetime.datetime.fromtimestamp(int(post_date))

    formatted = message_media_filter(message)
    nonsense = is_nonsense(formatted)

    prisma = Prisma()
    await prisma.connect()

    # insert a new transaction
    post = await prisma.post.upsert(
        where={
            'hash': tr_hash
        },
        data={
            'create': {
                'hash': tr_hash,
                'block': block_hash,
                'text': message,
                'formatted_text': formatted,
                'timestamp': post_date,
                'nonsense': nonsense,
                'network': network
            },
            'update': {},
        },
    )

    await prisma.disconnect()


# Insert new comment on post
async def db_insert_comment(post_hash, text, network="inforever"):
    formatted = message_media_filter(text)
    nonsense = is_nonsense(formatted)
    tr_hash = str(random.getrandbits(64))

    prisma = Prisma()
    await prisma.connect()

    # insert a new transaction
    post = await prisma.post.upsert(
        where={
            'hash': tr_hash
        },
        data={
            'create': {
                'hash': tr_hash,
                'text': text,
                'formatted_text': formatted,
                'nonsense': nonsense,
                'network': network,
                'isReply': True,
                'replyToHash': post_hash 
            },
            'update': {},
        },
    )

    await prisma.disconnect()


# Update formatted text for all posts 
async def db_update_format_transactions():
    prisma = Prisma()
    await prisma.connect()

    posts = await prisma.post.find_many()

    for post in posts:
        formatted = message_media_filter(post.text)

        updated = await prisma.post.update(
            where={
                'id': post.id,
            },
            data={
                'formatted_text': formatted,
                'nonsense': is_nonsense(formatted)
            }
        )

    await prisma.disconnect()


# remove media tags part in message text
def message_media_filter(message):
    message = message.strip()

    # media formatting
    if '${' in message and '}$' in message:
        start, end = message.find('${'), message.find('}$')

        media_content = message[start + 2:end]
        # TODO: insert media_content as media into the db

        message = message[:start]

    return message


# Receive a list of transactions
async def db_read_transactions(limit=None, where=None, include_addresses=True, replies=False):
    prisma = Prisma()
    await prisma.connect()

    # specify network
    if where is None:
        where = { 'isReply': replies }
    else:
        where['isReply'] = replies

    # specify network
    where['network'] = g.net

    # specify recent range
    if g.recent == 'D':
        where['timestamp'] = { 'gt': datetime.datetime.now() - datetime.timedelta(days=1) }
    elif g.recent == 'W':
        where['timestamp'] = { 'gt': datetime.datetime.now() - datetime.timedelta(days=7) }
    elif g.recent == 'M':
        where['timestamp'] = { 'gt': datetime.datetime.now() - datetime.timedelta(days=30) }
    elif g.recent == 'Y':
        where['timestamp'] = { 'gt': datetime.datetime.now() - datetime.timedelta(days=365) }
    elif g.recent == 'A':
        pass

    # specify human readable format
    if g.human:
        where['nonsense'] = False

    # read transactions
    posts = await prisma.post.find_many(
        where=where,
        take=limit,
        order={
            'timestamp': 'desc',
        },
        include={
            'addresses': include_addresses,
            'media': True,
            'repliers': True,
        }
    )

    await prisma.disconnect()
    return posts


# Return the number of nested replies
async def db_count_nested_replies(posts):
    prisma = Prisma()
    await prisma.connect()

    replies_counter = {}

    # go through all passed posts
    for post in posts:
        # use BFS approach to count nested replies
        queue = deque([post.hash])
        replies_counter[post.hash] = 0
        
        while len(queue) > 0:
            replies = await prisma.post.find_many(
                where={
                    'replyToHash': queue.popleft(),
                },
            )

            for reply in replies:
                queue.append(reply.hash)
                replies_counter[post.hash] += 1


    await prisma.disconnect()
    return replies_counter


# read comments
async def db_read_replies(post_hash, limit=None, where=None):
    prisma = Prisma()
    await prisma.connect()

    # select replies only
    if where is None:
        where = { 'replyToHash': post_hash }
    else:
        where['replyToHash'] = post_hash


    replies = await prisma.post.find_many(
        where=where,
        limit=limit,
        order={
            'timestamp': 'desc',
        },
        include={
            'media': True,
        }
    )

    await prisma.disconnect()
    return replies
    

# Receive total number of posts in the database
async def db_transactions_count(where=None):
    prisma = Prisma()
    await prisma.connect()

    # specify network
    if where is None:
        where = { 'network': g.net }
    else:
        where['network'] = g.net

    # specify recent range
    if g.recent == 'D':
        where['timestamp'] = { 'gt': datetime.datetime.now() - datetime.timedelta(days=1) }
    elif g.recent == 'W':
        where['timestamp'] = { 'gt': datetime.datetime.now() - datetime.timedelta(days=7) }
    elif g.recent == 'M':
        where['timestamp'] = { 'gt': datetime.datetime.now() - datetime.timedelta(days=30) }
    elif g.recent == 'Y':
        where['timestamp'] = { 'gt': datetime.datetime.now() - datetime.timedelta(days=365) }
    elif g.recent == 'A':
        pass

    # specify human readable format
    if g.human:
        where['nonsense'] = False

    # receive total number of transactions
    total_posts = await prisma.post.count(where=where)

    await prisma.disconnect()
    return total_posts


# Reasses nonsense factor of all posts in the database
async def db_validate_transactions_nonsense():
    prisma = Prisma()
    await prisma.connect()

    # select posts to check
    posts = await prisma.post.find_many(
        order={
            'timestamp': 'desc',
        }
    )

    for post in posts:
        nonsense_check = is_nonsense(post.formatted_text)

        # if do not correspond to the db value
        if post.nonsense != nonsense_check:
            # update record in the database
            await prisma.post.update(
                where={
                    'id': post.id,
                },
                data={
                    'nonsense': nonsense_check,
                }
            )


    await prisma.disconnect()


# Nonsense checker
def is_nonsense(text):
    try:
        if len(text) == 0:  # empty, therefore nonsense
            nonsense_check = True
        elif len(text) < 5:  # too short but can make sense
            nonsense_check = False
        elif not nonsense(text):  # seems to make sense
            nonsense_check = False
            # these formats incorrectly recognized as not nonsense
            if len(text) > 15 and text.count(' ') == 0:
                nonsense_check = True
        else:
            nonsense_check = True
    except:
        nonsense_check = True

    return nonsense_check


# Return post content
async def db_find_post(post_hash):
    prisma = Prisma()
    await prisma.connect()
    
    # find post by its hash
    post = await prisma.post.find_unique(
        where={
            'hash': post_hash
        },
        include={
            'addresses': True,
            'media': True,
            'repliers': nested_replies,
        }
    )
    
    await prisma.disconnect()
    return post


# Insert senders addresses for a transaction
async def db_insert_sent_address(tr_hash, addresses, network):
    prisma = Prisma()
    await prisma.connect()

    # insert sender addresses to the db
    # TODO: use upsert instead
    for address in addresses:
        # receive total number of transactions made by this address
        total_trs = await prisma.address.count(
            where={
                'post_hash': tr_hash,
                'address': address[0],
                'direction': address[1],
                'network': network
            }
        )

        if total_trs == 0:
            await prisma.address.create(
                data={
                    'post_hash': tr_hash,
                    'address': address[0],
                    'direction': address[1],
                    'network': network
                }
            )

    await prisma.disconnect()


# Receive a list of addresses
async def db_read_addresses(limit=None, where=None):
    prisma = Prisma()
    await prisma.connect()

    # specify network
    if where is None:
        where = { 'network': g.net }
    else:
        where['network'] = g.net

    # read transactions
    posts = await prisma.address.find_many(
        where=where,
        take=limit
    )

    await prisma.disconnect()
    return posts


# Receive a list of posts made by passed address
async def db_find_posts_by_addresses(address, limit=None):
    prisma = Prisma()
    await prisma.connect()

    # prep 'where' of the query
    where = {
            'addresses': {
                'some': {
                    'address': {
                        'equals': address
                    }
                }
            },
            'network': g.net,
        }
    
    # specify recent range
    if g.recent == 'D':
        where['timestamp'] = { 'gt': datetime.datetime.now() - datetime.timedelta(days=1) }
    elif g.recent == 'W':
        where['timestamp'] = { 'gt': datetime.datetime.now() - datetime.timedelta(days=7) }
    elif g.recent == 'M':
        where['timestamp'] = { 'gt': datetime.datetime.now() - datetime.timedelta(days=30) }
    elif g.recent == 'Y':
        where['timestamp'] = { 'gt': datetime.datetime.now() - datetime.timedelta(days=365) }
    elif g.recent == 'A':
        pass

    # specify human readable format
    if g.human:
        where['nonsense'] = False

    # read transactions
    posts = await prisma.post.find_many(
        where=where,
        include={
            'addresses': True,
            'media': True,
            'repliers': True,
        },
        take=limit
    )

    await prisma.disconnect()
    return posts


# Add a new media information into the database
async def db_insert_media(filename, type):
    prisma = Prisma()
    await prisma.connect()

    # insert a new transaction
    media = await prisma.media.create(
        data={
            'type': type,
            'filename': filename,
        },
    )

    await prisma.disconnect()
    return media


# Update media information
async def db_update_media(id, post_hash):
    prisma = Prisma()
    await prisma.connect()

    # insert a new transaction
    media = await prisma.media.update(
        where={
            'id': id,
        },
        data={
            'post_hash': post_hash,
        },
    )

    await prisma.disconnect()
    return media


# Read media information
async def db_read_media(id):
    prisma = Prisma()
    await prisma.connect()

    # insert a new transaction
    media = await prisma.media.find_unique(
        where={
            'id': id,
        },
    )

    await prisma.disconnect()
    return media


# Update reactions counter
async def db_update_reactions(post_hash, reaction):
    prisma = Prisma()
    await prisma.connect()
    
    # insert a new reaction
    reaction = await prisma.post.update(
        where={
            'hash': post_hash,
        },
        data={
            reaction + '_counter': {
                'increment': 1,
            }
        }
    )

    await prisma.disconnect()