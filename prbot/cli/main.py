import os
from pathlib import Path
from typing import Annotated

import typer
from rich import print

from prbot.cli import account, pull_request, repository
from prbot.cli.common import async_command, build_typer
from prbot.config.settings import get_global_settings
from prbot.injection import inject_instance
from prbot.modules.database.import_export import ImportExportProcessor
from prbot.modules.lock import LockClient

app = build_typer()
app.add_typer(account.app, name="account", help="Manage accounts.")
app.add_typer(repository.app, name="repository", help="Manage repositories.")
app.add_typer(pull_request.app, name="pull-request", help="Manage pull requests.")


@app.command()
def dev() -> None:
    """Start the development server."""
    settings = get_global_settings()

    cmd = [
        "uvicorn",
        "--host",
        str(settings.server_ip),
        "--port",
        str(settings.server_port),
        "--reload",
        "prbot.server.main:app",
    ]
    os.execvp(cmd[0], cmd)


@app.command()
def serve() -> None:
    """Start the production server."""
    settings = get_global_settings()

    cmd = [
        "gunicorn",
        "-k",
        "uvicorn.workers.UvicornWorker",
        "--bind",
        f"{settings.server_ip}:{settings.server_port}",
        "prbot.server.main:app",
    ]
    os.execvp(cmd[0], cmd)


@app.command()
def aerich(args: list[str]) -> None:
    """Proxy to the aerich CLI."""
    import subprocess

    subprocess.call(["aerich", *args])


@async_command(app)
async def check() -> None:
    """Check availability of external dependencies."""
    lock = inject_instance(LockClient)
    if await lock.ping():
        print("[green]Lock OK[/green]")
    else:
        print("[red]Lock KO[/red]")


@async_command(app)
async def data_export(
    path: Path,
    overwrite: Annotated[bool, typer.Option(help="Overwrite existing file")] = False,
) -> None:
    """Export database items to JSON."""
    if path.exists() and not overwrite:
        print(f"[red]Output file '{path}' already exists.[/red]")
        raise typer.Exit(code=1)

    processor = ImportExportProcessor()

    with open(path, mode="wb") as fd:
        await processor.export_data(fd)


@async_command(app)
async def data_import(
    path: Path,
    compatibility: Annotated[bool, typer.Option(help="Use compatibility mode")] = False,
) -> None:
    """Import database items from JSON."""
    if not path.exists():
        print(f"[red]Import file '{path}' does not exist.[/red]")
        raise typer.Exit(code=1)

    processor = ImportExportProcessor()
    with open(path, mode="rb") as fd:
        if compatibility:
            await processor.import_data_compatibility(fd)
        else:
            await processor.import_data(fd)


@app.command()
def pem_to_var(pem_file: Path) -> None:
    """Convert a PEM file to one-line, so it can be used as an environment variable."""
    with open(pem_file, mode="r") as fd:
        data = "\\n".join(line.strip() for line in fd.readlines())
        print(f"[green]{data}[/green]")


@async_command(app)
async def crash_test() -> None:
    """Trigger a crash, to test the Sentry integration."""
    raise RuntimeError("Task failed successfully")


def run_main() -> None:
    app()


if __name__ == "__main__":
    run_main()
