from odoo.http import Response, request
from odoo import http
import json
import logging

_logger = logging.getLogger(__name__)

class DocumentsTypesController(http.Controller):

    @http.route("/trading/api/get_documents_types", type="http", auth="public", cors="*", methods=["GET"], csrf=False)
    def get_documents_types(self, **kw):
        try:
            # Log the host URL from which the request was made
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            _logger.info(f"Received request from: {hosturl}")

            # Get document_id from the request (if provided)
            document_id = kw.get('document_id')

            if document_id:
                # If document_id is provided, search for that specific document
                record = request.env["documents.types"].sudo().search([('id', '=', int(document_id))], limit=1)

                if not record:
                    # If no document is found with the given ID, return a 404 response
                    return http.Response(
                        status=404,
                        response=json.dumps({
                            "status": "fail",
                            "data": {
                                "message": "Document not found"
                            }
                        }),
                        headers=[('Content-Type', 'application/json')]
                    )

                # Prepare data for the single document
                data = {
                    "document_id": record.id,
                    "name": record.name if record.name else None,
                    "code": record.code if record.code else None,
                }

            else:
                # If no document_id is provided, search for all documents
                records = request.env["documents.types"].sudo().search([])

                # Log the number of records retrieved
                _logger.info(f"Found {len(records)} records in documents.types")

                # Prepare data for all documents
                data = []
                for record in records:
                    data.append({
                        "document_id": record.id,
                        "name": record.name if record.name else None,
                        "code": record.code if record.code else None,
                    })

            # Return the result as JSON response
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            # Log the error and return a 401 response
            _logger.error(f"Error: {str(e)}")
            return http.Response(
                status=401,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": str(e)
                    }
                }),
                headers=[('Content-Type', 'application/json')],
            )
