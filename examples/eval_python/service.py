from config import MAX_NAME_LENGTH


def greet(name: str) -> str:
    if not name or len(name) > MAX_NAME_LENGTH:
        raise ValueError("Invalid name")
    return f"Hello, {name}!"
