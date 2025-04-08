from odoo import models, fields, api
from num2words import num2words

class Utilities():

    def amount_to_words_np(self, amount):
        units = ["", "एक", "दुई", "तीन", "चार", "पाँच", "छ", "सात", "आठ", "नौ"]
        teens = ["दश", "एघार", "बाह्र", "तेह्र", "चौध", "पन्ध्र", "सोह्र", "सत्र", "अठार", "उन्नाइस"]
        tens = ["", "दश", "बीस", "तीस", "चालीस", "पचास", "साठी", "सत्तरी", "असी", "नब्बे"]
        suffixes = ["", "हजार", "लाख", "करोड"]

        if amount < 0:
            return "ऋणात्मक " + self.amount_to_words_np(-amount)
        
        if amount == 0:
            return "शून्य"

        num_str = str(int(amount))
        num_str = num_str.zfill(((len(num_str) + 1) // 2) * 2)  # Pad to make length even
        words = []

        def _get_word_for_two_digits(two_digit_str):
            if two_digit_str == "00":
                return ""
            elif two_digit_str[0] == "1":
                return teens[int(two_digit_str[1])]
            else:
                tens_word = tens[int(two_digit_str[0])]
                units_word = units[int(two_digit_str[1])]
                return tens_word + (" " + units_word if units_word else "")

        # Split the number into segments of two digits
        segments = [num_str[i:i+2] for i in range(0, len(num_str), 2)]

        for idx, segment in enumerate(segments):
            if segment != "00":
                words.append(_get_word_for_two_digits(segment) + " " + suffixes[len(segments) - idx - 1])

        return " ".join(words).strip()