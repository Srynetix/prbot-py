from prbot.version import __version__


def generate_message_footer() -> str:
    return (
        f"\n---\n" f"_Beep boop, i'm a bot!_ :robot: :snake: _(prbot-py {__version__})_"
    )
