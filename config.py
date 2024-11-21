import os

class Config:
    API_KEY = os.getenv('API_KEY')  # 'default_value_if_not_set' is optional
