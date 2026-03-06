"""Database management CLI tool."""
import asyncio
import sys
import argparse
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import init_db, close_db
from scripts.seed_database import seed_all


async def reset_database():
    """Drop all tables and recreate them."""
    print("⚠️  WARNING: This will delete all data!")
    confirm = input("Type 'yes' to confirm: ")
    if confirm.lower() != "yes":
        print("Aborted.")
        return

    from app.db.base import Base
    from app.db.session import engine

    print("Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    print("Creating all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Database reset complete!")


async def seed_database():
    """Seed database with test data."""
    print("Seeding database with test data...")
    await seed_all()
    print("✅ Seeding complete!")


async def init_database():
    """Initialize database (create tables)."""
    print("Initializing database...")
    await init_db()
    print("✅ Database initialized!")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Database management tool")
    parser.add_argument(
        "command",
        choices=["init", "seed", "reset"],
        help="Command to execute",
    )

    args = parser.parse_args()

    try:
        if args.command == "init":
            await init_database()
        elif args.command == "seed":
            await seed_database()
        elif args.command == "reset":
            await reset_database()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
