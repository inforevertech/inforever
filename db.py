import datetime
from prisma import Prisma


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


async def db_read_all_transactions():
    prisma = Prisma()
    await prisma.connect()

    # read transactions
    posts = await prisma.post.find_many()

    await prisma.disconnect()
    return posts
