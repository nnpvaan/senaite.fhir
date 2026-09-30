FHIR external ID of Contacts
----------------------------

`senaite.fhir` extends `Contact` with the `IExtendedContactBehavior`
behavior, that adds the `fhir_external_id` field: the identifier assigned
to the practitioner (`use=secondary`) by the system of the FHIR API consumer.
The field is indexed in the contacts catalog, so a `Practitioner` can be
matched to its counterpart Contact.

See https://fhir.senaite.org/identifiers.html

This test covers the install, upgrade and uninstall of the behavior and the
index, and the accessors of the field. The matching of a `Practitioner` to a
Contact is covered by `bundle_post.rst`.

Running this test from the buildout directory:

    bin/test test_doctests -t contact_behavior


Test Setup
~~~~~~~~~~

Needed imports:

    >>> from bika.lims import api
    >>> from plone.app.testing import setRoles
    >>> from plone.app.testing import TEST_USER_ID
    >>> from plone.autoform.interfaces import IFormFieldProvider
    >>> from senaite.core.catalog import CONTACT_CATALOG
    >>> from senaite.fhir import setuphandlers
    >>> from senaite.fhir.behaviors.contact import IExtendedContactBehavior
    >>> from senaite.fhir.upgrade.v01_00_000 import setup_contact_behavior

Variables:

    >>> portal = self.portal
    >>> setup_tool = api.get_tool("portal_setup")
    >>> fti = api.get_tool("portal_types").getTypeInfo("Contact")
    >>> catalog = api.get_tool(CONTACT_CATALOG)
    >>> behavior_id = "senaite.fhir.contact.IExtendedContactBehavior"
    >>> setRoles(portal, TEST_USER_ID, ["LabManager", "Manager"])


Install
~~~~~~~

The behavior is assigned to the `Contact` type on install:

    >>> behavior_id in fti.behaviors
    True

It provides the form fields, so `fhir_external_id` is displayed in the edit
form of the Contact:

    >>> IFormFieldProvider.providedBy(IExtendedContactBehavior)
    True
    >>> "fhir_external_id" in IExtendedContactBehavior.names()
    True

And the index is added to the contacts catalog:

    >>> "fhir_external_id" in catalog.indexes()
    True

Assigning the behaviors again does not add the behavior twice:

    >>> setuphandlers.setup_behaviors(portal)
    >>> list(fti.behaviors).count(behavior_id)
    1


Accessors
~~~~~~~~~

Create a Contact:

    >>> client = api.create(portal.clients, "Client",
    ...                     Name="Behavior Lab", ClientID="BHV")
    >>> contact = api.create(client, "Contact",
    ...                      Firstname="Rita", Surname="Mohale")

The Contact has no external ID by default:

    >>> contact.getFHIRExternalID() is None
    True

The field is a `TextLineField`: the value is stored as unicode, with leading
and trailing whitespaces removed, and returned as UTF-8 encoded bytes, as the
other accessors of the Contact do:

    >>> contact.setFHIRExternalID(u"  PRACT-RITA-MOHALE  ")
    >>> contact.getFHIRExternalID()
    'PRACT-RITA-MOHALE'

The field is also accessible through the behavior:

    >>> behavior = IExtendedContactBehavior(contact)
    >>> behavior.fhir_external_id
    'PRACT-RITA-MOHALE'
    >>> behavior.fhir_external_id = u"PRACT-R-MOHALE"
    >>> contact.getFHIRExternalID()
    'PRACT-R-MOHALE'

Once reindexed, the Contact can be searched by it:

    >>> contact.reindexObject()
    >>> query = {"fhir_external_id": "PRACT-R-MOHALE"}
    >>> brains = api.search(query, CONTACT_CATALOG)
    >>> [api.get_object(brain) for brain in brains] == [contact]
    True


Upgrade
~~~~~~~

Simulate a site from before the upgrade step, without behavior and index:

    >>> setuphandlers.remove_behaviors(portal)
    >>> behavior_id in fti.behaviors
    False
    >>> catalog.delIndex("fhir_external_id")
    >>> "fhir_external_id" in catalog.indexes()
    False

Run the upgrade step:

    >>> setup_contact_behavior(setup_tool)
    >>> behavior_id in fti.behaviors
    True
    >>> "fhir_external_id" in catalog.indexes()
    True

A new index is empty, so reindex the Contact to search by it again:

    >>> contact.reindexObject()
    >>> brains = api.search(query, CONTACT_CATALOG)
    >>> [api.get_object(brain) for brain in brains] == [contact]
    True


Uninstall
~~~~~~~~~

The behavior is removed from the `Contact` type on uninstall, while other
behaviors are kept:

    >>> behaviors = list(fti.behaviors)
    >>> setuphandlers.remove_behaviors(portal)
    >>> behavior_id in fti.behaviors
    False
    >>> list(fti.behaviors) == [b for b in behaviors if b != behavior_id]
    True

Types without behaviors (e.g. Archetypes) are skipped:

    >>> original = setuphandlers.BEHAVIORS
    >>> setuphandlers.BEHAVIORS = [("Client", [behavior_id])]
    >>> setuphandlers.remove_behaviors(portal)
    >>> setuphandlers.setup_behaviors(portal)
    >>> setuphandlers.BEHAVIORS = original

Restore the behavior:

    >>> setuphandlers.setup_behaviors(portal)
    >>> behavior_id in fti.behaviors
    True
