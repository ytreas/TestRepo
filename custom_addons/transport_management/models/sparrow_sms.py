from odoo import models, fields, api
import requests
import logging
import re

_logger = logging.getLogger(__name__)

class SparrowSMS(models.Model):
    _name = 'sparrow.sms'
    _description = 'Sparrow SMS Integration'

    def _format_nepal_phone_number(self, phone_number):
        """
        Format Nepal phone number for Sparrow SMS API
        Handles various input formats and converts to proper format
        """
        if not phone_number:
            return None
            
        # Remove all non-digit characters
        clean_number = re.sub(r'\D', '', str(phone_number))
        
        # Handle different input formats
        if len(clean_number) == 10 and clean_number.startswith('98'):
            return clean_number
        elif len(clean_number) == 10 and clean_number.startswith('97'):
            return clean_number
        elif len(clean_number) == 13 and clean_number.startswith('977'):
            # With full country code: 9779861973100
            return clean_number[3:]  # Remove country code
        elif len(clean_number) == 12 and clean_number.startswith('77'):
            # Partial country code: 779861973100  
            return clean_number[2:]  # Remove partial country code
        elif len(clean_number) == 9:
            # Missing leading digit: 861973100
            return '9' + clean_number
        else:
            # Return as-is and let the API handle it
            return clean_number

    @api.model
    def send_sms(self, message, to):
        """
        Send SMS via Sparrow SMS API
        Args:
            message: SMS message content
            to: Phone number (will be formatted automatically)
        """
        # Format the phone number
        formatted_number = self._format_nepal_phone_number(to)
        
        if not formatted_number:
            _logger.error("Invalid phone number provided: %s", to)
            return False
            
        url = "http://api.sparrowsms.com/v2/sms/"
        payload = {
            'token': 'v2_XdQGZBTY6MaqxKVTmZGf6erwEk5.8UBT',
            'from': 'InfoSMS',
            'to': formatted_number,
            'text': message
        }

        _logger.info("Attempting to send SMS to: %s (formatted from: %s)", formatted_number, to)
        
        try:
            response = requests.post(url, data=payload, timeout=30)
            res = response.json()
            
            _logger.info("SMS API Response: %s", res)
            
            if res.get("response_code") == 200:
                _logger.info("SMS sent successfully to %s", formatted_number)
                return True
            else:
                _logger.error("Failed to send SMS to %s: %s", formatted_number, res)

                if not formatted_number.startswith('977'):
                    _logger.info("Retrying with country code...")
                    return self._retry_with_country_code(message, formatted_number)
                
                return False
                
        except requests.exceptions.Timeout:
            _logger.error("SMS request timed out for number: %s", formatted_number)
            return False
        except requests.exceptions.RequestException as e:
            _logger.error("Network error while sending SMS: %s", str(e))
            return False
        except Exception as e:
            _logger.exception("Unexpected error while sending SMS: %s", str(e))
            return False

    def _retry_with_country_code(self, message, phone_number):
        """Retry sending SMS with country code prefix"""
        country_code_number = '977' + phone_number
        
        url = "http://api.sparrowsms.com/v2/sms/"
        payload = {
            'token': 'v2_XdQGZBTY6MaqxKVTmZGf6erwEk5.8UBT',
            'from': 'InfoSMS',
            'to': country_code_number,
            'text': message
        }

        _logger.info("Retrying SMS with country code: %s", country_code_number)
        
        try:
            response = requests.post(url, data=payload, timeout=30)
            res = response.json()
            
            _logger.info("SMS API Retry Response: %s", res)
            
            if res.get("response_code") == 200:
                _logger.info("SMS sent successfully on retry to %s", country_code_number)
                return True
            else:
                _logger.error("Failed to send SMS on retry: %s", res)
                return False
                
        except Exception as e:
            _logger.exception("Error in SMS retry: %s", str(e))
            return False

    @api.model
    def test_sms_formats(self, phone_number, message="Test message"):
        """
        Test different phone number formats - useful for debugging
        """
        formats_to_try = [
            phone_number,  # Original
            self._format_nepal_phone_number(phone_number),
            '977' + self._format_nepal_phone_number(phone_number),
            '+977' + self._format_nepal_phone_number(phone_number),
        ]
        
        for fmt in formats_to_try:
            if fmt:
                _logger.info("Testing SMS format: %s", fmt)
                result = self.send_sms(message, fmt)
                if result:
                    _logger.info("SUCCESS with format: %s", fmt)
                    return fmt
                    
        return False