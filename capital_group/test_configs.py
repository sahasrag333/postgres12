# test_configs.py
from configs import config

print("Flask Env:", config.FLASK_ENV)
print("DB URI:", config.SQLALCHEMY_DATABASE_URI)
print("Celery Broker:", config.CELERY_BROKER_URL)
