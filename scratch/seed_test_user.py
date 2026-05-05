import asyncio
from app.db.session import AsyncSessionLocal
from app.models.user import User

async def create_user():
    async with AsyncSessionLocal() as db:
        # Check if user already exists
        from sqlalchemy.future import select
        stmt = select(User).where(User.id == 'local-admin')
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            print("Test user 'local-admin' already exists.")
            return

        user = User(
            id='local-admin', 
            github_id='local-123',
            username='admin_tester', 
            role='admin', 
            is_active=True
        )
        db.add(user)
        await db.commit()
        print("✅ Test user 'local-admin' created successfully!")

if __name__ == "__main__":
    asyncio.run(create_user())
