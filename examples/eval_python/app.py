from service import greet


def main():
    try:
        return greet("CodeTrace")
    except ValueError:
        return "Invalid name"


if __name__ == "__main__":
    print(main())
