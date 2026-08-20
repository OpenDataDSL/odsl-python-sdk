"""Example: update an object and attach a curve, building the JSON payloads by hand.

This is the same walkthrough as object-example.py + curve-example.py, but
skips odsl.types entirely and constructs the raw dicts that actually go
over the wire. Useful if you want to see exactly what shape the ODSL API
expects without going through the SDK's builder classes, or you're
somewhere depending on odsl.types isn't convenient.

If you'd rather not hand-maintain these shapes yourself, odsl.types.Object/
Curve build the same thing with named setters instead of dict literals --
see their docstrings for exactly which key each one writes and why (a few,
like Curve's `_merge`/`_objtype`, are named differently on the wire than
you'd guess from the server's Java field names).

Usage:
    Create a .env file (see README.md) with the following variables set for
    a service principal that has permission to write private objects:

        tid=<azure-ad-tenant-id>
        appid=<application-client-id>
        secret=<client-secret>

    Then run:

        python examples/manual-payload-example.py
"""

import os

from dotenv import load_dotenv
from odsl import sdk

load_dotenv()

odsl = sdk.ODSL()
odsl.setStage("dev")
odsl.loginWithSecret(os.getenv('tid'), os.getenv('appid'), os.getenv('secret'))

# --- 1. Update the object ----------------------------------------------------
# The 'object' service is a plain document -- '_id' plus whatever other keys
# you want, no wrapper. `update` creates it if '_id' doesn't exist yet, or
# overwrites it if it does.
object_id = 'AAA.PYTHON-MANUAL-EXAMPLE'
obj = {
    '_id': object_id,
    'name': 'Manual Python Example',
    'description': 'Created by manual-payload-example.py, without odsl.types',
}
odsl.update('object', 'private', obj)

created = odsl.get('object', 'private', object_id)
print("Created object:")
print(created)

# --- 2. Attach a curve, built as a plain dict --------------------------------
# This is the exact shape the server's VarCurveAdaptor/VarCurveDateAdaptor
# expect: '_type': 'VarCurve', an 'ondate' block with 'curveDate' and
# 'expiryCalendar', a flat 'contracts' array of {'tenor', 'value'} pairs, and
# any custom fields nested under 'properties' rather than at the top level.
curve = {
    '_type': 'VarCurve',
    '_id': 'CURVE',
    'ondate': {
        'curveDate': '2026-08-20',
        'expiryCalendar': '#REOMHENG',
    },
    'name': 'Manual example curve',
    'currency': 'EUR',
    'units': 'MWh',
    'properties': {
        'timezone': 'BST',
    },
    'contracts': [
        {'tenor': 'M01', 'value': 1.4},
        {'tenor': 'M02', 'value': 2.2},
        {'tenor': 'M03', 'value': 3.3},
        {'tenor': 'M04', 'value': 4.4},
        {'tenor': 'M05', 'value': 5.5},
        {'tenor': 'M06', 'value': 6.6},
    ],
}

# Read the object back so we don't clobber anything else on it, attach the
# curve as a new field, and send it back.
created['CURVE'] = curve
odsl.update('object', 'private', created)

print("\nObject with curve attached:")
print(odsl.get('object', 'private', object_id))
