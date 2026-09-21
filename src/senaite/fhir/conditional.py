# -*- coding: utf-8 -*-

from bika.lims import api
from senaite.core.catalog import CLIENT_CATALOG
from senaite.core.catalog import CONTACT_CATALOG
from senaite.fhir import api as fapi
from senaite.fhir.config import EXTERNAL_ID_SYSTEMS
from senaite.fhir.config import INTERNAL_ID_SYSTEMS
from senaite.fhir.converter import to_naming_system_url
from senaite.fhir.exceptions import ServiceRequestValidationError
from senaite.patient.catalog import PATIENT_CATALOG

# Resource type -> (catalog id, external-identifier index name)
MATCH_TABLE = {
    "Patient": (PATIENT_CATALOG, "patient_mrn"),
    "Practitioner": (CONTACT_CATALOG, "contact_external_id"),
    "Organization": (CLIENT_CATALOG, "getClientID"),
}


def get_if_none_exist(resource):
    """Returns the raw `ifNoneExist` string declared on the bundle entry of
    the given resource, or None when absent, the resource type is not one
    SENAITE evaluates ifNoneExist for (Specimen/ServiceRequest carry
    `request.ifNoneExist 0..0` per the IG -- silently ignored here, same as
    every other resource type this module doesn't recognize), or the
    resource isn't part of a bundle at all (e.g. a standalone POST /Patient,
    which has no entry.request to begin with).

    :param resource: the FHIR resource being processed by post()
    :returns: the raw ifNoneExist value, or None
    """
    if resource.resourceType not in MATCH_TABLE:
        return None
    bundle = resource.get("_bundle")
    if not bundle:
        return None
    return bundle.get_request(resource).get("ifNoneExist")


def parse_if_none_exist(raw):
    """Parses an `ifNoneExist` value of the `identifier=<system>|<value>`
    form mandated by the SenaiteRequestBundle profile.

    :param raw: the raw ifNoneExist string
    :returns: (system, value) tuple; either half is "" when `raw` is
        malformed or doesn't use the `identifier` search parameter
    """
    param, eq, query = (raw or "").partition("=")
    if not eq or param != "identifier":
        return "", ""
    if "|" not in query:
        # FHIR token search: no "|" means a bare value with no system
        return "", query
    system, _, value = query.partition("|")
    return system, value


def get_valid_systems(resource_type):
    """Returns the (internal_system_url, external_system_url) NamingSystem
    URIs recognized for ifNoneExist on the given resource type
    """
    internal_id = dict(INTERNAL_ID_SYSTEMS)[resource_type]
    external_id = dict(EXTERNAL_ID_SYSTEMS)[resource_type]
    return to_naming_system_url(internal_id), to_naming_system_url(external_id)


def find_by_if_none_exist(resource, raw):
    """Resolves the ifNoneExist conditional-create precondition for a
    Patient, Practitioner or Organization bundle entry.

    Business rules (per naralabs/senaite.fhir.model#39): zero matches means
    the caller should proceed to create as normal; exactly one match means
    the entry is already satisfied and the submitted body must be discarded;
    more than one match -- or a missing/unrecognized/valueless identifier,
    since the precondition can't be safely evaluated either way -- rejects
    the whole bundle with 412 Precondition Failed.

    :param resource: the FHIR resource being processed (Patient, Practitioner
        or Organization -- caller must have already confirmed via
        get_if_none_exist that this type is supported)
    :param raw: the raw ifNoneExist string (from get_if_none_exist)
    :returns: the matched content object, or None for zero matches
    :raises ServiceRequestValidationError: code="multiple-matches" (mapped
        to HTTP 412 by post()) when the precondition can't be safely
        evaluated
    """
    resource_type = resource.resourceType
    expression = ["{}.request.ifNoneExist".format(resource_type)]
    system, value = parse_if_none_exist(raw)
    internal_system, external_system = get_valid_systems(resource_type)

    if not system:
        raise ServiceRequestValidationError(
            "Missing identifier system in {}.request.ifNoneExist: {!r}"
            .format(resource_type, raw),
            expression=expression, code="multiple-matches")
    if system not in (internal_system, external_system):
        raise ServiceRequestValidationError(
            "Unsupported identifier system in {}.request.ifNoneExist: {}"
            .format(resource_type, system),
            expression=expression, code="multiple-matches")
    if not value:
        raise ServiceRequestValidationError(
            "Missing identifier value in {}.request.ifNoneExist: {!r}"
            .format(resource_type, raw),
            expression=expression, code="multiple-matches")

    portal_type = fapi.get_portal_type(resource)
    catalog, external_index = MATCH_TABLE[resource_type]
    index = "id" if system == internal_system else external_index
    brains = api.search({"portal_type": portal_type, index: value}, catalog)

    if len(brains) > 1:
        raise ServiceRequestValidationError(
            "Multiple {} resources match ifNoneExist: {}"
            .format(resource_type, raw),
            expression=expression, code="multiple-matches")

    return api.get_object(brains[0]) if brains else None
