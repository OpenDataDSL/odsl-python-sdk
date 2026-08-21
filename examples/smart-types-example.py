"""Example: computed/derived data -- EventCurve, SmartCurve, EventTimeSeries, SmartTimeSeries.

Builds on full-example.py: creates an object with a plain curve, a plain
time series, and two groups of events (the same way full-example.py does),
then attaches four more fields built with odsl.types' "computed" builders --
ones that don't carry their own values, but tell the server how to derive
them from data that already exists:

* `EventCurve`/`EventTimeSeries` are computed from an event group -- here,
  a small set of per-tenor forward-price events for the curve, and the
  same sensor-reading events from full-example.py for the time series.
* `SmartCurve`/`SmartTimeSeries` are computed from a formula expression
  against another curve/time series -- here, the plain CURVE/TIMESERIES
  fields created in step 1, scaled by a constant.

Usage:
    Create a .env file (see README.md) with the following variables set for
    a service principal that has permission to write private objects and
    events:

        tid=<azure-ad-tenant-id>
        appid=<application-client-id>
        secret=<client-secret>

    Then run:

        python examples/smart-types-example.py
"""

import os

from dotenv import load_dotenv
from odsl import sdk, types

load_dotenv()

odsl = sdk.ODSL()
odsl.setStage("dev")
odsl.loginWithSecret(os.getenv('tid'), os.getenv('appid'), os.getenv('secret'))

# --- 1. Base data: an object with a plain curve and time series -------------
# Same pattern as full-example.py -- see that script for more detail on
# building/attaching these.
object_id = 'AAA.PYTHON-SMART-EXAMPLE'
obj = types.Object(object_id).set('name', 'Python Smart-Types Example')
odsl.update('object', 'private', obj.data)

curve = (
    types.Curve('2026-08-20', '#REOMHENG', id='CURVE')
    .set_name('Base curve')
    .set_currency('EUR')
    .add('M01', 1.4)
    .add('M02', 2.2)
    .add('M03', 3.3)
)
timeseries = (
    types.TimeSeries(id='TIMESERIES', calendar='DAILY', start='2026-08-01')
    .set_name('Base time series')
    .set_units('MWh')
    .add('2026-08-01', 10.5)
    .add('2026-08-02', 11.2)
)
obj = odsl.get('object', 'private', object_id)
obj['CURVE'] = curve.data
obj['TIMESERIES'] = timeseries.data
odsl.update('object', 'private', obj)

# --- 2. Two groups of events -------------------------------------------------
# 'FORWARDS': one event per tenor, shaped for EventCurve below -- each has a
# 'tenor' property (the maturity code) and a 'price' property (the value).
forwards_key = f'{object_id}:FORWARDS'
forwards = [
    types.Event(forwards_key, f'AAA-SMART-EXAMPLE-FWD-{i}', '2026-08-20T00:00:00Z')
    .set_property('tenor', tenor)
    .set_property('price', price)
    for i, (tenor, price) in enumerate([('M01', 1.5), ('M02', 2.3), ('M03', 3.4)], start=1)
]
odsl.update('event', 'private', types.events_dataframe(forwards))

# 'READINGS': timestamped sensor readings, shaped for EventTimeSeries below --
# each has a 'value' property.
readings_key = f'{object_id}:READINGS'
readings = [
    types.Event(readings_key, f'AAA-SMART-EXAMPLE-READING-{i}', eventtime)
    .set_property('value', value)
    for i, (eventtime, value) in enumerate([
        ('2026-08-20T00:00:00Z', 41.2),
        ('2026-08-20T00:15:00Z', 42.8),
        ('2026-08-20T00:30:00Z', 40.1),
    ], start=1)
]
odsl.update('event', 'private', types.events_dataframe(readings))

# --- 3. EventCurve and EventTimeSeries, computed from those events ----------
# EventCurve reads 'price' as the value and 'tenor' as the tenor/maturity
# code off each event under 'FORWARDS' -- there's no add()/contracts here,
# the server derives them.
event_curve = (
    types.EventCurve(forwards_key, 'price', 'tenor', '#REOMHENG', id='EVENT_CURVE')
    .set_name('Curve built from FORWARDS events')
    .set_currency('EUR')
)

# EventTimeSeries reads 'value' off each event under 'READINGS'. The
# observations are derived entirely server-side -- there's no add()/data
# here at all, unlike EventCurve which at least keeps precision/name-style
# metadata setters in common with Curve; sending a 'data' key (even an
# empty one) here gets rejected with [8003] Cannot contain data.
event_timeseries = (
    types.EventTimeSeries(readings_key, 'value', id='EVENT_TIMESERIES', calendar='DAILY', start='2026-08-20')
    .set_name('Time series built from READINGS events')
)

# --- 4. SmartCurve and SmartTimeSeries, computed from CURVE/TIMESERIES ------
# Both reference the plain curve/time series from step 1 as `BASE` in a
# formula expression -- the base curve/time series id and the expression
# are both required positional args (the server rejects a SmartCurve/
# SmartTimeSeries missing either with [8003]), passed straight through to
# set_base_curve()/set_base_time_series() and set_expression().
#
# The base id has to be the *field's* full reference id -- OBJECTID:FIELDNAME
# -- not just the field name on its own ('CURVE'/'TIMESERIES' alone resolve
# to nothing and the smart curve/time series won't compute).
smart_curve = (
    types.SmartCurve(f'{object_id}:CURVE', 'BASE * 1.1', id='SMART_CURVE')
    .set_name('Smart curve: CURVE scaled by 10%')
    .set_currency('EUR')
)
smart_timeseries = (
    types.SmartTimeSeries(f'{object_id}:TIMESERIES', 'BASE * 2', id='SMART_TIMESERIES', calendar='DAILY')
    .set_name('Smart time series: TIMESERIES doubled')
)

# --- 5. Attach all four as new fields and send the object back --------------
obj = odsl.get('object', 'private', object_id)
obj['EVENT_CURVE'] = event_curve.data
obj['EVENT_TIMESERIES'] = event_timeseries.data
obj['SMART_CURVE'] = smart_curve.data
obj['SMART_TIMESERIES'] = smart_timeseries.data
odsl.update('object', 'private', obj)

print("Object with computed curve/time series fields attached:")
print(odsl.get('object', 'private', object_id))
