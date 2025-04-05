# Don't Remove Credit @KR_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_KR
# Ask Doubt on telegram @KingKR01

import pymongo
from pymongo.errors import PyMongoError
from info import OTHER_DB_URI, DATABASE_NAME
import logging
from typing import Union, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# Configure connection with timeout and retry
myclient = pymongo.MongoClient(
    OTHER_DB_URI,
    connectTimeoutMS=5000,
    socketTimeoutMS=30000,
    serverSelectionTimeoutMS=5000,
    retryWrites=True,
    retryReads=True
)
mydb = myclient.get_database(DATABASE_NAME)
mycol = mydb.get_collection('CONNECTION')

def validate_ids(user_id: Union[int, str], group_id: Union[int, str]) -> bool:
    """Validate user and group IDs before database operations"""
    try:
        int(user_id)
        int(group_id)
        return True
    except (ValueError, TypeError):
        logger.error(f"Invalid ID format: user_id={user_id}, group_id={group_id}")
        return False

async def add_connection(group_id: Union[int, str], user_id: Union[int, str]) -> bool:
    """Add connection with validation and error handling"""
    if not validate_ids(user_id, group_id):
        return False

    try:
        query = mycol.find_one(
            {"_id": user_id},
            {"_id": 0, "active_group": 0}
        )
        if query is not None:
            group_ids = [x["group_id"] for x in query["group_details"]]
            if group_id in group_ids:
                return False

        group_details = {"group_id": group_id}
        data = {
            '_id': user_id,
            'group_details': [group_details],
            'active_group': group_id,
        }

        if mycol.count_documents({"_id": user_id}) == 0:
            result = mycol.insert_one(data)
            return result.acknowledged
        else:
            result = mycol.update_one(
                {'_id': user_id},
                {
                    "$push": {"group_details": group_details},
                    "$set": {"active_group": group_id}
                }
            )
            return result.modified_count > 0

    except PyMongoError as e:
        logger.error(f"Database error in add_connection: {str(e)}")
        return False

        
async def active_connection(user_id: Union[int, str]) -> Optional[int]:
    """Get active connection with validation and error handling"""
    if not validate_ids(user_id, "dummy_group_id"):  # Just validate user_id format
        return None

    try:
        query = mycol.find_one(
            {"_id": user_id},
            {"_id": 0, "group_details": 0}
        )
        if not query:
            return None

        group_id = query['active_group']
        return int(group_id) if group_id is not None else None
        
    except PyMongoError as e:
        logger.error(f"Database error in active_connection: {str(e)}")
        return None


async def all_connections(user_id: Union[int, str]) -> Optional[list]:
    """Get all connections with validation and error handling"""
    if not validate_ids(user_id, "dummy_group_id"):  # Just validate user_id format
        return None

    try:
        query = mycol.find_one(
            {"_id": user_id},
            {"_id": 0, "active_group": 0}
        )
        if query is not None:
            return [x["group_id"] for x in query["group_details"]]
        return None
        
    except PyMongoError as e:
        logger.error(f"Database error in all_connections: {str(e)}")
        return None


async def if_active(user_id: Union[int, str], group_id: Union[int, str]) -> bool:
    """Check if connection is active with validation and error handling"""
    if not validate_ids(user_id, group_id):
        return False

    try:
        query = mycol.find_one(
            {"_id": user_id},
            {"_id": 0, "group_details": 0}
        )
        return query is not None and query['active_group'] == group_id
        
    except PyMongoError as e:
        logger.error(f"Database error in if_active: {str(e)}")
        return False


async def make_active(user_id, group_id):
    update = mycol.update_one(
        {'_id': user_id},
        {"$set": {"active_group" : group_id}}
    )
    return update.modified_count != 0


async def make_inactive(user_id):
    update = mycol.update_one(
        {'_id': user_id},
        {"$set": {"active_group" : None}}
    )
    return update.modified_count != 0


async def delete_connection(user_id, group_id):

    try:
        update = mycol.update_one(
            {"_id": user_id},
            {"$pull" : { "group_details" : {"group_id":group_id} } }
        )
        if update.modified_count == 0:
            return False
        query = mycol.find_one(
            { "_id": user_id },
            { "_id": 0 }
        )
        if len(query["group_details"]) >= 1:
            if query['active_group'] == group_id:
                prvs_group_id = query["group_details"][len(query["group_details"]) - 1]["group_id"]

                mycol.update_one(
                    {'_id': user_id},
                    {"$set": {"active_group" : prvs_group_id}}
                )
        else:
            mycol.update_one(
                {'_id': user_id},
                {"$set": {"active_group" : None}}
            )
        return True
    except Exception as e:
        logger.exception(f'Some error occurred! {e}', exc_info=True)
        return False

