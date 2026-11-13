"""Private, disposable real PostgreSQL; never connect to an existing database."""

import os
import secrets
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass

import pytest
from sqlalchemy import URL, Engine, create_engine, text
from sqlalchemy.exc import OperationalError

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"


def docker(*args):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="session")
def postgres():
    name = "sentinel-sn003-" + secrets.token_hex(6)
    database = "sentinel_demo_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    admin = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="sn003-env-") as env_file:
        os.chmod(env_file.name, 0o600)
        env_file.write(f"POSTGRES_PASSWORD={password}\nPOSTGRES_DB={database}\n")
        env_file.flush()
        try:
            docker(
                "run",
                "--detach",
                "--name",
                name,
                "--rm",
                "--publish",
                "127.0.0.1::5432",
                "--tmpfs",
                "/var/lib/postgresql/data:rw,nosuid,size=256m",
                "--env-file",
                env_file.name,
                IMAGE,
            )
            host_port = int(docker("port", name, "5432/tcp").rsplit(":", 1)[1])
            url = URL.create(
                "postgresql+psycopg",
                username="postgres",
                password=password,
                host="127.0.0.1",
                port=host_port,
                database=database,
                query={"connect_timeout": "2"},
            )
            admin = create_engine(url, hide_parameters=True)
            deadline = time.monotonic() + 45
            while True:
                try:
                    with admin.connect() as connection:
                        connection.execute(text("SELECT 1"))
                    break
                except OperationalError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Private PostgreSQL did not become ready") from None
                    time.sleep(0.2)
            with admin.begin() as connection:
                connection.execute(text("REVOKE ALL ON SCHEMA public FROM PUBLIC"))
                connection.execute(text(f'REVOKE ALL ON DATABASE "{database}" FROM PUBLIC'))
            yield admin
        finally:
            if admin is not None:
                admin.dispose()
            # --rm plus tmpfs ensures no fixture database or volume survives.
            subprocess.run(
                ["docker", "rm", "--force", name],
                capture_output=True,
                timeout=30,
                check=False,
            )


@dataclass
class Service:
    schema: str
    owner_role: str
    runtime_role: str
    owner: Engine
    runtime: Engine


@pytest.fixture
def services(postgres):
    engines = []

    @contextmanager
    def provision(label):
        suffix = secrets.token_hex(4)
        schema = f"demo_{label}_{suffix}"
        owner_role = "owner_" + suffix
        runtime_role = "runtime_" + suffix
        password = secrets.token_hex(24)
        with postgres.begin() as connection:
            for role in (owner_role, runtime_role):
                connection.exec_driver_sql(
                    f"CREATE ROLE \"{role}\" LOGIN PASSWORD '{password}' "
                    "NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT"
                )
                connection.exec_driver_sql(
                    f'GRANT CONNECT ON DATABASE "{postgres.url.database}" TO "{role}"'
                )
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}" AUTHORIZATION "{owner_role}"')
        owner = create_engine(
            postgres.url.set(username=owner_role, password=password),
            hide_parameters=True,
        )
        runtime = create_engine(
            postgres.url.set(username=runtime_role, password=password),
            hide_parameters=True,
            pool_size=1,
            max_overflow=0,
        )
        engines.extend([owner, runtime])
        yield Service(schema, owner_role, runtime_role, owner, runtime)

    yield provision
    for engine in engines:
        engine.dispose()
