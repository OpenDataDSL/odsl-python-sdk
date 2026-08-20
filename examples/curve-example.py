"""Example: add a curve field to a private object via the object service.

Builds on example-create-update-object.py: it attaches a `VarCurve`-shaped
field (built with the `odsl.types.Curve`/`Contract` helpers) to the object
created there, then confirms it saved by reading the object back.

Usage:
    Create a .env file (see README.md) with the following variables set for
    a service principal that has permission to write private objects:

        tid=<azure-ad-tenant-id>
        appid=<application-client-id>
        secret=<client-secret>

    Then run:

        python example-add-curve.py
"""

import os

from dotenv import load_dotenv
from odsl import sdk, types

load_dotenv()

odsl = sdk.ODSL()
odsl.setStage("dev")
odsl.loginWithSecret(os.getenv('tid'), os.getenv('appid'), os.getenv('secret'))

# The object created by example-create-update-object.py.
object_id = 'AAA.PYTHON-EXAMPLE'

# Build the curve using the Curve/Contract helpers from odsl.types. `Curve`
# produces the '_type': 'VarCurve' shape (ondate + contracts) that the ODSL
# object service expects for a curve-valued field; `add()` appends each
# tenor/value pair as a Contract.
curve = types.Curve(ondate='2026-08-20', expcal='#REOMHENG')
curve.add('M01', 1.4)
curve.add('M02', 2.2)
curve.add('M03', 3.3)
curve.add('M04', 4.4)
curve.add('M05', 5.5)
curve.add('M06', 6.6)

# Curve doesn't set '_id' or 'properties' -- they're optional and specific to
# how you're using the curve -- so add them directly to the underlying dict.
curve.data['_id'] = 'CURVE'
curve.data['properties'] = {'timezone': 'BST'}

# Read the existing object so we don't clobber fields already on it, then
# attach the curve as a new field ('CURVE') and send the object back.
obj = odsl.get('object', 'private', object_id)
if obj is None:
    # Fall back to a fresh object if this script is run standalone, without
    # having first run example-create-update-object.py.
    obj = {'_id': object_id, '_type': '#Object'}

obj['CURVE'] = curve.data
odsl.update('object', 'private', obj)

# Read it back to confirm the curve was saved.
result = odsl.get('object', 'private', object_id)
print("Object with curve:")
print(result)