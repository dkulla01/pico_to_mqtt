import asyncio
import datetime
import logging
import os
import signal
import sys
import traceback
from typing import Any, Mapping, Optional

import aiomqtt

from pico_to_mqtt.caseta.button_watcher import ButtonTracker
from pico_to_mqtt.caseta.topology import Topology, default_bridge
from pico_to_mqtt.config import AllConfig, MqttConfig, MqttCredentials, get_config
from pico_to_mqtt.event_handler import EventHandler

_LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
_HANDLER = logging.StreamHandler(stream=sys.stderr)
_HANDLER.setLevel(_LOGLEVEL)
_FORMATTER = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
_HANDLER.setFormatter(_FORMATTER)
logging.basicConfig(level=_LOGLEVEL, handlers=[_HANDLER])
LOGGER = logging.getLogger(__name__)

_TERMINATION_SIGNALS = [
    signal.SIGHUP,
    signal.SIGTERM,
    signal.SIGINT,
]


async def shutdown(
    loop: asyncio.AbstractEventLoop, signal: Optional[signal.Signals] = None
):
    if signal:
        LOGGER.info(
            "received termination signal %s. Starting to shut down.",
            signal.name,
        )
    LOGGER.info("cancelling outstanding tasks")
    tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
    for task in tasks:
        LOGGER.debug("cancelling task %s", task)
        task.cancel()
    LOGGER.info("waiting for %d tasks to be cancelled", len(tasks))
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


def handle_exception(loop: asyncio.AbstractEventLoop, context: Mapping[str, Any]):
    if "exception" in context:
        exception = context["exception"]
        LOGGER.error("caught exception %s", exception)
        if isinstance(exception, Exception):
            LOGGER.error(
                "caught exception: \n%s", "".join(traceback.format_exception(exception))
            )
    else:
        message = context["message"]
        LOGGER.info("received notification: %s", message)
    LOGGER.info("shutting down now")
    asyncio.create_task(shutdown(loop))


def new_mqtt_client(
    mqtt_config: MqttConfig, mqtt_credentials: MqttCredentials
) -> aiomqtt.Client:
    tls_params = aiomqtt.TLSParameters(
        ca_certs=mqtt_config.path_to_mqtt_client_ca.as_posix(),
        certfile=mqtt_config.path_to_mqtt_client_cert.as_posix(),
        keyfile=mqtt_config.path_to_mqtt_client_key.as_posix(),
    )
    return aiomqtt.Client(
        mqtt_config.hostname,
        mqtt_config.port,
        username=mqtt_credentials.username,
        password=mqtt_credentials.password,
        tls_params=tls_params,
    )


async def main_loop(configuration: AllConfig):
    shutdown_condition = asyncio.Condition()
    mqtt_client = new_mqtt_client(
        configuration.mqtt_config, configuration.mqtt_credentials
    )

    async with mqtt_client as context_managed_mqtt_client:
        caseta_event_handler = EventHandler(
            context_managed_mqtt_client, shutdown_condition
        )
        button_tracker = ButtonTracker(
            shutdown_condition,
            caseta_event_handler,
            configuration.button_watcher_config,
            datetime.datetime.now,
        )
        current_topology: Optional[Topology] = None
        while True:
            new_topology = Topology(
                default_bridge(configuration.caseta_config),
                shutdown_condition,
                button_tracker,
            )
            await new_topology.connect()

            if not current_topology:
                LOGGER.info("connecting an initial topology instance")
                current_topology = new_topology
                current_topology.attach_callbacks()
            elif current_topology.remotes_by_id != new_topology.remotes_by_id:
                LOGGER.info(
                    "new topoology differs from existing topology. "
                    "swapping out the old topology"
                )
                old_topology = current_topology
                current_topology = new_topology
                current_topology.attach_callbacks()
                asyncio.create_task(old_topology.close())
            else:
                LOGGER.info(
                    "the new topology is the same as the old topology. "
                    "nothing to do here"
                )

            wait_for_caseta_bridge_refresh_interval_task = asyncio.create_task(
                asyncio.sleep(
                    configuration.caseta_config.caseta_bridge_refresh_interval_sec
                )
            )
            wait_for_shutdown_condition_task = asyncio.create_task(
                wait_for_shutdown_condition(shutdown_condition)
            )
            finished_tasks, _unfinished_tasks = await asyncio.wait(
                [
                    wait_for_caseta_bridge_refresh_interval_task,
                    wait_for_shutdown_condition_task,
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if wait_for_shutdown_condition_task in finished_tasks:
                asyncio.get_running_loop().call_exception_handler(
                    {"message": "shutdown condition received"}
                )
                return


async def sleep_for_three_seconds() -> None:
    await asyncio.sleep(3)


async def wait_for_shutdown_condition(shutdown_condition: asyncio.Condition) -> None:
    async with shutdown_condition:
        await shutdown_condition.wait()


def main():
    configuration = get_config()
    loop = asyncio.new_event_loop()
    for termination_signal in _TERMINATION_SIGNALS:

        def _handle_termination_signal():
            asyncio.create_task(shutdown(loop, termination_signal))

        loop.add_signal_handler(termination_signal, _handle_termination_signal)
    loop.set_exception_handler(handle_exception)
    try:
        loop.create_task(main_loop(configuration))
        loop.run_forever()
    finally:
        loop.close()

    LOGGER.info("shutdown work complete.")


if __name__ == "__main__":
    main()
