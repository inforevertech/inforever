# Inforever

Inforever is a post-sharing platform utilizing the Bitcoin blockchain as the protocol for data storage. This approach presents some unique advantages, such as censorship resistance, imperishability of records, and unrestricted public access to data for everyone who has access to the blockchain.

Inforever works as a client-oriented user-friendly interface to display and share information in ```OP_RETURN``` statements.

## How it works
1. Have a private key with some BTC balance to pay transaction fees.
2. Create a message and use your private key to send it to the blockchain.
3. When the transaction is sent and the fee is paid, the message is recorded.
4. Use Inforever Explorer to see and share your messages in a friendly format.

## To launch
```shell
# Launch MySQL server on your local machine and create a database
# Don't forget to configure ./.env and ./build-database/.env files

# 1. Install virtualenv
pip install virtualenv

# 2. Create a virtualenv
virtualenv -p python3 venv

# 3. To activate virtual environment on Linux or MacOS: 
source venv/bin/activate
# Alternatively, to activate virtual environment on Windows:
# .\venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Generate database structure
prisma generate --schema=./build-database/schema.prisma

# 6. Scrape some data from blockchain for database
python3 ./build-database/collect_info.py

# 7. Launch the website
python3 app.py
```
