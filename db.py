import datetime
from prisma import Prisma


# Add a new transaction into the database
async def db_insert_transaction(tr_hash, block_hash, message, post_date):
    post_date = datetime.datetime.fromtimestamp(int(post_date))

    prisma = Prisma()
    await prisma.connect()

    # insert a new transaction
    user = await prisma.post.upsert(
        where={
            'hash': tr_hash
        },
        data={
            'create': {
                'hash': tr_hash,
                'block': block_hash,
                'text': message,
                'timestamp': post_date
            },
            'update': {},
        },
    )

    await prisma.disconnect()


# Receive a list of transactions
async def db_read_transactions(limit=100):
    prisma = Prisma()
    await prisma.connect()

    # read transactions
    posts = await prisma.post.find_many(
        take=limit,
        order={
            'timestamp': 'desc',
        }
    )

    await prisma.disconnect()
    return posts


# Receive total number of posts in the database
async def db_transactions_count():
    prisma = Prisma()
    await prisma.connect()

    # receive total number of transactions
    total_posts = await prisma.post.count()

    await prisma.disconnect()
    return total_posts
