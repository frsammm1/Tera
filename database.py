import time
import motor.motor_asyncio
from config import Config

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users

    def new_user(self, id):
        return dict(
            id=id,
            credits=3,
            expiry_date=0,
            is_banned=False
        )

    async def add_user(self, id):
        user = await self.col.find_one({'id': int(id)})
        if not user:
            user = self.new_user(id)
            await self.col.insert_one(user)
        return user

    async def get_user(self, id):
        user = await self.col.find_one({'id': int(id)})
        if not user:
             # Auto-create if not found to ensure consistency
            user = await self.add_user(id)
        return user

    async def get_all_users(self):
        return self.col.find({})

    async def reduce_credit(self, id):
        if id == Config.ADMIN_ID:
            return True

        user = await self.get_user(id)
        if user['credits'] > 0:
            await self.col.update_one({'id': int(id)}, {'$inc': {'credits': -1}})
            return True
        return False

    async def update_expiry(self, id, seconds):
        current_time = time.time()
        # If already active, add to existing expiry, else start from now
        user = await self.get_user(id)
        current_expiry = user.get('expiry_date', 0)

        if current_expiry > current_time:
            new_expiry = current_expiry + seconds
        else:
            new_expiry = current_time + seconds

        await self.col.update_one({'id': int(id)}, {'$set': {'expiry_date': new_expiry, 'is_banned': False}})
        return new_expiry

    async def check_access(self, id):
        if id == Config.ADMIN_ID:
            return True, "ADMIN"

        user = await self.get_user(id)
        if user.get('is_banned', False):
            return False, "BANNED"

        # Check validity first
        if user.get('expiry_date', 0) > time.time():
            return True, "PREMIUM"

        # Check credits
        if user.get('credits', 0) > 0:
            return True, "FREE"

        return False, "EXPIRED"

    async def ban_user(self, id):
        await self.col.update_one({'id': int(id)}, {'$set': {'is_banned': True}})

    async def revoke_access(self, id):
        # Revokes all access
        await self.col.update_one({'id': int(id)}, {'$set': {'is_banned': True, 'credits': 0, 'expiry_date': 0}})

    async def unban_user(self, id):
        await self.col.update_one({'id': int(id)}, {'$set': {'is_banned': False}})

db = Database(Config.MONGO_URI, "TeraboxBot")
