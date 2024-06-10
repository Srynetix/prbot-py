# Architecture

prbot-py is a simple GitHub bot made in Python, managed with Poetry.

Most of the code is in the `prbot` package.

## Files overview

Here's the top-level view of the main files, ignoring misc. files like Docker or devenv:

```
.
├── docs/              Various documentations for the project
├── prbot/             The main Python project folder
├── tests/             Tests (duh!)
├── manage.py          Project entrypoint
├── pyproject.toml     The project definition file
└── poetry.lock        The lockfile for Poetry
```

## `prbot` module overview

Here's the tree view:

```
.
└── prbot/             
    ├── cli/           The CLI modules (for command-line management)
    ├── config/        The configuration module (using pydantic-settings)
    ├── core/          The core module (main business logic)
    ├── injection/     The injection system (using inject)
    ├── modules/       The various "external" modules
    ├── server/        The HTTP server (using FastAPI)
    ├── utils/         Various utilities
    └── __init__.py
```

The app is built with "Clean Architecture" principles in mind, so the database related code does not bleed into the business logic.