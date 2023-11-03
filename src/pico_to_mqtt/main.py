from pico_to_mqtt.config import get_config


def return_three_for_pytest_flow_check() -> int:
    return 3


def print_hello_world() -> None:
    print("Hello, world! hello, Dan")


def main():
    configuration = get_config()
    print(f"configuration: {configuration}")


if __name__ == "__main__":
    main()
