# Python script for monitoring temperature and operating space heaters when
# needed.

import asyncio
import click
import gpiozero
import os
import sys
import time
import traceback

from datetime import datetime
from enum import Enum

# -----------------------------------------------------------------------------
# Handle situation where user attempts to run on something other than a
# Raspberry Pi.
# -----------------------------------------------------------------------------
try:

    from sense_hat import SenseHat

except ModuleNotFoundError:

    print("Raspberry Pi with SenseHAT required.")
    sys.exit()

# Initialize the Sense HAT.
SENSE = SenseHat()

O = (0, 0, 0)
LED_MATRIX = [
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
]

# Keeps track of the current temperature in fahrenheit.
CURRENT_TEMPERATURE = 0.0

# -----------------------------------------------------------------------------
# Core asynchronous functions.
# -----------------------------------------------------------------------------
async def loop_update_led_matrix(temperature_lower, temperature_upper, update_interval):

    global CURRENT_TEMPERATURE

    click.echo("Starting updates for LED matrix...")

    while True:

        if CURRENT_TEMPERATURE < temperature_lower:

            SENSE.clear((0, 0, 255))

        elif CURRENT_TEMPERATURE > temperature_upper:

            SENSE.clear((255, 0, 0))

        else:

            SENSE.clear((255, 255, 255))

        # Wait before the next update.
        await asyncio.sleep(update_interval)

    click.echo("Stopping updates for LED matrix...")

async def loop_update_relay(temperature_lower, temperature_upper, update_interval, use_fahrenheit=False):

    global CURRENT_TEMPERATURE

    click.echo("Starting updates for relay...")

    relay = gpiozero.OutputDevice(17, active_high=True, initial_value=False)

    import random

    # Unit for printing.
    unit = "F" if use_fahrenheit else "C"

    while True:

        # Get the current temperature in celsius.
        CURRENT_TEMPERATURE = SENSE.get_temperature()

        # Convert to fahrenheit.
        if use_fahrenheit:

            CURRENT_TEMPERATURE = (CURRENT_TEMPERATURE * 9 / 5) + 32

        # TODO: Testing with random temperature.
        CURRENT_TEMPERATURE = random.randint(25, 45)

        # Print the current temperature.
        to_print = f"Current Temperature: {round(CURRENT_TEMPERATURE, 2)}°{unit}"

        if CURRENT_TEMPERATURE < temperature_lower:

            click.echo(click.style(to_print, bg="blue"))

        elif CURRENT_TEMPERATURE > temperature_upper:

            click.echo(click.style(to_print, bg="red"))

        else:

            click.echo(to_print)

        if CURRENT_TEMPERATURE < temperature_lower and relay.value == 0:

            relay.on()
            click.echo("Turning Relay On")

        if CURRENT_TEMPERATURE > temperature_upper and relay.value == 1:

            relay.off()
            click.echo("Turning Relay Off")

        # Wait before the next update.
        await asyncio.sleep(update_interval)

    click.echo("Stopping updates for relay...")

# -----------------------------------------------------------------------------
# Controller commands.
# -----------------------------------------------------------------------------
@click.group()
def cli():

    pass

@cli.command()
@click.option("--temperature-lower", default=35.0, help="Relay will be enabled below this temperature.")
@click.option("--temperature-upper", default=40.0, help="Relay will be disabled above this temperature.")
@click.option("--update-interval", default=60, help="Update interval for the controller.")
@click.option("--use-fahrenheit/--no-use-fahrenheit", default=False, help="Use fahrenheit instead of celsius.")
@click.option("--verbose/--no-verbose", default=False)
def control(temperature_lower, temperature_upper, update_interval, use_fahrenheit, verbose):

    # Sanity checks for user input.
    assert temperature_lower < temperature_upper
    assert update_interval > 0

    try:

        # Run the session, consisting of asynchronous tasks.
        asyncio.run(
            session(
                temperature_lower,
                temperature_upper,
                update_interval,
                use_fahrenheit,
                verbose
            )
        )

    except Exception:

        # Print the contents of the traceback.
        click.echo(traceback.print_exc())

    finally:

        # Clear the SenseHAT LED matrix.
        SENSE.clear()

async def session(temperature_lower, temperature_upper, update_interval, use_fahrenheit=False, verbose=False):

    if verbose:

        click.echo("Session has started...")

    # Create an asynchronous task for updating the LED matrix.
    task_1 = asyncio.create_task(
        loop_update_led_matrix(
            temperature_lower,
            temperature_upper,
            1
        )
    )

    # Create an asynchronous task for updating the relay.
    task_2 = asyncio.create_task(
        loop_update_relay(
            temperature_lower,
            temperature_upper,
            update_interval,
            use_fahrenheit
        )
    )

    # Await for the tasks to complete, then exit.
    await task_1
    await task_2

    if verbose:

        click.echo("Session has ended...")

if __name__ == '__main__':

    cli()
