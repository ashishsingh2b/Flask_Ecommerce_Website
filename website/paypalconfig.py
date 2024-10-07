import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()  

class Config:
    # PayPal API credentials
    PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', 'Ac-6BenOMQUWhSKfhyApy0Hpgmr_ZgM2dK_IHPF62ihajDu-Jxj6BKUyErxeh2n_1tSvZ-JMaWpYbPBH')
    PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET', 'EGDEo0-Zf5zW8HZLGB0fG8_PLr1RqclDrA_bZHcUbU3c78TqnoIKFaZD_cnF3ZS2DRwB6tqa7I7HNZNC')
    PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')  # Change to 'live' for production

    # # Other configurations
    # DEBUG = True
    # SECRET_KEY = 'your_secret_key'  # Replace with your actual secret key
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///your_database.db'  # Update as needed
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
