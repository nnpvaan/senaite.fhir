FHIR Bundle POST (Patient, Organization and Practitioner identifier validation)
--------------------------------------------------------------------------------

Extends the identifier validation covered by ``bundle_post_08`` (ServiceRequest
and Specimen) to the remaining resource types that carry the same
internal-id/external-id contract: ``Patient``, ``Organization`` and
``Practitioner``. Each of these is also independently POST-able (see
``api.can_create_or_update``'s ``supported_types``), so the validation lives
in their own ``IFHIRToContent`` converters (``ResourceToPatient``,
``ResourceToOrganisation``/``ResourceToClient``, ``ResourceToContact``) and
applies whether the resource arrives standalone or embedded in a Bundle.

1. **Rejection of usual identifier**: a ``usual`` identifier on ``Patient``,
   ``Organization`` or ``Practitioner`` is rejected -- internal ids are
   assigned by SENAITE only, never supplied by the consumer.

2. **Rejection of an invalid external identifier system**: a ``secondary``
   identifier on any of the three must carry the matching default
   ``NamingSystem`` (``patient-mrn``, ``organization-external-id``,
   ``practitioner-external-id`` respectively); any other system (including
   none at all) is rejected.

3. **Practitioner matched by external id**: a ``Practitioner`` whose
   ``secondary`` identifier matches an existing ``Contact``'s ``external_id``
   is resolved to that Contact rather than creating a duplicate -- the
   counterpart of the existing "Update a manually-created counterpart
   (matched by MRN)" Patient test in ``bundle_post.rst``.

Running this test from the buildout directory:

    bin/test test_doctests -t bundle_post_09


Test Setup
~~~~~~~~~~

Needed imports:

    >>> import json
    >>> import transaction
    >>> from pkg_resources import resource_string
    >>> from plone.app.testing import setRoles
    >>> from plone.app.testing import TEST_USER_ID
    >>> from bika.lims import api
    >>> from senaite.fhir import api as fapi
    >>> from senaite.fhir.behaviors.contact import IExtendedContactBehavior

Variables:

    >>> portal = self.portal
    >>> request = self.request
    >>> setup = portal.setup
    >>> fhir_url = "{}/@@FHIR/r5".format(portal.absolute_url())
    >>> browser = self.getBrowser()
    >>> browser.raiseHttpErrors = False
    >>> setRoles(portal, TEST_USER_ID, ["LabManager", "Manager"])

Load Bundle.01.json as the base bundle:

    >>> raw = resource_string("senaite.fhir.tests", "data/Bundle.01.json")
    >>> bundle = json.loads(raw)

    >>> def get_entry(bundle, resource_type):
    ...     matches = [e for e in bundle["entry"]
    ...                if e["resource"]["resourceType"] == resource_type]
    ...     return matches[0]


Setup objects
~~~~~~~~~~~~~

Create the basic SENAITE objects needed for bundle processing:

    >>> client = api.create(portal.clients, "Client",
    ...                     Name="Royal Melbourne Hospital",
    ...                     ClientID="ORG-RMH-MEL")
    >>> labcontact = api.create(portal.bika_setup.bika_labcontacts,
    ...                         "LabContact", Firstname="Lab", Lastname="Boss")
    >>> department = api.create(setup.departments, "Department",
    ...                         title="Chemistry", Manager=labcontact)
    >>> category = api.create(setup.analysiscategories, "AnalysisCategory",
    ...                       title="Liver", Department=department)
    >>> loinc_codes = ["1742-6", "1920-8", "6768-6", "1975-2",
    ...                "1968-7", "2885-2", "1751-7", "5902-2"]
    >>> for num, code in enumerate(loinc_codes):
    ...     service = api.create(
    ...         portal.bika_setup.bika_analysisservices, "AnalysisService",
    ...         title="LFT %s" % code, Keyword="LFT%s" % num,
    ...         Category=category.UID(), ProtocolID=code)
    >>> serum = api.create(setup.sampletypes, "SampleType",
    ...                    title="Serum specimen", Prefix="SER")
    >>> transaction.commit()


Rejection: Patient with a usual identifier
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    >>> raw = resource_string("senaite.fhir.tests", "data/Bundle.01.json")
    >>> bundle = json.loads(raw)
    >>> entry = get_entry(bundle, "Patient")
    >>> entry["resource"]["identifier"] = [
    ...     {
    ...         "use": "usual",
    ...         "system": "https://fhir.senaite.org/NamingSystem/patient-id",
    ...         "value": "INTERNAL-PATIENT-ID"
    ...     }
    ... ]
    >>> browser.post("{}/Bundle".format(fhir_url), json.dumps(bundle),
    ...              content_type="application/json")
    >>> browser.headers["Status"]
    '400 Bad Request'
    >>> outcome = json.loads(browser.contents)
    >>> text = outcome["issue"][0]["details"]["text"]
    >>> "Cannot specify usual identifier externally" in text
    True

No Patient is created -- the whole transaction is rejected:

    >>> portal._p_jar.sync()
    >>> len(portal.patients.objectValues())
    0


Rejection: Patient with an invalid external identifier system
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    >>> raw = resource_string("senaite.fhir.tests", "data/Bundle.01.json")
    >>> bundle = json.loads(raw)
    >>> entry = get_entry(bundle, "Patient")
    >>> entry["resource"]["identifier"] = [
    ...     {"use": "secondary", "value": "MRN-20394857"}
    ... ]
    >>> browser.post("{}/Bundle".format(fhir_url), json.dumps(bundle),
    ...              content_type="application/json")
    >>> browser.headers["Status"]
    '400 Bad Request'
    >>> outcome = json.loads(browser.contents)
    >>> text = outcome["issue"][0]["details"]["text"]
    >>> "Unsupported identifier system in Patient" in text
    True


Rejection: Organization with a usual identifier
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    >>> raw = resource_string("senaite.fhir.tests", "data/Bundle.01.json")
    >>> bundle = json.loads(raw)
    >>> entry = get_entry(bundle, "Organization")
    >>> entry["resource"]["identifier"] = [
    ...     {
    ...         "use": "usual",
    ...         "system": "https://fhir.senaite.org/NamingSystem/organization-id",
    ...         "value": "INTERNAL-ORG-ID"
    ...     }
    ... ]
    >>> browser.post("{}/Bundle".format(fhir_url), json.dumps(bundle),
    ...              content_type="application/json")
    >>> browser.headers["Status"]
    '400 Bad Request'
    >>> outcome = json.loads(browser.contents)
    >>> text = outcome["issue"][0]["details"]["text"]
    >>> "Cannot specify usual identifier externally" in text
    True


Rejection: Organization with an invalid external identifier system
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    >>> raw = resource_string("senaite.fhir.tests", "data/Bundle.01.json")
    >>> bundle = json.loads(raw)
    >>> entry = get_entry(bundle, "Organization")
    >>> entry["resource"]["identifier"] = [
    ...     {
    ...         "use": "secondary",
    ...         "system": "https://example.org/NamingSystem/their-own-id",
    ...         "value": "ORG-RMH-MEL"
    ...     }
    ... ]
    >>> browser.post("{}/Bundle".format(fhir_url), json.dumps(bundle),
    ...              content_type="application/json")
    >>> browser.headers["Status"]
    '400 Bad Request'
    >>> outcome = json.loads(browser.contents)
    >>> text = outcome["issue"][0]["details"]["text"]
    >>> "Unsupported identifier system in Organization" in text
    True


Rejection: Practitioner with a usual identifier
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    >>> raw = resource_string("senaite.fhir.tests", "data/Bundle.01.json")
    >>> bundle = json.loads(raw)
    >>> entry = get_entry(bundle, "Practitioner")
    >>> entry["resource"]["identifier"] = [
    ...     {
    ...         "use": "usual",
    ...         "system": "https://fhir.senaite.org/NamingSystem/practitioner-id",
    ...         "value": "INTERNAL-PRACT-ID"
    ...     }
    ... ]
    >>> browser.post("{}/Bundle".format(fhir_url), json.dumps(bundle),
    ...              content_type="application/json")
    >>> browser.headers["Status"]
    '400 Bad Request'
    >>> outcome = json.loads(browser.contents)
    >>> text = outcome["issue"][0]["details"]["text"]
    >>> "Cannot specify usual identifier externally" in text
    True


Rejection: Practitioner with an invalid external identifier system
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    >>> raw = resource_string("senaite.fhir.tests", "data/Bundle.01.json")
    >>> bundle = json.loads(raw)
    >>> entry = get_entry(bundle, "Practitioner")
    >>> entry["resource"]["identifier"] = [
    ...     {"use": "secondary", "value": "PRACT-DR-SULLIVAN"}
    ... ]
    >>> browser.post("{}/Bundle".format(fhir_url), json.dumps(bundle),
    ...              content_type="application/json")
    >>> browser.headers["Status"]
    '400 Bad Request'
    >>> outcome = json.loads(browser.contents)
    >>> text = outcome["issue"][0]["details"]["text"]
    >>> "Unsupported identifier system in Practitioner" in text
    True

No content was persisted by any of the rejected attempts above:

    >>> portal._p_jar.sync()
    >>> len(portal.patients.objectValues())
    0
    >>> len(client.getContacts())
    0


Success: Practitioner matched by external id (not duplicated)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A Contact already exists under the Client, carrying the same external id
as the bundle's Practitioner:

    >>> contact = api.create(client, "Contact",
    ...                      Firstname="Catherine", Lastname="Sullivan")
    >>> IExtendedContactBehavior(contact).external_id = u"PRACT-DR-SULLIVAN"
    >>> contact.reindexObject()
    >>> transaction.commit()
    >>> portal._p_jar.sync()
    >>> len(client.getContacts())
    1

Posting the (unmodified) bundle resolves the Practitioner to this Contact
instead of creating a duplicate one:

    >>> raw = resource_string("senaite.fhir.tests", "data/Bundle.01.json")
    >>> bundle = json.loads(raw)
    >>> browser.post("{}/Bundle".format(fhir_url), json.dumps(bundle),
    ...              content_type="application/json")
    >>> browser.headers["Status"]
    '200 OK'
    >>> response = json.loads(browser.contents)
    >>> response["type"]
    u'transaction-response'

    >>> portal._p_jar.sync()
    >>> contacts = client.getContacts()
    >>> len(contacts)
    1
    >>> contacts[0].getFullname() == contact.getFullname()
    True

The created Sample's Contact is the pre-existing one:

    >>> samples = client.objectValues("AnalysisRequest")
    >>> len(samples)
    1
    >>> samples[0].getContact().getFullname() == contact.getFullname()
    True
