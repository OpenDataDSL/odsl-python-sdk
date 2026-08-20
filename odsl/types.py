"""Helpers for building ODSL "Var" payloads to send to the object/data service.

Each class here builds the JSON shape for one server-side "Var" type,
matching how the ODSL server itself serialises/deserialises that type in
``odsl-core/.../var/adaptor/``:

* `Curve`/`Contract` -- a `VarCurve` (a forward curve: a value per tenor,
  as of a given curve date). See `VarCurveAdaptor.java`,
  `VarContractAdaptor.java`, `VarCurveDateAdaptor.java`.
* `Object` -- a `VarSimpleObject` (a plain, flat JSON document -- the shape
  used by the ``object`` service). See `VarSimpleObjectAdaptor.java`.
* `TimeSeries` -- a plain `VarTimeSeries` (a value per timestamp). See
  `VarTimeSeriesAdaptor.java`.
* `Event` -- a `VarEvent` (a single timestamped event message, with
  arbitrary flat custom properties). See `VarEventAdaptor.java` for how
  events are *read*; use `events_dataframe()` to *write* one or more --
  the write endpoint doesn't accept `Event.data` directly (see that
  function's docstring for why).

That Java source is the source of truth for this module -- if the server
model changes, re-check the adaptor classes rather than the POJOs' field
names, since several properties are exposed on the wire under a different,
underscore-prefixed name than their Java getter/setter (see each class's
docstring below for the specifics, and note they're not all consistent
with each other -- e.g. `Curve.set_objtype`'s value is never round-tripped
back by the server, while `TimeSeries.set_objtype`'s is).

Example::

    from odsl import types

    curve = types.Curve('2022-02-28', '#REOMHENG', id='CURVE')
    curve.set_name('Example curve').set_currency('EUR').set_units('MWh')
    curve.add('M01', 1.4).add('M02', 2.2)

    obj = odsl.get('object', 'private', 'AAA.PYTHON-EXAMPLE')
    obj['CURVE'] = curve.data
    odsl.update('object', 'private', obj)
"""


