"""Example: add a curve field to a private object via the object service.

Builds on object-example.py: it attaches a `VarCurve`-shaped field (built
with the `odsl.types.Curve`/`Contract` helpers) to the object created there,
then confirms it saved by reading the object back.

Usage:
    Create a .env file (see README.md) with the following variables set for
    a service principal that has permission to write private objects:

        tid=<azure-ad-tenant-id>
        appid=<application-client-id>
        secret=<client-secret>

    Then run:

        python examples/curve-example.py
"""

import os

from dotenv import load_dotenv
from odsl import sdk, types

load_dotenv()

odsl = sdk.ODSL()
odsl.setStage("dev")
odsl.loginWithSecret(os.getenv('tid'), os.getenv('appid'), os.getenv('secret'))

# The object created by object-example.py.
object_id = 'AAA.PYTHON-EXAMPLE'

# Build the curve using the Curve/Contract helpers from odsl.types. `Curve`
# produces the '_type': 'VarCurve' shape (ondate + contracts) that the ODSL
# object service expects for a curve-valued field. Every setter (including
# `add`) returns the curve itself, so the whole thing can be built as one
# chained expression.
curve = (
    types.Curve('2026-08-20', '#REOMHENG', id='CURVE')
    .set_timezone('UTC')
    .set_currency('EUR')
    .set_units('MWH')
    .add('M01', 1.4)
    .add('M02', 2.2)
    .add('M03', 3.3)
    .add('M04', 4.5)
    .add('M05', 5.5)
    .add('M06', 6.6)
)

# Read the existing object so we don't clobber fields already on it, then
# attach the curve as a new field ('CURVE') and send the object back.
obj = odsl.get('object', 'private', object_id)
if obj is None:
    # Fall back to a fresh object if this script is run standalone, without
    # having first run object-example.py.
    obj = {'_id': object_id, '_type': '#Object'}

obj['CURVE'] = curve.data
odsl.update('object', 'private', obj)

# Read it back to confirm the curve was saved.
result = odsl.get('object', 'private', object_id)
print("Object with curve:")
print(result)
