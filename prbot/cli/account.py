from rich import print

from prbot.core.models import (
    ExternalAccount,
)
from prbot.injection import inject_instance
from prbot.modules.database.repository import (
    ExternalAccountDatabase,
)
from prbot.server.crypto import create_access_token
from prbot.utils.crypto import generate_key_pair

from .account_right import app as account_rights_app
from .common import async_command, build_typer, ensure_external_account

app = build_typer()
app.add_typer(account_rights_app, name="right", help="Manage account rights.")


@async_command(app)
async def new_token(username: str) -> None:
    """
    Generate a signed JWT token for a specific external account.
    The token will have no expiration date, so to revoke access, you will need
    to rotate the RSA keys using the `rotate-keys` command.
    """
    account = await ensure_external_account(username)
    token = create_access_token(username=username, private_key=account.private_key)
    print(f"[green]{token}[/green]")


@async_command(app)
async def add(username: str) -> None:
    """Add a new external account."""
    external_account_db = inject_instance(ExternalAccountDatabase)
    key_pair = generate_key_pair()
    data = await external_account_db.create(
        ExternalAccount(
            username=username,
            private_key=key_pair.private_key,
            public_key=key_pair.public_key,
        )
    )

    print(data)


@async_command(app)
async def remove(username: str) -> None:
    """Remove an existing external account."""
    await ensure_external_account(username)

    external_account_db = inject_instance(ExternalAccountDatabase)
    await external_account_db.delete(
        username=username,
    )

    print(f"[green]Account '{username}' deleted.[/green]")


@async_command(app)
async def list() -> None:
    """List all known external accounts."""
    external_account_db = inject_instance(ExternalAccountDatabase)
    accounts = await external_account_db.all()
    if len(accounts) == 0:
        print("[yellow]No external account found.[/yellow]")
    else:
        print("External accounts:")
        for account in accounts:
            print(f" - [green]{account.username}[/green]")


@async_command(app)
async def rotate_keys(username: str) -> None:
    """Rotate RSA keys for a specific external account."""
    account = await ensure_external_account(username)

    external_account_db = inject_instance(ExternalAccountDatabase)
    key_pair = generate_key_pair()
    account.private_key = key_pair.private_key
    account.public_key = key_pair.public_key
    await external_account_db.update(account)

    print(f"[green]Keys rotated for external account '{username}'[/green]")
