import random
import string
from passlib.context import CryptContext
from ua_parser import user_agent_parser
from fastapi import Request
from geopy.geocoders import Nominatim
import requests


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str):
    return pwd_context.verify(password, hashed_password)


def generate_password_reset_code():
    # generate a random string of length 10
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))


def extract_device_info(request: Request):
    """
    Extract device information from request headers
    """
    ua_string = request.headers.get("User-Agent")
    language = request.headers.get("Accept-Language")
    user_agent = user_agent_parser.Parse(ua_string)
    device = user_agent['device']
    device_name = device['family']

    # Use a free IP geolocation API to get latitude and longitude 
    response = requests.get(f"http://ip-api.com/json")
    data = response.json()
    latitude = data["lat"]
    longitude = data["lon"]
    
    device = {"user_agent": user_agent, "language": language, "latitude": latitude, "longitude": longitude, "device_name": device_name}
    return device