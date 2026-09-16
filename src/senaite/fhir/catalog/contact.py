# -*- coding: utf-8 -*-

from plone.indexer import indexer
from senaite.core.interfaces import IContact
from senaite.core.interfaces.catalog import IContactCatalog
from senaite.fhir.behaviors.contact import getExternalId


@indexer(IContact, IContactCatalog)
def getExternalID(instance):
    """Indexes the external id assigned by the FHIR API consumer, so
    Practitioner resources can be matched to an existing Contact by it
    """
    return getExternalId(instance) or ""
