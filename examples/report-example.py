"""Example: define a report via the odsl.types.Report builder.

Unlike every other example in this directory, a report definition isn't a
field attached to an object -- it's written directly to its own
`reportconfig` service, and read back the same way. This creates a simple
scheduled report definition and confirms it saved.

Note this creates the report *definition* (a `VarReportConfiguration`),
not a generated report result (a `VarReport`) -- running the report is a
separate step this example doesn't cover. See `Report`'s docstring in
odsl/types.py for the distinction.

Usage:
    Create a .env file (see README.md) with the following variables set for
    a service principal that has permission to write private report
    configurations:

        tid=<azure-ad-tenant-id>
        appid=<application-client-id>
        secret=<client-secret>

    Then run:

        python examples/report-example.py
"""

import os

from dotenv import load_dotenv
from odsl import sdk, types

load_dotenv()

odsl = sdk.ODSL()
odsl.setStage("dev")
odsl.loginWithSecret(os.getenv('tid'), os.getenv('appid'), os.getenv('secret'))

report_id = 'AAA.PYTHON-REPORT-EXAMPLE'

# Build the report definition. `script` points at an existing ODSL script
# that produces this report's data when it's run -- substitute one that
# exists in your environment (or use set_expression(...) instead) if you
# want this report to actually be runnable.
report = (
    types.Report(report_id, name='Python Report Example')
    .set_description('Created by report-example.py')
    .set_category('Examples')
    .set_script('#MyReportScript')
    .set_currency('EUR')
    .add_tag('python')
    .add_tag('example')
    # Schedule this report to run every Monday at 06:00, every year --
    # set_cron() enables the schedule by default (unlike the server's own
    # default of disabled, since you're setting a schedule by calling it at
    # all). NOTE: this is ODSL's cron format, not standard 5-field unix
    # cron -- it requires a 6th "year" field ('*' here means every year);
    # see set_cron()'s docstring for the full format, including what
    # happens if you leave the year field out.
    .set_cron('0 6 * * MON *')
)
odsl.update('reportconfig', 'private', report.data)

# Read it back to confirm it saved.
print("Created report configuration:")
print(odsl.get('reportconfig', 'private', report_id))
