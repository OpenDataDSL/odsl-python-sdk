# ODSL Python SDK

The Python SDK for the [OpenDataDSL](https://opendatadsl.com) data management platform.

## Installation

You can install the ODSL Python SDK from [PyPI](https://pypi.org/project/odsl/):

    pip install odsl


You can upgrade an existing install using:

    pip install odsl --upgrade

## About

This Python SDK for OpenDataDSL has the following features:

* Find any data in OpenDataDSL using the `list` method
* Retrieve any data using the `get` method
* Update any data (if you have permission) using the `update` method
* Build well-formed payloads for objects, curves, time series, computed/derived data, events, and report definitions with the `odsl.types` helpers, instead of hand-writing the JSON shapes yourself

Full, runnable walkthroughs for everything below live in the [odsl-python-sdk-demo](https://github.com/OpenDataDSL/odsl-python-sdk-demo) repository, along with setup instructions (including the `.env` file each one expects):

| Script | What it shows |
| --- | --- |
| [`object-example.py`](https://github.com/OpenDataDSL/odsl-python-sdk-demo/blob/main/object-example.py) | Create a private object, then update it |
| [`curve-example.py`](https://github.com/OpenDataDSL/odsl-python-sdk-demo/blob/main/curve-example.py) | Attach a forward curve to an object, built with `odsl.types.Curve` |
| [`full-example.py`](https://github.com/OpenDataDSL/odsl-python-sdk-demo/blob/main/full-example.py) | One walkthrough covering an object, a curve, a time series, and events, all built with `odsl.types` |
| [`smart-types-example.py`](https://github.com/OpenDataDSL/odsl-python-sdk-demo/blob/main/smart-types-example.py) | Computed/derived fields -- `EventCurve`, `SmartCurve`, `EventTimeSeries`, `SmartTimeSeries` |
| [`report-example.py`](https://github.com/OpenDataDSL/odsl-python-sdk-demo/blob/main/report-example.py) | Define a scheduled report with `odsl.types.Report` |
| [`manual-payload-example.py`](https://github.com/OpenDataDSL/odsl-python-sdk-demo/blob/main/manual-payload-example.py) | The same object/curve update as above, with the JSON payloads written out by hand instead of using `odsl.types` |

## Usage

### Logging in and getting started

```python
from odsl import sdk

odsl = sdk.ODSL()
odsl.login()
```

`login()` triggers an interactive Microsoft sign-in the first time, then reuses a cached token on subsequent runs. It's the right choice for scripts a person runs themselves.

### Logging in using a client secret

For unattended/service-to-service use (scheduled jobs, CI, servers), authenticate as an application instead:

```python
from odsl import sdk

odsl = sdk.ODSL()
odsl.loginWithSecret(tenant_id, client_id, secret)
```

### Logging in using an API key

```python
from odsl import sdk

odsl = sdk.ODSL()
odsl.loginWithAPIKey(userid, apikey)
```

### Pointing at a different environment

By default the SDK talks to the production API. To target the dev environment instead (useful while testing):

```python
odsl = sdk.ODSL()
odsl.setStage('dev')          # or 'local' for http://localhost:7071
odsl.loginWithSecret(tenant_id, client_id, secret)
```

### Finding master data

```python
objects = odsl.list('object', source='public', params={'source': 'ECB'})
print(objects[0])
```

`list` also accepts query params like `_filter`, `_sort`, `_limit`, `_skip`, and `_aggregate` for more targeted searches.

### Getting master data

```python
obj = odsl.get('object', 'public', '#ECB')
print(obj['description'])
```

### Getting a time series

```python
ts = odsl.get('data', 'public', '#ABN_FX.EURUSD:SPOT', {'_range': 'from(2024-07-01)'})
print(ts)
```

### Getting a forward curve

```python
id = '#AEMO.EL.AU.NEM.NSW1.FORECAST:DEMAND:2024-07-15'
curve = odsl.get('data', 'public', id)
for c in curve['contracts']:
    print(c['tenor'] + ' - ' + str(c['value']))
```

### Creating and updating private master data

`update` is used for both creates and updates: if the `_id` you send doesn't exist yet it's created, otherwise it's overwritten with whatever fields you send. Read the record back first if you want to change one field without clobbering the rest:

```python
# Create
obj = {
    '_id': 'AAA.PYTHON',
    'name': 'Python Example',
}
odsl.update('object', 'private', obj)

# Update, preserving the fields already on the object
obj = odsl.get('object', 'private', 'AAA.PYTHON')
obj['description'] = 'Updated from Python'
odsl.update('object', 'private', obj)
```

If a call fails, the SDK prints the server's `x-odsl-error` response header automatically (e.g. `ODSL error 400: [5005] Update Error: ...`) to help explain what went wrong, in addition to whatever `get`/`update` themselves return.

### Building payloads with `odsl.types`

Writing the raw JSON for a curve, time series, or event by hand means matching the server's wire format exactly -- including a few fields that are named differently on the wire than you'd expect (see each class's docstring for specifics). `odsl.types` provides fluent builder classes for the common shapes instead, so you don't have to look those up each time:

```python
from odsl import sdk, types

odsl = sdk.ODSL()
odsl.setStage('dev')
odsl.loginWithSecret(tenant_id, client_id, secret)

# A plain object
obj = types.Object('AAA.PYTHON-EXAMPLE').set('name', 'Python Example')
odsl.update('object', 'private', obj.data)

# A forward curve, attached to that object
curve = (
    types.Curve('2026-08-20', '#REOMHENG', id='CURVE')
    .set_name('Example curve')
    .set_currency('EUR')
    .add('M01', 1.4)
    .add('M02', 2.2)
    .add('M03', 3.3)
)
obj = odsl.get('object', 'private', 'AAA.PYTHON-EXAMPLE')
obj['CURVE'] = curve.data
odsl.update('object', 'private', obj)

# A time series, attached the same way
timeseries = (
    types.TimeSeries(id='TIMESERIES', calendar='DAILY', start='2026-08-01')
    .set_units('MWh')
    .add('2026-08-01', 10.5)
    .add('2026-08-02', 11.2)
)
obj['TIMESERIES'] = timeseries.data
odsl.update('object', 'private', obj)
```

Every setter returns the builder itself, so a curve, time series, or object can be built as one chained expression, as shown above.

`odsl.types.Object`/`Curve`/`TimeSeries`/`Event` mirror the server's `VarSimpleObject`/`VarCurve`/`VarTimeSeries`/`VarEvent` shapes; see each class's docstring in [`odsl/types.py`](https://github.com/OpenDataDSL/odsl-python-sdk/blob/master/odsl/types.py) for the full list of setters and which wire key each one writes -- including `EventCurve`, `SmartCurve`, `EventTimeSeries`, `SmartTimeSeries`, and `Report`, covered below.

### Writing events

Events are appended to a named array field on an existing object -- e.g. a `READING` field on `AAA.PYTHON-EXAMPLE`, addressed as `AAA.PYTHON-EXAMPLE:READING`. Unlike `object`/`data` writes, the `event` service's write endpoint expects a small table (the same shape as `pandas.DataFrame.to_json(orient="split")`), not a single event's JSON directly -- `odsl.types.events_dataframe()` builds that for you from one or more `Event` builders, whether you're writing a single event or a batch:

```python
event_key = 'AAA.PYTHON-EXAMPLE:READING'
events = [
    types.Event(event_key, 'READING-1', '2026-08-20T00:00:00Z').set_property('value', 41.2),
    types.Event(event_key, 'READING-2', '2026-08-20T00:15:00Z').set_property('value', 42.8),
]
odsl.update('event', 'private', types.events_dataframe(events))

# Reading a key back returns every event under it
readings = odsl.get('event', 'private', event_key)
```

See [`full-example.py`](https://github.com/OpenDataDSL/odsl-python-sdk-demo/blob/main/full-example.py) for this in the context of a full object/curve/time-series/event walkthrough, and the `Event`/`events_dataframe` docstrings in [`odsl/types.py`](https://github.com/OpenDataDSL/odsl-python-sdk/blob/master/odsl/types.py) for the details of the required fields.

### Computed curves and time series

Alongside `Curve`/`TimeSeries` (which carry their own explicit values), `odsl.types` has four builders for fields the server computes for you instead:

* `EventCurve`/`EventTimeSeries` derive their values from an event group -- the same kind of events `Event`/`events_dataframe()` write -- reading one property off each event as the value (and, for a curve, another as the tenor/maturity code). Neither carries an explicit `data`/`contracts` field -- the server rejects one being present at all, even empty (`[8003] Invalid update ... Cannot contain data/contracts`), since the whole point is that it's derived, not supplied.
* `SmartCurve`/`SmartTimeSeries` derive their values from a formula expression against another curve/time series as `BASE`, optionally with a script layered on top. The base curve/time series id and the expression are both required arguments -- the server rejects either being missing the same way. The base id has to be the referenced field's full `OBJECTID:FIELDNAME` reference id (the same id `odsl.get('data', source, id)` would read it back with) -- just the field name on its own resolves to nothing and the curve/time series won't compute.

All four attach to an object as a field exactly like `Curve`/`TimeSeries` do:

```python
# EventCurve: built from 'tenor'/'price' properties on events under FORWARDS
event_curve = (
    types.EventCurve('AAA.PYTHON-EXAMPLE:FORWARDS', 'price', 'tenor', '#REOMHENG', id='EVENT_CURVE')
    .set_currency('EUR')
)

# SmartCurve: the object's own CURVE field, scaled by a formula -- note the
# base id is 'AAA.PYTHON-EXAMPLE:CURVE', not just 'CURVE'
smart_curve = types.SmartCurve('AAA.PYTHON-EXAMPLE:CURVE', 'BASE * 1.1', id='SMART_CURVE')

obj = odsl.get('object', 'private', 'AAA.PYTHON-EXAMPLE')
obj['EVENT_CURVE'] = event_curve.data
obj['SMART_CURVE'] = smart_curve.data
odsl.update('object', 'private', obj)
```

See [`smart-types-example.py`](https://github.com/OpenDataDSL/odsl-python-sdk-demo/blob/main/smart-types-example.py) for the full walkthrough, including `EventTimeSeries`/`SmartTimeSeries`, and each class's docstring in [`odsl/types.py`](https://github.com/OpenDataDSL/odsl-python-sdk/blob/master/odsl/types.py) for the rest of their setters.

### Defining a report

Unlike everything else in this section, a report definition isn't a field attached to an object -- `types.Report` builds a `reportconfig` record and is written to its own service:

```python
report = (
    types.Report('AAA.PYTHON-REPORT', name='Python Example Report')
    .set_script('#MyReportScript')
    .set_category('Examples')
    .set_cron('0 6 * * MON *')
)
odsl.update('reportconfig', 'private', report.data)
```

This creates the report's *definition* -- what produces it, and on what schedule -- not a generated result; see [`report-example.py`](https://github.com/OpenDataDSL/odsl-python-sdk-demo/blob/main/report-example.py) and `Report`'s docstring in [`odsl/types.py`](https://github.com/OpenDataDSL/odsl-python-sdk/blob/master/odsl/types.py) for more.

`set_cron`'s format is worth calling out explicitly, since getting it wrong fails in a confusing way: it's *not* standard 5-field unix cron -- the server requires a 6th field for the year (`*` for "every year", as above), and rejects a 5-field expression like `'0 6 * * MON'`. That rejection happens server-side *before* the report is written, and `update` doesn't raise on error, so a bad cron expression means the report silently never gets created -- the first sign of trouble is usually an unrelated-looking `404 ... Not Found` from a later `get`, not an error about the cron itself. `Report.set_cron` raises a `ValueError` up front if the expression doesn't have 6 or 7 fields, specifically to catch this before it gets that far.

### Skipping `odsl.types` and building payloads by hand

If you'd rather not depend on `odsl.types` -- or just want to see exactly what's going over the wire -- every example above has a plain-dict equivalent; see [`manual-payload-example.py`](https://github.com/OpenDataDSL/odsl-python-sdk-demo/blob/main/manual-payload-example.py) for the object + curve update written out as raw dicts.
