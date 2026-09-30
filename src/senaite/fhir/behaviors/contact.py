# -*- coding: utf-8 -*-

from AccessControl import ClassSecurityInfo
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import model
from Products.CMFCore import permissions
from senaite.core.interfaces import IContact
from senaite.core.schema import TextLineField
from senaite.fhir import _
from zope.component import adapter
from zope.interface import implementer
from zope.interface import provider


@provider(IFormFieldProvider)
class IExtendedContactBehavior(model.Schema):

    fhir_external_id = TextLineField(
        title=_(u"External ID"),
        description=_(u""),
        required=False,
    )


@implementer(IExtendedContactBehavior)
@adapter(IContact)
class ExtendedContact(object):

    security = ClassSecurityInfo()

    def __init__(self, context):
        self.context = context

    @security.protected(permissions.View)
    def getFHIRExternalID(self):
        accessor = self.context.accessor("fhir_external_id")
        return accessor(self.context)

    @security.protected(permissions.ModifyPortalContent)
    def setFHIRExternalID(self, value):
        mutator = self.context.mutator("fhir_external_id")
        mutator(self.context, value)

    fhir_external_id = property(getFHIRExternalID, setFHIRExternalID)


def getFHIRExternalID(self):
    behavior = IExtendedContactBehavior(self)
    return behavior.getFHIRExternalID()


def setFHIRExternalID(self, value):
    behavior = IExtendedContactBehavior(self)
    behavior.setFHIRExternalID(value)
