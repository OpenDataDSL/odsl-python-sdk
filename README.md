# ODSL Python SDK

The python SDK for the [OpenDataDSL](https://opendatadsl.com) data management platform

## Usage

### Logging in and getting started

```python
from odsl import sdk

odsl = sdk.ODSL()
odsl.login()
```

### Finding master data

```python
objects = odsl.list('object', source='public', filter='source=ECB')
print(objects[0])
```

### Getting master data

```python
obj = odsl.get('object', 'public', '#ECB')
print(obj['description'])
```

### Getting a timeseries
```python
ts = odsl.get('data', 'public', '#ABN_FX.EURUSD:SPOT')
print(ts)
```

### Updating some private master data
```python
var = {
    '_id': 'AAA.PYTHON',
    'name': 'Python Example'
}
odsl.update('object', 'private', var)
```

### Reading and updating some private master data
```python
po = odsl.get('object', 'private', 'AAA.PYTHON')
po['description'] = 'Updated from Python'
odsl.update('object', 'private', po)
```
