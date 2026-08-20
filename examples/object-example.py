"""Example: create a private object via the ODSL object service, then update it.

Usage:
    Create a .env file (see README.md) with the following variables set for
    a service principal that has permission to write private objects:

        tid=<azure-ad-tenant-id>
        appid=<application-client-id>
        secret=<client-secret>

    Then run:

        python example-create-update-object.py
"""

import os

from dotenv import load_dotenv
from odsl import sdk

load_dotenv()

odsl = sdk.ODSL()
odsl.setStage("dev")
odsl.loginWithSecret(os.getenv('tid'), os.getenv('appid'), os.getenv('secret'))

# The id of the private object we're going to create/update. Private object
# ids don't start with '#' (that prefix is reserved for public/reference
# data, as used elsewhere in the SDK examples).
object_id = 'AAA.PYTHON-EXAMPLE'

# --- Create the object -----------------------------------------------------
# `update` is used for both creates and updates: if `_id` doesn't exist yet,
# it's created; if it does, it's overwritten with whatever fields you send.
new_object = {
    '_id': object_id,
    'name': 'Python Example',
    'description': 'Created by example-create-update-object.py',
}
odsl.update('object', 'private', new_object)

# Read it back to confirm it was created.
created = odsl.get('object', 'private', object_id)
print("Created object:")
print(created)

# --- Update the object ------------------------------------------------------
# Modify the record we just read back and send it again. Only the fields
# present in the dict are sent, so start from the current object rather than
# a fresh dict if you want to preserve fields you're not explicitly changing.
created['description'] = 'Updated by example-create-update-object.py'
odsl.update('object', 'private', created)

# Read it back again to confirm the update took effect.
updated = odsl.get('object', 'private', object_id)
print("\nUpdated object:")
print(updated)