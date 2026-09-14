# -*- coding: utf-8 -*-

from bika.lims import api
from senaite.fhir import logger
from senaite.fhir.setuphandlers import setup_behaviors


def setup_contact_behavior(tool):
    """Add patient behavior
    """
    logger.info("Setup Contact behavior ...")
    portal = api.get_portal()
    setup_behaviors(portal)
    logger.info("Setup Contact behavior [DONE]")
