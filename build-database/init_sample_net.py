import asyncio
import sys, os
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import *
from avatar_generator import generate_avatar_by_address

# Sample Network can be used for public demostration allowing 
# to form all content in specific ways to demonstrate platform features

# Download sample media folder and put it in static/sample/
# TODO: https://link-to-media-folder

# Insert sample transaction
hash = 'ES1K24zJ93E'

# this is a random post I found on Reddit
message = """
Hello there,
I've been reading a lot about browsers but I'm getting anywhere with it.

What I understand and what I also know is that Chrome is the monopoly like Internet Explorer used to be. Chrome aka Google sells ads, and they obv won't shot it their own leg and block ads and trackers.

Google made it harder for Ad blockers to work, and now they try to add some DRM shit. I don't mind it, I will just refuse to open any website that's using this AD DRM shit and I will probably move to web3 as web3 looks better the more dumb stuff google does.

Now Firefox was seen as a big alternative for people who don't like giving a lot of power to one single ad company, sad part is that Firefox used to be good but goes downhill pretty bad. Their whole identitiy is based of "Chrome is bad come to us". In fact I really like webkit and chromium based browsers, they just work and many people work on it. Issue also with chromium is that this DRM nonsense will be added to it, even tho it is "Open Source".

So I'm using now Brave because chromium based, fast, uses v8 js engine and feels fast, blocks all ads, and I'm happy with it. But Brave also seem sorta sketchy. Is their only income the ads you see when you open your browser or tab? Or what is exactly going on here?

It somehow seems like there is no definitive anwser to which browser should we use. I don't even need any adons to be honest, unless I write them myself or download from github after checking them if they aren't sketchy.

I'm happy to read and learn more about it, if there is something we can count on, that is privacy focused, 100% transparent, no bloat..."""

# insert post
asyncio.run(db_insert_transaction(hash, None, message, int(round(datetime.datetime.now().timestamp())), 'sample'))
# generate avatar
generate_avatar_by_address('lawaldemur')
# insert address info
asyncio.run(db_insert_sent_address(hash, [['lawaldemur', False]], 'sample'))
# add media
asyncio.run(db_update_media(29, hash))
asyncio.run(db_update_media(23, hash))
