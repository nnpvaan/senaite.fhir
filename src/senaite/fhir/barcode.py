# -*- coding: utf-8 -*-

"""Generate the printable barcode attachment carried by FHIR Specimens."""

from __future__ import absolute_import

import base64
from io import BytesIO

from barcode import Code39
from barcode.writer import ImageWriter
from bika.lims.utils import createPdf
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.fhir.config import SPECIMEN_BARCODE_EXTENSION_URL


BARCODE_CONTENT_TYPE = "application/pdf"
MODULE_WIDTH = 0.25
BAR_HEIGHT = 14
QUIET_ZONE = 2.5
DPI = 300
BARCODE_OPTIONS = {
    "dpi": DPI,
    "module_height": BAR_HEIGHT,
    "module_width": MODULE_WIDTH,
    "quiet_zone": QUIET_ZONE,
    "write_text": False,
}


class BarcodePdfTemplate(BrowserView):
    """Render the barcode label template with a SENAITE request context."""

    template = ViewPageTemplateFile("templates/specimen_barcode.pt")

    def __call__(self):
        return self.template()


def get_barcode_extension(sample_id, context):
    """Return the barcode-only extension for ``sample_id``.
    """
    output = BytesIO()
    barcode = Code39(sample_id, writer=ImageWriter(), add_checksum=False)
    barcode.write(output, options=BARCODE_OPTIONS)
    image_uri = "data:image/png;base64,{}".format(
        base64.b64encode(output.getvalue()))
    view = BarcodePdfTemplate(context, context.REQUEST)
    view.image_uri = image_uri
    pdf = createPdf(view())
    return {
        "url": SPECIMEN_BARCODE_EXTENSION_URL,
        "valueAttachment": {
            "contentType": BARCODE_CONTENT_TYPE,
            "data": base64.b64encode(pdf),
        },
    }
