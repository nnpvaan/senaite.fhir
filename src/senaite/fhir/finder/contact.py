# -*- coding: utf-8 -*-

from bika.lims import api
from senaite.core.catalog import CONTACT_CATALOG
from senaite.fhir.converter import get_by_key
from senaite.fhir.interfaces import IContentFinder
from senaite.fhir.interfaces import IPractitionerResource
from zope.component import adapter
from zope.interface import implementer


@adapter(IPractitionerResource)
@implementer(IContentFinder)
class ContactFinder(object):
    """Adapter in charge of searching the counterpart Contact object of a
    FHIR Practitioner resource
    """

    def __init__(self, resource):
        self.resource = resource

    def find(self):
        """Looks for the resource's counterpart Contact object
        """
        # search by external id (use=secondary)
        identifier = self.resource.get_external_id()
        if identifier and identifier.value:
            query = dict(portal_type="Contact",
                         contact_external_id=identifier.value)
            brains = api.search(query, CONTACT_CATALOG)
            if len(brains) == 1:
                return api.get_object(brains[0])

        # fallback to search by fullname (ignorecase)
        name = get_by_key(self.resource.name, key="use", value="official")
        if not name:
            names = self.resource.name
            name = names[0] if names else None
        fullname = name.get_fullname() if name else None
        if fullname:
            query = dict(portal_type="Contact", getFullname=fullname)
            brains = api.search(query, CONTACT_CATALOG)
            if len(brains) == 1:
                return api.get_object(brains[0])

        return None
