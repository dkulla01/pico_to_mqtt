import asyncio
import logging
import os
import sys
from enum import Enum

import attrs

from pico_to_mqtt.caseta.topology import Topology, default_bridge
from pico_to_mqtt.config import AllConfig, get_config

_LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
_HANDLER = logging.StreamHandler(stream=sys.stderr)
_HANDLER.setLevel(_LOGLEVEL)
_FORMATTER = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
_HANDLER.setFormatter(_FORMATTER)
logging.basicConfig(level=_LOGLEVEL, handlers=[_HANDLER])
LOGGER = logging.getLogger(__name__)


def return_three_for_pytest_flow_check() -> int:
    return 3


def print_hello_world() -> None:
    print("Hello, world! hello, Dan")


async def consume_pico_messages(topology: Topology):
    await topology.connect()
    LOGGER.info("yay we've connected")


async def main_loop(configuration: AllConfig):
    shutdown_condition = asyncio.Condition()
    topology = Topology(default_bridge(configuration.caseta_config), shutdown_condition)

    await consume_pico_messages(topology)

def main():
    configuration = get_config()
    logging.info(f"configuration: {configuration}")

    loop = asyncio.new_event_loop()
    try:
        loop.create_task(main_loop(configuration))
        loop.run_forever()
    except KeyboardInterrupt:
        logging.info("got a keyboard interrupt")
    finally:
        loop.close()

    logging.info("we're done")


if __name__ == "__main__":
    main()