class Curve:
	"""Builds the JSON payload for a `VarCurve`.

	Every setter returns ``self`` so calls can be chained. The underlying
	dict being built is always available as ``.data`` if you need to set
	something this class doesn't have a named method for.

	Most properties are sent under the same name as their Java getter
	(``currency``, ``units``, ``name``, ``description``, ``timezone``,
	``precision``, ``properties``). A handful are sent under an
	underscore-prefixed key instead, per `VarCurveAdaptor`/
	`VarCurveDateAdaptor` -- ``_id``, ``_merge``, ``_substituted``,
	``_objtype``, ``_objid``, ``_dataid``, ``_status``, ``_identity``. The
	setters below already use the correct wire key for each property, so
	you don't need to remember which is which.

	Two things are worth calling out specifically. `subtype`
	(`setSubtype`/`getSubtype` in Java) is written to the wire as
	``_subtype`` when the server serialises a curve, but as of this
	writing `VarCurveAdaptor.deserialize` never reads `_subtype` back --
	so setting it here has no observable effect when sending a curve to
	the server today; it's included for completeness/forward-compat.
	`objtype`/`objid`/`dataid` (``_objtype``/``_objid``/``_dataid`` on the
	wire) likewise are read by the deserializer but never written by the
	serializer, so round-tripping a curve you `get()` back from the server
	won't show them even if you set them -- that's the server's current
	behaviour, not a limitation of this SDK.
	"""

	def __init__(self, ondate, expcal, id=None):
		"""Start building a curve.

		Args:
			ondate: The curve date, e.g. ``'2022-02-28'``.
			expcal: The id of the expiry calendar to use, e.g.
				``'#REOMHENG'``.
			id: Optional id for this curve (``_id`` on the wire). Only
				needed when the curve is a standalone object rather than
				a field nested inside another object.
		"""
		self.contracts = []
		self.data = dict()
		self.data['_type'] = 'VarCurve'
		self.data['ondate'] = {
			'expiryCalendar': expcal,
			'curveDate': ondate
		}
		self.data['contracts'] = self.contracts
		if id is not None:
			self.set_id(id)

	def add(self, tenor, value):
		"""Add a contract (a tenor/value pair) to this curve.

		Args:
			tenor: The relative tenor code, e.g. ``'M01'``.
			value: The value for that tenor.

		Returns:
			self, for chaining.
		"""
		c = Contract(tenor, value)
		self.contracts.append(c.data)
		return self

	def set_id(self, id):
		"""Set the id of this curve (wire key: ``_id``)."""
		self.data['_id'] = id
		return self

	def set_name(self, name):
		"""Set the display name of this curve (wire key: ``name``)."""
		self.data['name'] = name
		return self

	def set_description(self, description):
		"""Set the description of this curve (wire key: ``description``)."""
		self.data['description'] = description
		return self

	def set_currency(self, currency):
		"""Set the currency of this curve's values (wire key: ``currency``)."""
		self.data['currency'] = currency
		return self

	def set_units(self, units):
		"""Set the units of measure of this curve's values (wire key: ``units``)."""
		self.data['units'] = units
		return self

	def set_timezone(self, timezone):
		"""Set the timezone of this curve (wire key: ``timezone``).

		This is a property of the curve itself, separate from the
		``ondate`` block -- it isn't nested inside ``ondate`` on the wire.
		"""
		self.data['timezone'] = timezone
		return self

	def set_subtype(self, subtype):
		"""Set the curve subtype (wire key: ``_subtype`` on output).

		See the class docstring: as of this writing the server doesn't
		read this back in on deserialize, so it currently has no
		observable effect when sending a curve to the server.
		"""
		self.data['subtype'] = subtype
		return self

	def set_objtype(self, objtype):
		"""Set the associated object type (wire key: ``_objtype``)."""
		self.data['_objtype'] = objtype
		return self

	def set_objid(self, objid):
		"""Set the associated object id (wire key: ``_objid``)."""
		self.data['_objid'] = objid
		return self

	def set_dataid(self, dataid):
		"""Set the associated data id (wire key: ``_dataid``)."""
		self.data['_dataid'] = dataid
		return self

	def set_merge(self, merge=True):
		"""Set whether this curve should be merged with existing data (wire key: ``_merge``)."""
		self.data['_merge'] = merge
		return self

	def set_substituted(self, substituted=True):
		"""Mark this curve's values as substituted (wire key: ``_substituted``)."""
		self.data['_substituted'] = substituted
		return self

	def set_precision(self, precision):
		"""Set the precision configuration for this curve (wire key: ``precision``).

		Args:
			precision: A dict matching the server's `Precision` shape,
				e.g. ``{'roundingMode': 'HALF_UP', 'scale': 6,
				'useDefault': False, 'store': False}``.
		"""
		self.data['precision'] = precision
		return self

	def set_status(self, status):
		"""Set the status information for this curve (wire key: ``_status``).

		Args:
			status: A dict matching the server's `Status` shape (quality,
				source, reliability, processed, and their *Info fields).
		"""
		self.data['_status'] = status
		return self

	def set_identity(self, identity):
		"""Set the configured identity for this curve (wire key: ``_identity``).

		Args:
			identity: A dict matching the server's `VarSimpleObject`
				shape.
		"""
		self.data['_identity'] = identity
		return self

	def set_properties(self, properties):
		"""Replace the free-form properties bag for this curve (wire key: ``properties``).

		Args:
			properties: A dict of arbitrary custom key/value properties.
		"""
		self.data['properties'] = properties
		return self

	def set_property(self, key, value):
		"""Set a single free-form property on this curve without replacing the rest.

		Args:
			key: The property name.
			value: The property value.
		"""
		self.data.setdefault('properties', {})[key] = value
		return self


class Contract:
	"""Builds the JSON payload for a single `VarContract` (tenor/value pair) on a curve.

	The server (`VarContractAdaptor`) computes derived fields -- the
	contract's start/end/expiry dates, its absolute tenor, its status --
	from ``tenor``, ``value``, and the parent curve's ``ondate``, so those
	don't need to (and can't usefully) be supplied here.
	"""

	def __init__(self, tenor, value):
		"""Args:
			tenor: The relative tenor code, e.g. ``'M01'``.
			value: The value for that tenor.
		"""
		self.data = dict()
		self.data['tenor'] = tenor
		self.data['value'] = value


