"""Helpers for building ODSL "Var" payloads to send to the object/data service.

Each class here builds the JSON shape for one server-side "Var" type,
matching how the ODSL server itself serialises/deserialises that type in
``odsl-core/.../var/adaptor/``:

* `Curve`/`Contract` -- a `VarCurve` (a forward curve: a value per tenor,
  as of a given curve date). See `VarCurveAdaptor.java`,
  `VarContractAdaptor.java`, `VarCurveDateAdaptor.java`.
* `EventCurve` -- a `VarEventCurve` (a curve computed from events instead
  of fixed contracts). Also built by `VarCurveAdaptor.java` -- it's the
  same wire type as `Curve` with ``_type: 'VarEventCurve'`` and a
  different set of fields, not a separate adaptor class.
* `SmartCurve` -- a `VarSmartCurve` (a curve computed from a script or
  formula expression, optionally against a `baseCurve`). This is *not* a
  `VarCurve` subtype server-side -- unlike `EventCurve`, it has its own
  POJO and its own adaptor, `VarSmartCurveAdaptor.java`.
* `Object` -- a `VarSimpleObject` (a plain, flat JSON document -- the shape
  used by the ``object`` service). See `VarSimpleObjectAdaptor.java`.
* `TimeSeries` -- a plain `VarTimeSeries` (a value per timestamp). See
  `VarTimeSeriesAdaptor.java`.
* `EventTimeSeries` -- a `VarEventTimeSeries` (a time series whose
  observations are derived from an event property, alongside its own
  explicit ``data`` points). Same adaptor as `TimeSeries` --
  `VarTimeSeriesAdaptor.java` -- distinguished by ``_type``.
* `SmartTimeSeries` -- a `VarSmartTimeSeries` (a time series computed from
  a script or formula expression, optionally against a
  `baseTimeSeries`). Same adaptor as `TimeSeries`, distinguished by
  ``_type``; unlike `TimeSeries`/`EventTimeSeries`, it has no ``data``
  points of its own to set.
* `Event` -- a `VarEvent` (a single timestamped event message, with
  arbitrary flat custom properties). See `VarEventAdaptor.java` for how
  events are *read*; use `events_dataframe()` to *write* one or more --
  the write endpoint doesn't accept `Event.data` directly (see that
  function's docstring for why).
* `Report` -- a `VarReportConfiguration` (the definition of a report --
  what actually produces a `VarReport` result when run). See
  `VarReportConfigurationAdaptor.java`; written via the ``reportconfig``
  service, not ``object``/``data`` like everything else here.

That Java source is the source of truth for this module -- if the server
model changes, re-check the adaptor classes rather than the POJOs' field
names, since several properties are exposed on the wire under a different,
underscore-prefixed name than their Java getter/setter (see each class's
docstring below for the specifics, and note they're not all consistent
with each other -- e.g. `Curve.set_objtype`'s value is never round-tripped
back by the server, while `TimeSeries.set_objtype`'s is).

`EventCurve`/`SmartCurve`/`EventTimeSeries`/`SmartTimeSeries` are all
attached to an object as a field and written via the ``object`` service,
exactly like `Curve`/`TimeSeries`::

    obj = odsl.get('object', 'private', 'AAA.PYTHON-EXAMPLE')
    obj['SMART_CURVE'] = types.SmartCurve('AAA.PYTHON-EXAMPLE:CURVE', 'BASE * 1.1', id='SMART_CURVE').data
    odsl.update('object', 'private', obj)

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


def _var_reference(oid, service='data', source='private', otype=None):
	"""Build the wire shape of a `VarReference`, per `VarReferenceAdaptor.java`.

	Used for `SmartCurve.set_base_curve`/`SmartTimeSeries.set_base_time_series`,
	which point at another curve/time series by reference rather than embedding
	it. ``source``/``service`` are underscore-prefixed on the wire
	(``_service``/``_source``/``_oid``/``_otype``) even though the setter
	names here aren't.
	"""
	ref = {
		'_type': 'VarReference',
		'_service': service,
		'_source': source,
		'_oid': oid,
	}
	if otype is not None:
		ref['_otype'] = otype
	return ref


class EventCurve:
	"""Builds the JSON payload for a `VarEventCurve` -- a curve computed from events.

	Same wire type as `Curve` (both go through `VarCurveAdaptor`), just with
	``_type: 'VarEventCurve'`` and a different set of fields: instead of an
	``ondate``/``contracts`` pair you supply, the server builds the curve
	itself from events under ``event`` -- reading ``property`` off each one
	as the value and ``tenor`` as the tenor/maturity code. Unlike `Curve`,
	there's no `add()` here -- there's nothing to add, the contracts are
	derived server-side.

	``event``, ``property``, ``tenor``, and ``calendar`` are always written
	to the wire (per `VarCurveAdaptor.serialize`), so they're required here
	in `__init__` rather than left as optional setters, even though the
	deserializer itself doesn't reject a payload missing them outright --
	without them the server has nothing to compute the curve from.
	"""

	def __init__(self, event, property, tenor, calendar, id=None):
		"""Args:
			event: The event group this curve is built from, in
				``'OBJECTID:EVENTID'`` form -- see `Event`'s docstring for
				what that means.
			property: The name of the property on each event to use as
				this curve's value.
			tenor: The name of the property on each event to use as this
				curve's tenor/maturity code.
			calendar: The id of the expiry calendar to use (wire key:
				``calendar``, not ``expiryCalendar`` -- `EventCurve` isn't
				nested under an ``ondate`` block the way `Curve` is).
			id: Optional id for this curve (``_id`` on the wire). Only
				needed when the curve is a standalone object rather than
				a field nested inside another object.
		"""
		self.data = dict()
		self.data['_type'] = 'VarEventCurve'
		self.data['event'] = event
		self.data['property'] = property
		self.data['tenor'] = tenor
		self.data['calendar'] = calendar
		if id is not None:
			self.set_id(id)

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
		"""Set the timezone of this curve (wire key: ``timezone``)."""
		self.data['timezone'] = timezone
		return self

	def set_holiday_calendar(self, holiday_calendar):
		"""Set the calendar used to decide which dates this curve is published on (wire key: ``holidayCalendar``)."""
		self.data['holidayCalendar'] = holiday_calendar
		return self

	def set_filter(self, filter):
		"""Set the optional filter used to select which events feed this curve (wire key: ``filter``)."""
		self.data['filter'] = filter
		return self

	def set_source(self, source):
		"""Set the optional source of the events used to build this curve (wire key: ``source``)."""
		self.data['source'] = source
		return self

	def set_value_transformation(self, value_transformation):
		"""Set an optional expression to transform every value in this curve (wire key: ``valueTransformation``)."""
		self.data['valueTransformation'] = value_transformation
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

	def set_identity(self, identity):
		"""Set the configured identity for this curve (wire key: ``_identity``)."""
		self.data['_identity'] = identity
		return self

	def set_properties(self, properties):
		"""Replace the free-form properties bag for this curve (wire key: ``properties``)."""
		self.data['properties'] = properties
		return self

	def set_property(self, key, value):
		"""Set a single free-form property on this curve without replacing the rest."""
		self.data.setdefault('properties', {})[key] = value
		return self


class SmartCurve:
	"""Builds the JSON payload for a `VarSmartCurve` -- a curve computed from a script/formula.

	Unlike `EventCurve`, this is *not* a `VarCurve` -- it's a completely
	separate POJO with its own adaptor, `VarSmartCurveAdaptor.java`, so it
	doesn't share `Curve`'s wire shape at all: no ``ondate``, no
	``contracts``, no ``_merge``/``_substituted``/``_subtype``. Instead it's
	built from an ``expression`` (a formula referencing ``BASE``, the curve
	pointed at by ``baseCurve``) and, optionally, a ``script`` that runs on
	top of that.

	``baseCurve`` and ``expression`` are both required here in `__init__`
	-- when this curve is attached to an object and written,
	`DataHelper.validateData` in odsl-azure rejects a payload missing
	either with ``[8003] Invalid update to type VarSmartCurve``, and
	separately rejects one that has a ``contracts`` field at all (this
	class never sets one, so that half doesn't need a workaround). Setting
	`set_script` on top is optional -- it doesn't relax the ``baseCurve``/
	``expression`` requirement, it runs in addition to them.
	"""

	def __init__(self, base_curve, expression, id=None, script=None):
		"""Args:
			base_curve: The id of the curve this formula refers to as
				``BASE`` -- passed straight to `set_base_curve` with its
				defaults (``source='private'``, ``service='data'``). Call
				`set_base_curve` again afterwards if you need a different
				source/service/otype. See `set_base_curve` for the id
				format this needs to be in -- it's not just the curve's
				own field name.
			expression: The formula expression, e.g. ``'BASE * 1.1'``. See
				`set_expression`.
			id: Optional id for this curve (``_id`` on the wire).
			script: Optional name of a script to run on top of the
				expression. See `set_script`.
		"""
		self.data = dict()
		self.data['_type'] = 'VarSmartCurve'
		self.set_base_curve(base_curve)
		self.set_expression(expression)
		if id is not None:
			self.set_id(id)
		if script is not None:
			self.set_script(script)

	def set_id(self, id):
		"""Set the id of this curve (wire key: ``_id``)."""
		self.data['_id'] = id
		return self

	def set_base_curve(self, oid, source='private', service='data', otype=None):
		"""Set the base curve this formula refers to as ``BASE`` (wire key: ``baseCurve``).

		Args:
			oid: The id of the referenced curve, curve dates, or smart
				curve, in ``'OBJECTID:FIELDNAME'`` form when it's a field
				attached to an object -- e.g. a curve field named
				``CURVE`` on object ``AAA.PYTHON-EXAMPLE`` is
				``'AAA.PYTHON-EXAMPLE:CURVE'``, *not* just ``'CURVE'``.
				This is the same ``createReference``/``_oid`` id you'd use
				with ``odsl.get('data', source, oid)`` to read that field
				directly -- passing just the field name resolves to
				nothing and this smart curve won't compute.
			source: The source/scope of the reference -- ``'private'``
				(the default) or ``'public'``.
			service: The service the reference points into. Defaults to
				``'data'``, which is correct for referencing another
				curve.
			otype: Optional referenced object type (wire key: ``_otype``),
				e.g. ``'VarCurve'``.
		"""
		self.data['baseCurve'] = _var_reference(oid, service=service, source=source, otype=otype)
		return self

	def set_expression(self, expression):
		"""Set the formula expression used to compute this curve (wire key: ``expression``).

		``BASE`` in the expression refers to whatever curve `set_base_curve`
		points at.
		"""
		self.data['expression'] = expression
		return self

	def set_script(self, script):
		"""Set the name of the script used to compute this curve (wire key: ``script``).

		Uses the default ``#CurveScript`` script server-side if not set.
		"""
		self.data['script'] = script
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

	def set_category(self, category):
		"""Set the category this curve is placed in (wire key: ``category``). Defaults to ``'General'`` server-side if not set."""
		self.data['category'] = category
		return self

	def set_commodity(self, commodity):
		"""Set the commodity for this curve (wire key: ``commodity``)."""
		self.data['commodity'] = commodity
		return self

	def set_market(self, market):
		"""Set the market this curve is placed in (wire key: ``market``)."""
		self.data['market'] = market
		return self

	def set_product(self, product):
		"""Set the product category for this curve (wire key: ``product``)."""
		self.data['product'] = product
		return self

	def set_priority(self, priority):
		"""Set the build priority for this curve (wire key: ``priority``): ``1`` (high), ``2`` (medium, the default), or ``3`` (low)."""
		self.data['priority'] = priority
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

	def set_identity(self, identity):
		"""Set the configured identity for this curve (wire key: ``_identity``)."""
		self.data['_identity'] = identity
		return self

	def set_cache_options(self, cache_options):
		"""Set the caching options for this curve (wire key: ``cacheOptions``).

		Args:
			cache_options: A dict matching the server's
				`SmartCurveCacheOptions` shape.
		"""
		self.data['cacheOptions'] = cache_options
		return self

	def set_properties(self, properties):
		"""Replace the free-form properties bag for this curve (wire key: ``properties``)."""
		self.data['properties'] = properties
		return self

	def set_property(self, key, value):
		"""Set a single free-form property on this curve without replacing the rest."""
		self.data.setdefault('properties', {})[key] = value
		return self


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


class EventTimeSeries:
	"""Builds the JSON payload for a `VarEventTimeSeries` -- a time series driven by events.

	Same wire type as `TimeSeries` (both go through `VarTimeSeriesAdaptor`),
	just with ``_type: 'VarEventTimeSeries'`` and the extra ``event``/
	``property``/``filter``/``index`` fields below.

	Unlike `TimeSeries`, there's no `add()` here and this class never sets
	a ``data`` key at all -- when this time series is attached to an object
	and written, `DataHelper.validateData` in odsl-azure rejects a payload
	that has a ``data`` key *present*, even an empty list, with ``[8003]
	Invalid update to type VarEventTimeseries - Cannot contain data``. The
	observations are derived entirely server-side from the events under
	``event``; there's nothing for the caller to supply.
	"""

	def __init__(self, event, property, id=None, calendar=None, start=None):
		"""Args:
			event: The event group this time series is built from, in
				``'OBJECTID:EVENTID'`` form -- see `Event`'s docstring for
				what that means.
			property: The name of the property on each event to use as
				this time series' value.
			id: Optional id for this time series (wire key: ``_id``).
			calendar: Optional calendar code, e.g. ``'DAILY'``. Defaults
				to ``'SPARSE'`` server-side if omitted.
			start: Optional ISO date/time string this time series is
				considered to start from. Doesn't add any ``data`` -- see
				the class docstring.
		"""
		self.data = dict()
		self.data['_type'] = 'VarEventTimeSeries'
		self.data['valueType'] = 'BASIC'
		self.data['event'] = event
		self.data['property'] = property
		# Matches VarEventTimeSeries.java's own default -- which field on
		# each event to index observations by, if not overridden below.
		self.data['index'] = 'start'
		if id is not None:
			self.set_id(id)
		if calendar is not None:
			self.set_calendar(calendar)
		if start is not None:
			self.set_start(start)

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

	def set_index(self, index):
		"""Set which date field on each event to index observations by (wire key: ``index``). Defaults to ``'start'``."""
		self.data['index'] = index
		return self

	def set_filter(self, filter):
		"""Set the optional filter used to select which events feed this time series (wire key: ``filter``)."""
		self.data['filter'] = filter
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

	def set_precision(self, precision):
		"""Set the precision configuration for this time series (wire key: ``precision``)."""
		self.data['precision'] = precision
		return self

	def set_properties(self, properties):
		"""Replace the free-form properties bag for this time series (wire key: ``properties``)."""
		self.data['properties'] = properties
		return self

	def set_property(self, key, value):
		"""Set a single free-form property on this time series without replacing the rest."""
		self.data.setdefault('properties', {})[key] = value
		return self


class SmartTimeSeries:
	"""Builds the JSON payload for a `VarSmartTimeSeries` -- a time series computed from a script/formula.

	Same wire type as `TimeSeries` (`VarTimeSeriesAdaptor` handles all
	three), but with ``_type: 'VarSmartTimeSeries'`` and computed values --
	unlike `TimeSeries`/`EventTimeSeries`, there's no `add()` here and no
	``start``, since the server doesn't read observation data for a smart
	time series at all; it's built from ``expression``/``script`` instead,
	the same way `SmartCurve` is.

	``baseTimeSeries`` and ``expression`` are both required here in
	`__init__` -- when this time series is attached to an object and
	written, `DataHelper.validateData` in odsl-azure rejects a payload
	missing either. The error you'll see says ``Invalid update to type
	VarEventTimeseries``, not ``VarSmartTimeseries`` -- that's a labelling
	quirk in odsl-azure's own error message for this check, not a mistake
	in this SDK. The same check also rejects a payload with a ``data`` key
	present, which this class never sets. Setting `set_script` on top is
	optional -- it doesn't relax the ``baseTimeSeries``/``expression``
	requirement, it runs in addition to them.
	"""

	def __init__(self, base_time_series, expression, id=None, calendar=None, script=None):
		"""Args:
			base_time_series: The id of the time series this formula
				refers to as ``BASE`` -- passed straight to
				`set_base_time_series` with its defaults
				(``source='private'``, ``service='data'``). Call
				`set_base_time_series` again afterwards if you need a
				different source/service/otype. See `set_base_time_series`
				for the id format this needs to be in -- it's not just the
				time series' own field name.
			expression: The formula expression, e.g. ``'BASE * 1.1'``. See
				`set_expression`.
			id: Optional id for this time series (wire key: ``_id``).
			calendar: Optional calendar code, e.g. ``'DAILY'``. Defaults
				to ``'SPARSE'`` server-side if omitted.
			script: Optional name of a script to run on top of the
				expression. See `set_script`.
		"""
		self.data = dict()
		self.data['_type'] = 'VarSmartTimeSeries'
		self.set_base_time_series(base_time_series)
		self.set_expression(expression)
		if id is not None:
			self.set_id(id)
		if calendar is not None:
			self.set_calendar(calendar)
		if script is not None:
			self.set_script(script)

	def set_id(self, id):
		"""Set the id of this time series (wire key: ``_id``)."""
		self.data['_id'] = id
		return self

	def set_calendar(self, calendar):
		"""Set the calendar this time series uses (wire key: ``calendar``)."""
		self.data['calendar'] = calendar
		return self

	def set_base_time_series(self, oid, source='private', service='data', otype=None):
		"""Set the base time series this formula refers to as ``BASE`` (wire key: ``baseTimeSeries``).

		Args:
			oid: The id of the referenced time series or smart time
				series, in ``'OBJECTID:FIELDNAME'`` form when it's a
				field attached to an object -- e.g. a time series field
				named ``TIMESERIES`` on object ``AAA.PYTHON-EXAMPLE`` is
				``'AAA.PYTHON-EXAMPLE:TIMESERIES'``, *not* just
				``'TIMESERIES'``. This is the same ``createReference``/
				``_oid`` id you'd use with ``odsl.get('data', source,
				oid)`` to read that field directly -- passing just the
				field name resolves to nothing and this smart time series
				won't compute.
			source: The source/scope of the reference -- ``'private'``
				(the default) or ``'public'``.
			service: The service the reference points into. Defaults to
				``'data'``, which is correct for referencing another time
				series.
			otype: Optional referenced object type (wire key: ``_otype``),
				e.g. ``'VarTimeSeries'``.
		"""
		self.data['baseTimeSeries'] = _var_reference(oid, service=service, source=source, otype=otype)
		return self

	def set_expression(self, expression):
		"""Set the formula expression used to compute this time series (wire key: ``expression``).

		``BASE`` in the expression refers to whatever time series
		`set_base_time_series` points at.
		"""
		self.data['expression'] = expression
		return self

	def set_script(self, script):
		"""Set the name of the script used to compute this time series (wire key: ``script``)."""
		self.data['script'] = script
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


class Report:
	"""Builds the JSON payload for a `VarReportConfiguration` -- a report definition.

	This is the *definition* of a report (what script/expression to run, on
	what schedule, over what date range), matching
	`VarReportConfigurationAdaptor` in odsl-core -- running it is what
	produces a `VarReport` result (``data``, ``start``/``end``,
	``errorMessage``, etc.), which isn't modelled here since it's an output,
	not something you construct and send.

	Unlike every other class in this module, a `Report` isn't a field
	attached to an object -- it's written directly to its own service::

	    report = types.Report('AAA.PYTHON-REPORT', name='Python Example Report')
	    report.set_script('#MyReportScript').set_category('Examples')
	    odsl.update('reportconfig', 'private', report.data)

	``_id`` and ``name`` are required by `Validate.validateBody` in
	odsl-azure -- a payload missing either fails validation before it
	reaches the deserializer at all.
	"""

	#: Valid values for `set_report_type`, per `VarReportConfiguration.reportTypes`.
	REPORT_TYPES = ('Default', 'Fixed', 'Dynamic', 'Insight', 'Widget', 'Composition', 'CompositionTemplate')

	def __init__(self, id, name=None, report_type=None):
		"""Args:
			id: The id of this report (wire key: ``_id``). Required --
				see the class docstring.
			name: Optional display name for this report (wire key:
				``name``). Also effectively required server-side -- see
				the class docstring -- so it's accepted here even though
				every other field is set via a setter.
			report_type: Optional report type -- see `set_report_type`.
		"""
		self.data = dict()
		self.data['_type'] = 'VarReportConfiguration'
		self.data['_id'] = id
		if name is not None:
			self.set_name(name)
		if report_type is not None:
			self.set_report_type(report_type)

	def set_name(self, name):
		"""Set the display name of this report (wire key: ``name``)."""
		self.data['name'] = name
		return self

	def set_report_type(self, report_type):
		"""Set the type of this report (wire key: ``reportType``). Defaults to ``'Default'`` server-side if not set.

		Args:
			report_type: One of `REPORT_TYPES` (``'Default'``, ``'Fixed'``,
				``'Dynamic'``, ``'Insight'``, ``'Widget'``,
				``'Composition'``, ``'CompositionTemplate'``) -- the
				server rejects anything else. ``'Insight'``/``'Widget'``
				also switch this report's caching to never-cache
				server-side.
		"""
		self.data['reportType'] = report_type
		return self

	def set_category(self, category):
		"""Set the category this report is placed in (wire key: ``category``)."""
		self.data['category'] = category
		return self

	def set_sub_category(self, sub_category):
		"""Set the sub-category this report is placed in (wire key: ``subCategory``)."""
		self.data['subCategory'] = sub_category
		return self

	def set_description(self, description):
		"""Set the description of this report (wire key: ``description``)."""
		self.data['description'] = description
		return self

	def set_script(self, script):
		"""Set the name of the script that produces this report's data (wire key: ``script``)."""
		self.data['script'] = script
		return self

	def set_expression(self, expression):
		"""Set the formula expression that produces this report's data, as an alternative to `set_script` (wire key: ``expression``)."""
		self.data['expression'] = expression
		return self

	def set_currency(self, currency):
		"""Set this report's currency (wire key: ``currency``), available to the script/expression as ``#REPORT.currency``."""
		self.data['currency'] = currency
		return self

	def set_units(self, units):
		"""Set this report's units (wire key: ``units``), available to the script/expression as ``#REPORT.units``."""
		self.data['units'] = units
		return self

	def set_timezone(self, timezone):
		"""Set this report's timezone (wire key: ``timezone``), available to the script/expression as ``#REPORT.timezone``."""
		self.data['timezone'] = timezone
		return self

	def set_template(self, template):
		"""Set the mustache template used to render this report (wire key: ``template``)."""
		self.data['template'] = template
		return self

	def set_default_range(self, default_range):
		"""Set the default date range for this report (wire key: ``defaultRange``)."""
		self.data['defaultRange'] = default_range
		return self

	def set_cron(self, cron, enabled=True):
		"""Set the schedule used to run this report (wire key: ``cron``).

		This is *not* standard 5-field unix cron. The server
		(`CronService.createCronTab` in odsl-core) requires 6 or 7
		space-separated fields -- ``minute hour dom month dow year
		[tz]`` -- i.e. unix cron plus a required year field, and an
		optional trailing timezone. A 5-field expression like
		``'0 6 * * MON'`` is missing the year and is rejected -- see
		``Raises`` below for what that looks like in practice.

		Each field accepts a number, ``*`` (any), a list (``1,2,3``),
		a range (``1-5``), an increment (``*/15``), and, for
		day-of-week, a day name (``MON``..``SUN``); year additionally
		accepts ``*`` for "every year" (it doesn't have to be a fixed
		year), and must otherwise be between 2020 and 2999. ``tz``, if
		given, must be one of ``'UTC'`` (default), ``'EU1'``, ``'EU2'``.

		For example, 6am every Monday, every year::

			report.set_cron('0 6 * * MON *')

		Args:
			cron: A 6- or 7-field cron expression as described above.
			enabled: Whether the schedule is active (wire key:
				``enabled``) -- the cron expression alone doesn't trigger
				anything unless this is also true, which it is by
				default here (unlike the server's own default of
				``False``, since you're setting a schedule by calling
				this at all).

		Raises:
			ValueError: If `cron` doesn't have 6 or 7 space-separated
				fields. This is checked here, client-side, because the
				server validates the cron expression in a ``preUPDATE``
				hook that runs *before* the report is written -- an
				invalid expression means the report is never created at
				all. Since `sdk.ODSL.update` doesn't raise on error (it
				only prints the status code and any ``x-odsl-error``
				detail), that failure is easy to miss, and shows up
				later as a confusing ``404 ... Not Found`` from a
				follow-up `sdk.ODSL.get` instead of a cron-related
				error.
		"""
		parts = cron.split(' ')
		if len(parts) < 6 or len(parts) > 7:
			raise ValueError(
				"cron must have 6 or 7 space-separated fields (minute hour "
				"dom month dow year [tz]) -- not standard 5-field unix cron. "
				f"Got {len(parts)}: {cron!r}. Did you forget the year field? "
				f"If so, try {cron + ' *'!r} to run in every year."
			)
		self.data['cron'] = cron
		self.data['enabled'] = enabled
		return self

	def set_enabled(self, enabled=True):
		"""Set whether the cron schedule set by `set_cron` is active (wire key: ``enabled``). Defaults to ``False`` server-side if not set."""
		self.data['enabled'] = enabled
		return self

	def set_hide_excel(self, hide=True):
		"""Set whether to hide this report from the Excel add-in (wire key: ``hideExcel``)."""
		self.data['hideExcel'] = hide
		return self

	def set_hide_list(self, hide=True):
		"""Set whether to hide this report from the reports list (wire key: ``hideList``)."""
		self.data['hideList'] = hide
		return self

	def set_tags(self, tags):
		"""Replace the list of tags on this report (wire key: ``tags``).

		Args:
			tags: A list of tag strings.
		"""
		self.data['tags'] = list(tags)
		return self

	def add_tag(self, tag):
		"""Add a single tag to this report without replacing the rest (wire key: ``tags``)."""
		self.data.setdefault('tags', []).append(tag)
		return self

	def set_odg(self, odg):
		"""Set the on-date generator used to decide what dates to run this report for (wire key: ``_odg``).

		Not modelled in detail here -- the server has several shapes
		(filter/distinct/aggregation/curve/matrix/calendar-based), each
		with its own fields; see `ODGFilter`/`ODGDistinct`/
		`ODGAggregation`/`ODGCurve`/`ODGMatrix`/`ODGCalendar` in odsl-core
		for the exact shape of each. Pass whichever one's JSON as a dict.

		Args:
			odg: A dict matching one of the server's on-date generator
				shapes.
		"""
		self.data['_odg'] = odg
		return self

	def set_cache_options(self, cache_options):
		"""Set the caching options for this report (wire key: ``cacheOptions``).

		Args:
			cache_options: A dict matching the server's
				`SmartReportCachingOptions` shape.
		"""
		self.data['cacheOptions'] = cache_options
		return self

	def set_properties(self, properties):
		"""Replace the free-form properties bag for this report (wire key: ``properties``)."""
		self.data['properties'] = properties
		return self

	def set_property(self, key, value):
		"""Set a single free-form property on this report without replacing the rest."""
		self.data.setdefault('properties', {})[key] = value
		return self
