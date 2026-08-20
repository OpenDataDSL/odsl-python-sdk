"""Example: create an object, attach a curve and a time series to it, and create some events.

A single walkthrough exercising all four builder classes in `odsl.types`
(`Object`, `Curve`, `TimeSeries`, `Event`) against a live ODSL dev
environment:

1. Creates a private object.
2. Builds a curve and a time series and attaches them as fields on that
   object (the same pattern as curve-example.py).
3. Creates a handful of events under a new event group, then reads them
   back with a filtered `list()`.

Usage:
    Create a .env file (see README.md) with the following variables set for
    a service principal that has permission to write private objects and
    events:

        tid=<azure-ad-tenant-id>
        appid=<application-client-id>
        secret=<client-secret>

    Then run:

        python examples/full-example.py
"""

import os

from dotenv import load_dotenv
from odsl import sdk, types

load_dotenv()

odsl = sdk.ODSL()
odsl.setStage("dev")
odsl.loginWithSecret(os.getenv('tid'), os.getenv('appid'), os.getenv('secret'))

# --- 1. Object --------------------------------------------------------------
# `Object` mirrors the plain-dict pattern from object-example.py, just built
# up with a fluent API instead of a dict literal.
object_id = 'AAA.PYTHON-FULL-EXAMPLE'
obj = (
    types.Object(object_id)
    .set('name', 'Full Python Example')
    .set('description', 'Created by full-example.py')
)
odsl.update('object', 'private', obj.data)
print("Created object:")
print(odsl.get('object', 'private', object_id))

# --- 2. Curve and time series ------------------------------------------------
# Both are built standalone, then attached as fields on the object -- see
# curve-example.py for the curve half of this on its own.
curve = (
    types.Curve('2026-08-20', '#REOMHENG', id='CURVE')
    .set_name('Example curve')
    .set_currency('EUR')
    .set_units('MWh')
    .set_property('timezone', 'BST')
    .add('M01', 1.4)
    .add('M02', 2.2)
    .add('M03', 3.3)
    .add('M04', 4.4)
    .add('M05', 5.5)
    .add('M06', 6.6)
)

timeseries = (
    types.TimeSeries(id='TIMESERIES', calendar='DAILY', start='2026-08-01')
    .set_name('Example time series')
    .set_currency('EUR')
    .set_units('MWh')
    .add('2026-08-01', 10.5)
    .add('2026-08-02', 11.2)
    .add('2026-08-03', 9.8)
)

# Read the object back so we don't clobber fields already on it, attach the
# curve and time series as new fields, and send it back.
obj = odsl.get('object', 'private', object_id)
obj['CURVE'] = curve.data
obj['TIMESERIES'] = timeseries.data
odsl.update('object', 'private', obj)

print("\nObject with curve and time series attached:")
print(odsl.get('object', 'private', object_id))

# --- 3. Events ----------------------------------------------------------------
# Events get appended to an array field on an existing object, named by the
# EVENTID half of an 'OBJECTID:EVENTID' key -- here that's the object we
# created in step 1, under a new 'READING' field. The event service's write
# endpoint doesn't accept an Event's JSON directly (posting that gets HTTP
# 400) -- it always expects a DataFrame-shaped body, built here with
# types.events_dataframe(). That works the same way for one event or a
# batch of many, so we build all three and send them in a single call.
event_key = f'{object_id}:READING'
readings = [
    ('2026-08-20T00:00:00Z', 41.2),
    ('2026-08-20T00:15:00Z', 42.8),
    ('2026-08-20T00:30:00Z', 40.1),
]
events = [
    types.Event(event_key, f'AAA-EXAMPLE-{i}', eventtime).set_property('value', value)
    for i, (eventtime, value) in enumerate(readings, start=1)
]
odsl.update('event', 'private', types.events_dataframe(events))

print(f"\nCreated {len(readings)} events under {event_key}")

# Read them back. The 'event' service's GET treats an 'OBJECTID:EVENTID'
# key specially -- it returns every event under that key, equivalent to
# odsl.list('event', 'private', {'_filter': '{"event": "%s"}' % event_key}).
result = odsl.get('event', 'private', event_key)
print("Events read back:")
print(result)