class Object:
	"""Builds the JSON payload for an ``object``-service record (`VarSimpleObject`).

	Matches `VarSimpleObjectAdaptor` in odsl-core: a "plain" object is a
	flat JSON document -- ``_id`` plus whatever other keys you set directly
	on it, with no nested "properties" wrapper (unlike `Curve`/`TimeSeries`).
	This is the shape used by the README's::

	    var = {'_id': 'AAA.PYTHON', 'name': 'Python Example'}
	    odsl.update('object', 'private', var)

	which is equivalent to::

	    obj = types.Object('AAA.PYTHON').set('name', 'Python Example')
	    odsl.update('object', 'private', obj.data)
	"""

	def __init__(self, id=None):
		"""Args:
			id: Optional id for this object (wire key: ``_id``).
		"""
		self.data = dict()
		if id is not None:
			self.set_id(id)

	def set_id(self, id):
		"""Set the id of this object (wire key: ``_id``)."""
		self.data['_id'] = id
		return self

	def set_replace(self, replace=True):
		"""Mark this update as a full replace rather than a merge (wire key: ``_replace``)."""
		self.data['_replace'] = replace
		return self

	def set(self, key, value):
		"""Set an arbitrary top-level property on this object.

		Args:
			key: The property name. Avoid leading-underscore names
				(``_id``, ``_replace``) -- those are reserved.
			value: The property value.

		Returns:
			self, for chaining.
		"""
		self.data[key] = value
		return self

	def set_property(self, key, value):
		"""Alias for `set`, kept for naming consistency with `Curve`/`TimeSeries`/`Event`."""
		return self.set(key, value)


class TimeSeries:
	"""Builds the JSON payload for a plain `VarTimeSeries` (a value per timestamp).

	Matches `VarTimeSeriesAdaptor` in odsl-core. This targets the basic,
	non-computed ``_type: 'VarTimeSeries'`` case -- the server also has
	several specialised subtypes built the same way but with extra fields
	(`VarSmartTimeSeries`, `VarEventTimeSeries`, `VarMetricTimeSeries`,
	`VarCurveDates`, `VarMatrixDates`, `VarReportDates`, `VarCurveSeries`);
	those aren't modelled here.

	Each observation is sent via `add()` as a ``{'time': ..., 'value':
	...}`` object -- this is the shape the server always accepts for
	``data`` elements regardless of ``valueType``, and is what this class
	defaults ``valueType`` to (``'BASIC'``, the simpler of the two wire
	shapes for a `TimeValue` -- ``'TRACKED'`` adds per-point status/links).

	Unlike `Curve`, the properties below round-trip both ways --
	``_objtype``/``_objid``/``_dataid``/``_subtype`` are both read from and
	written to the wire by the server, so `set_objtype` etc. here will show
	up again if you `get()` this time series back.
	"""

	def __init__(self, id=None, calendar=None, start=None):
		"""Args:
			id: Optional id for this time series (wire key: ``_id``).
			calendar: Optional calendar code, e.g. ``'DAILY'``. Defaults
				to ``'SPARSE'`` server-side if omitted.
			start: Optional ISO date/time string for the first
				observation.
		"""
		self.data = dict()
		self.data['_type'] = 'VarTimeSeries'
		self.data['data'] = []
		self.data['valueType'] = 'BASIC'
		if id is not None:
			self.set_id(id)
		if calendar is not None:
			self.set_calendar(calendar)
		if start is not None:
			self.set_start(start)

	def add(self, time, value):
		"""Add an observation to this time series.

		Args:
			time: An ISO date/time string for this observation.
			value: The value at that time.

		Returns:
			self, for chaining.
		"""
		self.data['data'].append({'time': time, 'value': value})
		return self

	def set_id(self, id):
		"""Set the id of this time series (wire key: ``_id``)."""
		self.data['_id'] = id
		return self

	def set_start(self, start):
		"""Set the start date/time of this time series (wire key: ``start``)."""
		self.data['start'] = start
		return self

	def set_calendar(self, calendar):
		"""Set the calendar this time series uses (wire key: ``calendar``)."""
		self.data['calendar'] = calendar
		return self

	def set_name(self, name):
		"""Set the display name of this time series (wire key: ``name``)."""
		self.data['name'] = name
		return self

	def set_description(self, description):
		"""Set the description of this time series (wire key: ``description``)."""
		self.data['description'] = description
		return self

	def set_currency(self, currency):
		"""Set the currency of this time series' values (wire key: ``currency``)."""
		self.data['currency'] = currency
		return self

	def set_units(self, units):
		"""Set the units of measure of this time series' values (wire key: ``units``)."""
		self.data['units'] = units
		return self

	def set_timezone(self, timezone):
		"""Set the timezone of this time series (wire key: ``timezone``)."""
		self.data['timezone'] = timezone
		return self

	def set_tenor(self, tenor):
		"""Set the tenor of this time series, if it's contract-based (wire key: ``tenor``)."""
		self.data['tenor'] = tenor
		return self

	def set_source(self, source):
		"""Set the source of this time series (wire key: ``source``)."""
		self.data['source'] = source
		return self

	def set_scaling(self, scaling):
		"""Set the scaling factor applied to this time series' values (wire key: ``scaling``)."""
		self.data['scaling'] = scaling
		return self

	def set_observed(self, observed):
		"""Set how values are observed/aggregated (wire key: ``observed``).

		Args:
			observed: One of ``'summed'``, ``'averaged'``, ``'end'``,
				``'beginning'``, ``'high'``, ``'low'``, ``'delta'``,
				``'none'``.
		"""
		self.data['observed'] = observed
		return self

	def set_value_type(self, value_type):
		"""Set the wire shape used for each observation (wire key: ``valueType``).

		Args:
			value_type: ``'BASIC'`` (time + value only, the default here)
				or ``'TRACKED'`` (adds per-point status/links).
		"""
		self.data['valueType'] = value_type
		return self

	def set_data_type(self, data_type):
		"""Set the data type of this time series' values (wire key: ``dataType``)."""
		self.data['dataType'] = data_type
		return self

	def set_precision(self, precision):
		"""Set the precision configuration for this time series (wire key: ``precision``).

		Args:
			precision: A dict matching the server's `Precision` shape,
				e.g. ``{'roundingMode': 'HALF_UP', 'scale': 6,
				'useDefault': False, 'store': False}``.
		"""
		self.data['precision'] = precision
		return self

	def set_status(self, status):
		"""Set the status information for this time series (wire key: ``_status``)."""
		self.data['_status'] = status
		return self

	def set_identity(self, identity):
		"""Set the configured identity for this time series (wire key: ``_identity``)."""
		self.data['_identity'] = identity
		return self

	def set_subtype(self, subtype):
		"""Set the time series subtype (wire key: ``_subtype``)."""
		self.data['_subtype'] = subtype
		return self

	def set_objtype(self, objtype):
		"""Set the associated object type (wire key: ``_objtype``)."""
		self.data['_objtype'] = objtype
		return self

	def set_objid(self, objid):
		"""Set the associated object id (wire key: ``_objid``)."""
		self.data['_objid'] = objid
		return self

	def set_dataid(self, dataid):
		"""Set the associated data id (wire key: ``_dataid``)."""
		self.data['_dataid'] = dataid
		return self

	def set_properties(self, properties):
		"""Replace the free-form properties bag for this time series (wire key: ``properties``)."""
		self.data['properties'] = properties
		return self

	def set_property(self, key, value):
		"""Set a single free-form property on this time series without replacing the rest."""
		self.data.setdefault('properties', {})[key] = value
		return self


