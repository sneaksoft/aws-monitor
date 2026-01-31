"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from moto import mock_aws

from app.main import app
from app.database import Base, get_db
from app.cache import init_cache, close_cache, get_cache, CacheService
from app.dependencies import get_current_user, get_cache_service
from app.models.database import User

# Test database URL (SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user."""
    user = User(
        email="test@example.com",
        cognito_sub="test-sub-123",
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def readonly_user(db_session: AsyncSession) -> User:
    """Create readonly test user."""
    user = User(
        email="readonly@example.com",
        cognito_sub="readonly-sub-123",
        role="readonly",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    test_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return test_user

    async def override_get_cache_service():
        # Return a mock cache service
        from unittest.mock import AsyncMock

        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        return mock_cache

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_cache_service] = override_get_cache_service

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def readonly_client(
    db_session: AsyncSession,
    readonly_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with readonly user."""

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return readonly_user

    async def override_get_cache_service():
        from unittest.mock import AsyncMock

        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        return mock_cache

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_cache_service] = override_get_cache_service

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials."""
    import os

    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def mock_ec2(aws_credentials):
    """Mock EC2 service."""
    with mock_aws():
        import boto3

        ec2 = boto3.client("ec2", region_name="us-east-1")

        # Create a VPC and subnet
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        vpc_id = vpc["Vpc"]["VpcId"]

        subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")
        subnet_id = subnet["Subnet"]["SubnetId"]

        # Create test instances
        instances = ec2.run_instances(
            ImageId="ami-12345678",
            MinCount=2,
            MaxCount=2,
            InstanceType="t2.micro",
            SubnetId=subnet_id,
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": "test-instance"},
                        {"Key": "Environment", "Value": "test"},
                    ],
                }
            ],
        )

        yield {
            "ec2": ec2,
            "vpc_id": vpc_id,
            "subnet_id": subnet_id,
            "instance_ids": [i["InstanceId"] for i in instances["Instances"]],
        }


@pytest.fixture
def mock_s3(aws_credentials):
    """Mock S3 service."""
    with mock_aws():
        import boto3

        s3 = boto3.client("s3", region_name="us-east-1")

        # Create test buckets
        s3.create_bucket(Bucket="test-bucket-1")
        s3.create_bucket(Bucket="test-bucket-2")

        # Add tags to first bucket
        s3.put_bucket_tagging(
            Bucket="test-bucket-1",
            Tagging={
                "TagSet": [
                    {"Key": "Environment", "Value": "test"},
                ]
            },
        )

        yield {"s3": s3, "buckets": ["test-bucket-1", "test-bucket-2"]}
