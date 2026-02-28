"""User profile service: MongoDB-backed CRUD."""

from pymongo import MongoClient

from src.core import settings
from src.models import UserProfile


client = MongoClient(settings.USER_DB_URL)
db = client.get_default_database()
profiles = db["user_profiles"]


def get_profile(user_id: str) -> UserProfile:
    doc = profiles.find_one({"user_id": user_id}) or {"user_id": user_id}
    return UserProfile(**doc)


def upsert_profile(user_id: str, profile: UserProfile) -> UserProfile:
    data = profile.model_dump()
    data["user_id"] = user_id
    profiles.update_one({"user_id": user_id}, {"$set": data}, upsert=True)
    return UserProfile(**data)