class Event:
	"""Builds the JSON shape of a `VarEvent` (a single timestamped event message).

	Matches `VarEventAdaptor` in odsl-core -- this is the shape you get
	back from `odsl.get`/`odsl.list` on the ``event`` service, and the shape
	of each element `events_dataframe()` (below) sends when *writing*
	events. Unlike `Curve`/`TimeSeries`, custom properties on an event are
	flat top-level keys (like `Object`), not nested under a "properties"
	key -- this is what you're filtering on when you see event queries
	like::

	    odsl.list('event', 'public', {'_filter': '{"MID_PRICE": {"$gt": 50}}'})

	IMPORTANT: ``event`` must be in ``OBJECTID:EVENTID`` form -- exactly
	one colon, splitting into the id of an existing private object and a
	field name. Per `EventService`/`EventUpdate` in odsl-azure, writing an
	event actually appends it to an array field (named by the ``EVENTID``
	half) on that object; ``OBJECTID:EVENTID`` is also the ``key`` you
	``get()``/filter by when reading events back. This is unrelated to
	``eventid``, which is just this specific event's own unique id within
	that array.

	``event`` and ``eventtime``, plus ``eventid``, are effectively required:
	the server reads ``eventid``/``eventtime`` unconditionally when parsing
	an event, so a payload missing either will fail to deserialise.
	``eventlist`` doesn't need to be set here -- when an event is written
	via ``events_dataframe()``, `ObjectService.extractDataFromObject` fills
	it in itself from the ``EVENTID`` half of ``event``.

	``eventtype`` is also effectively required, even though the docs for
	`set_eventtype` (and `VarEvent.java`) describe it as defaulting to
	``'#Event'`` -- `ObjectService.updateEvent` in odsl-azure reads
	``eventtype`` unconditionally *before* the code path that would apply
	that default ever runs, so a payload without it fails with ``[5005]
	Update Error: Document does not contain key eventtype`` instead of
	falling back. This class works around that by defaulting ``eventtype``
	to ``'#Event'`` itself in `__init__` -- call `set_eventtype` to
	override it, but don't rely on omitting it.

	The reserved top-level keys the server treats specially -- don't use
	these as custom property names via `set_property` -- are: ``eventid``,
	``eventtype``, ``event``, ``eventlist``, ``eventtime``, ``eventstart``,
	``eventend``, ``timezone``, and ``status``.

	Building an `Event` on its own doesn't send anything -- pass one or
	more to `events_dataframe()` and post the result to actually write
	them; see that function's docstring for why.
	"""

	def __init__(self, event, eventid, eventtime, id=None):
		"""Args:
			event: The private object id and event field name this event
				belongs to, in ``'OBJECTID:EVENTID'`` form, e.g.
				``'AAA.PYTHON-EXAMPLE:READING'``.
			eventid: The unique id of this specific event.
			eventtime: An ISO date/time string for when this event
				message was generated.
			id: Optional explicit id override (wire key: ``_id``). Not
				read back by the server on input -- ``eventid`` is what
				actually identifies the event -- defaults to ``eventid``
				if not given, matching what the server itself does when
				it serialises an event back to you.
		"""
		self.data = dict()
		self.data['_type'] = 'VarEvent'
		self.data['event'] = event
		self.data['eventid'] = eventid
		self.data['eventtime'] = eventtime
		self.data['_id'] = id if id is not None else eventid
		# See the class docstring: the server requires this key to be
		# present on write (it doesn't reliably apply its own '#Event'
		# default), so set it here rather than leaving it out. Call
		# set_eventtype() afterwards to use something other than '#Event'.
		self.data['eventtype'] = '#Event'

	def set_eventstart(self, eventstart):
		"""Set when this event started (wire key: ``eventstart``). Defaults to `eventtime` server-side if not set."""
		self.data['eventstart'] = eventstart
		return self

	def set_eventend(self, eventend):
		"""Set when this event ended (wire key: ``eventend``). Defaults to `eventstart` server-side if not set."""
		self.data['eventend'] = eventend
		return self

	def set_eventtype(self, eventtype):
		"""Set the type of this event (wire key: ``eventtype``). Defaults to ``'#Event'`` server-side if not set."""
		self.data['eventtype'] = eventtype
		return self

	def set_eventlist(self, eventlist):
		"""Set the non-object-specific name of this group of events (wire key: ``eventlist``)."""
		self.data['eventlist'] = eventlist
		return self

	def set_timezone(self, timezone):
		"""Set the timezone of this event (wire key: ``timezone``). Defaults to ``'UTC'`` server-side if not set."""
		self.data['timezone'] = timezone
		return self

	def set_source(self, source):
		"""Set the source of this event (wire key: ``_source``)."""
		self.data['_source'] = source
		return self

	def set_status(self, status):
		"""Set the status information for this event (wire key: ``_status``)."""
		self.data['_status'] = status
		return self

	def set_property(self, key, value):
		"""Set a custom top-level property on this event.

		Args:
			key: The property name. See the class docstring for the list
				of reserved names to avoid.
			value: The property value.

		Returns:
			self, for chaining.
		"""
		self.data[key] = value
		return self


