# prbot 🤖🐍

Simple GitHub bot to handle pull requests for you when you have other things to do.

## Features

- Manage a global overview of each pull request, using "step labels" to easily see what's going on
    - You can also track these labels using external applications (as JIRA) to automate tasks
- Handle QA / check status on a pull request
- Handle automerge following specific rules or on demand
- Handle specific repository rules for more granularity

## How to run

You need:

- [Python] 3.12+ and [Poetry]
- A [PostgreSQL] database
- A [Redis] instance
- A configured environment file
- *Optional*: [Just], to run tasks

> **Note**: if you use Nix and `direnv`, you can use the included `.envrc` / `shell.nix` file to automatically setup Python/Git/Just.

To configure your environment file, copy the `.env.dist` file to a `.env` file in the project root, and fill the blanks.

Then, you can setup everything by doing:

```sh
# Install the dependencies
poetry install

# Create the tables
poetry run manage aerich upgrade

# Run the application server
poetry run manage serve
```

The server should be accessible at https://localhost:8000.

> **Note**: You can override the port and IP using the `PRBOT_SERVER_PORT` / `PRBOT_SERVER_IP` environment variables.

You can also use the included `Dockerfile` to containerize the application.

## Credits

This project mainly uses the following technologies:

- [Python], as the main programming language,
- [Poetry], for better Python project management,
- [Typer], for CLI parsing,
- [FastAPI], for the HTTP server,
- [Pydantic], for data validation,
- [inject], as a dependency injector,
- [TortoiseORM] and [aerich], for the ORM / database migration tool. 

[aerich]: https://github.com/tortoise/aerich/
[FastAPI]: https://fastapi.tiangolo.com/
[inject]: https://github.com/ivankorobkov/python-inject/
[Just]: https://github.com/casey/just/
[Poetry]: https://python-poetry.org/
[PostgreSQL]: https://postgresql.org/
[Pydantic]: https://docs.pydantic.dev/latest/ 
[Python]: https://www.python.org/
[Redis]: https://redis.io/
[TortoiseORM]: https://tortoise.github.io/
[Typer]: https://typer.tiangolo.com/