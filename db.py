from prisma import Prisma
from nostril import nonsense
from flask import g
import datetime
import asyncio


# Perform explorer search
async def db_search(input, limit=None, where=None, include_addresses=True):
    # seach in posts
    prisma = Prisma()
    await prisma.connect()

    if where is None:
        where = {}

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
            'media': True
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
async def db_read_transactions(limit=None, where=None, include_addresses=True):
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
        }
    )

    await prisma.disconnect()
    return posts


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
            'media': True
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
            'media': True
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