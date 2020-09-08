import os
import re
import unittest
from unittest.mock import Mock, patch

import requests_mock

import src.avail_check.handler as avail_check


MOCK_GOOD_BBY_RESPONSE = {
    "status_code": 200,
    "json": {
        "ispuEligible": True,
        "stores": [
            {
                "storeID": "1465",
                "name": "Mechanicsville",
                "address": "7297 Battle Hill Dr",
                "city": "Mechanicsville",
                "state": "VA",
                "postalCode": "23111",
                "storeType": "Self_Delivery_Store",
                "minPickupHours": None,
                "lowStock": False,
                "distance": 4.5,
            },
            {
                "storeID": "1013",
                "name": "Glen Allen",
                "address": "9901 Brook Rd",
                "city": "Glen Allen",
                "state": "VA",
                "postalCode": "23059",
                "storeType": "Self_Delivery_Store",
                "minPickupHours": None,
                "lowStock": False,
                "distance": 9.0,
            },
            {
                "storeID": "422",
                "name": "Chesterfield",
                "address": "1560 W Koger Center Blvd",
                "city": "Richmond",
                "state": "VA",
                "postalCode": "23235",
                "storeType": "Self_Delivery_Store",
                "minPickupHours": None,
                "lowStock": False,
                "distance": 12.3,
            },
        ],
    },
}

BAD_BBY_DATA = {}


class TestHandler(unittest.TestCase):
    def test_happypath(self):
        """
            Pass in some good zips and good skus, smooth sailing
        """

        os.environ["BEST_BUY_API_KEY"] = "123456"
        os.environ["BEST_BUY_API_KEY"] = "FakeTableName"

        event = {
            "queryStringParameters": {
                "skus": "12345,54321,90123,24601",
                "zip_code": "23223",
            }
        }

        with requests_mock.Mocker() as m:
            # happy best buy API response
            url_matcher = re.compile(r"https:\/\/api\.bestbuy\.com.*")
            # whenever we use requests to .get this URL, we intercept it
            m.get(url_matcher, **MOCK_GOOD_BBY_RESPONSE)
            response = avail_check.handler(event=event, context={})

            self.assertDictEqual(
                response,
                {"status": 200, "number_of_skus": 6, "stock_found": 5, "error": ""},
            )

        self.assertTrue(response["status"] == 200)

    def test_format_zip_code(self):
        """
            Test that the zip code formatter handles good and bad inputs correcly
        """

        good_5_digit_code = "23223"
        good_9_digit_code = "23223-1234"
        another_good_9_digit_code = "232231234"

        bad_5_digit_code = "2aaa3"
        too_short_code = "2322"
        too_long_code = "23223-123456"

        self.assertEqual(avail_check.format_zip_code(good_5_digit_code), 23223)
        self.assertEqual(avail_check.format_zip_code(good_9_digit_code), 23223)
        self.assertEqual(avail_check.format_zip_code(another_good_9_digit_code), 23223)

        self.assertRaises(ValueError, avail_check.format_zip_code, bad_5_digit_code)
        self.assertRaises(ValueError, avail_check.format_zip_code, too_short_code)
        self.assertRaises(ValueError, avail_check.format_zip_code, too_long_code)

    def test_format_skus(self):
        """
            Test that the sku formatter handles good and bad inputs correcly
        """

        good_single_sku = "123456789"
        good_multiple_skus = "123456789,987654321,678901234"

        bad_single_sku = "12345kjnn9"
        bad_multiple_skus = "123456789,98abc4321,678901234"
        bad_delimiters = "123456789.98abc4321+678901234"

        self.assertEqual(avail_check.format_skus(good_single_sku), ["123456789"])
        self.assertEqual(
            avail_check.format_skus(good_multiple_skus),
            ["123456789", "987654321", "678901234"],
        )

        self.assertRaises(ValueError, avail_check.format_skus, bad_single_sku)
        self.assertRaises(ValueError, avail_check.format_skus, bad_multiple_skus)
        self.assertRaises(ValueError, avail_check.format_skus, bad_delimiters)

