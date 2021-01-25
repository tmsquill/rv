# Python script for monitoring temperature and operating space heaters when
# needed.

import asyncio
import click
import os
import signal
import sqlite3
import sys
import time
import traceback

from datetime import datetime
from enum import Enum
from tabulate import tabulate

# -----------------------------------------------------------------------------
# Handle situation where user attempts to run on something other than a
# Raspberry Pi.
# -----------------------------------------------------------------------------
try:

    from sense_hat import SenseHat

except ModuleNotFoundError:

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

CURRENT_TEMPERATURE = 0.0

# -----------------------------------------------------------------------------
# Core asynchronous functions.
# -----------------------------------------------------------------------------
async def loop_led_matrix_update():

    global LED_MATRIX
    global PICYCLE_STATE

    while PICYCLE_STATE == PicycleState.RUNNING:

        SENSE.set_pixels(LED_MATRIX)

        await asyncio.sleep(1)

    click.echo("Stopping LED matrix updates...")

async def loop_track_satellites():

    global LED_MATRIX
    global PICYCLE_STATE

    while PICYCLE_STATE == PicycleState.RUNNING:

        for x in range(gpsd.get_current().sats):

            if x % 2 == 0:

                idx = 0

            else:

                idx = 8

            idx = idx + (x // 2)

            if 0 <= x <= 3:

                LED_MATRIX[idx] = (255, 0, 0)

            elif 3 < x < 8:

                LED_MATRIX[idx] = (255, 255, 0)

            elif 8 <= x <= 16:

                LED_MATRIX[idx] = (0, 255, 0)

        await asyncio.sleep(1)

    click.echo("Stopping tracking satellites...")

async def loop_update_relay(temperature_lower, temperature_upper, update_interval):

    click.echo("Starting updates for relay...")

    while True:

        # Get the current temperature in celsius.
        temperature = round(SENSE.get_temperature(), 2)

        # Convert to fahrenheit.
        temperature = (temperature * 9 / 5) + 32

        # Get the current date and time.
        now = datetime.now()

        if temperature < temperature_lower: # and GPIO.is_off()

            # Turn on the GPIO.

        if temperature > temperature_upper: # and GPIO.is_on()

            # Turn off the GPIO.

        # Wait before the next update.
        time.sleep(update_interval)

    click.echo("Stopping updates for relay...")

    global LED_MATRIX
    global PICYCLE_STATE
    global SESSION_STATE

    # When run as a service, it's common to encounter SIGTERM. This is needed
    # to clear
    def sigterm_handler(signum, stack_frame):

        global PICYCLE_STATE

        PICYCLE_STATE = PicycleState.TERMINATE

    signal.signal(signal.SIGTERM, sigterm_handler)

    while PICYCLE_STATE == PicycleState.RUNNING:

        for i in range(16, 24):

            LED_MATRIX[i] = (255, 255, 255)

        if SESSION_STATE != SessionState.IN_PROGRESS:

            await asyncio.sleep(1)
            continue

        for i in range(16, 24):

            LED_MATRIX[i] = (0, 0, 255)

        # Get the current date and time, used for creating a new SQLite database.
        now = datetime.now().strftime('%Y%m%d-%H-%M-%S')

        # Connect to the SQLite database.
        db = f"{now}-picycle.sqlite"
        connection = create_connection(db)

        # Otherwise report the error and exit.
        else:

            SENSE.show_letter("E", (255, 0, 0))
            time.sleep(3)
            SENSE.clear()
            sys.exit(1)

# -----------------------------------------------------------------------------
# Controller commands.
# -----------------------------------------------------------------------------
@click.group()
def cli():

    pass

@cli.command()
@click.argument("temperature_lower")
@click.argument("temperature_upper")
@click.argument("update_interval")
@click.option("--verbose/--no-verbose", default=False)
def control(temperature_lower, temperature_upper, update_interval, verbose):

    try:

        # Run the session, consisting of asynchronous tasks.
        asyncio.run(session(temperature_lower, temperature_upper, update_interval, verbose))

    except Exception:

        # Print the contents of the traceback.
        print(trackback.print_exc())

    finally:

        # Clear the SenseHAT LED matrix.
        SENSE.clear()

async def session(temperature_lower, temperature_upper, update_interval, verbose=False):

    if verbose:

        click.echo("Session has started...")

    # Create an asynchronous task for updating the LED matrix.
    task_1 = asyncio.create_task(loop_update_led_matrix())

    # Create an asynchronous task for updating the relay.
    task_2 = asyncio.create_task(
        loop_update_relay(
            temperature_lower,
            temperature_upper,
            update_interval
        )
    )

    # Await for the tasks to complete, then exit.
    await task_1
    await task_2

    if verbose:

        click.echo("Session has ended...")