def events_dataframe(events):
	"""Build the payload the ``event`` service's write endpoint actually expects.

	Posting an `Event`'s ``.data`` directly (a flat `VarEvent`-shaped JSON
	object) to ``odsl.update('event', ...)`` returns HTTP 400. Despite
	`VarEventAdaptor` being what *reads* events back, writing them goes
	through `EventService.update` in odsl-azure, which always parses the
	request body as a `DataFrame` -- the same shape produced by
	``pandas.DataFrame.to_json(orient="split")``::

	    {'columns': [...], 'index': [...], 'data': [[...], [...], ...]}

	This function builds exactly that from one or more `Event` builders (or
	plain dicts shaped like `Event.data`). A single event is just a
	one-row DataFrame -- there's no separate "single event" shape, which is
	why this accepts a bare `Event`/dict as well as a list of them.

	Args:
		events: A single `Event` (or dict), or a list of them. Each one's
			``event`` value must be in ``'OBJECTID:EVENTID'`` form -- see
			`Event`'s docstring.

	Returns:
		A dict ready to pass straight to
		``odsl.update('event', source, events_dataframe(events))``.
	"""
	if isinstance(events, Event) or isinstance(events, dict):
		events = [events]
	rows = [e.data if isinstance(e, Event) else dict(e) for e in events]

	columns = []
	for row in rows:
		for key in row:
			# '_type' is added automatically by the server for each stored
			# event and doesn't need to be sent as a column.
			if key != '_type' and key not in columns:
				columns.append(key)

	data = [[row.get(c) for c in columns] for row in rows]
	return {
		'columns': columns,
		'index': list(range(len(rows))),
		'data': data,
	}
