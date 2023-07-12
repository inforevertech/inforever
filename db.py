import datetime
from prisma import Prisma
from nostril import nonsense


# Add a new transaction into the database
async def db_insert_transaction(tr_hash, block_hash, message, post_date):
    post_date = datetime.datetime.fromtimestamp(int(post_date))
    nonsense = is_nonsense(message)

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
                'timestamp': post_date,
                'nonsense': nonsense
            },
            'update': {},
        },
    )

    await prisma.disconnect()


# Receive a list of transactions
async def db_read_transactions(limit=None, where=None):
    prisma = Prisma()
    await prisma.connect()

    # read transactions
    posts = await prisma.post.find_many(
        where=where,
        take=limit,
        order={
            'timestamp': 'desc',
        }
    )

    await prisma.disconnect()
    return posts


# Receive a list of human-readable messages
async def db_read_human_messages(limit=100):
    prisma = Prisma()
    await prisma.connect()

    # read transactions
    posts = await prisma.post.find_many(
        take=limit,
        where={
            'nonsense': False,
        },
        order={
            'timestamp': 'desc',
        }
    )

    await prisma.disconnect()
    return posts


# Receive total number of posts in the database
async def db_transactions_count(where=None):
    prisma = Prisma()
    await prisma.connect()

    # receive total number of transactions
    total_posts = await prisma.post.count()

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
        nonsense_check = is_nonsense(post.text)

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


# Insert senders addresses for a transaction
async def db_insert_sent_from(tr_hash, addresses):
    prisma = Prisma()
    await prisma.connect()

    # insert sender addresses to the db
    for address in addresses:
        result = await prisma.sender.create(
            data={
                'post_hash': tr_hash,
                'address_from': address
            }
        )

    await prisma.disconnect()


# Receive a list of addresses
async def db_read_addresses(limit=None, where=None):
    prisma = Prisma()
    await prisma.connect()

    # read transactions
    posts = await prisma.sender.find_many(
        where=where,
        take=limit
    )

    await prisma.disconnect()
    return posts