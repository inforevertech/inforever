from app import app
from app import scheduler

if __name__ == "__main__":
    scheduler.start()
    app.run()
