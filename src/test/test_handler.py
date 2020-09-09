import os
import re
import unittest
from unittest.mock import Mock, patch

import boto3
import moto
import requests_mock

import src.avail_check.handler as avail_check

from .mocks import MOCK_GOOD_BBY_RESPONSE, MOCK_GOOD_RESPONSE


class TestHandler(unittest.TestCase):
    """
        Tests for lambda handler
    """

    @patch("boto3.client")
    def test_happypath(self, mocked_boto):
        """
            Pass in some good zips and good skus, smooth sailing
        """

        os.environ["BEST_BUY_API_KEY"] = "123456"
        os.environ["TABLE_NAME"] = "FakeTableName"

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
            self.assertDictEqual(response, MOCK_GOOD_RESPONSE)

        self.assertTrue(response["status"] == 200)

    @patch("boto3.client")
    def test_bad_zip(self, mocked_boto):
        """
            Pass in some a bad zip code, should fail
        """

        os.environ["BEST_BUY_API_KEY"] = "123456"
        os.environ["TABLE_NAME"] = "FakeTableName"

        event = {
            "queryStringParameters": {
                "skus": "12345,54321,90123,24601",
                "zip_code": "sdfd23223",
            }
        }

        with requests_mock.Mocker() as m:
            # happy best buy API response
            url_matcher = re.compile(r"https:\/\/api\.bestbuy\.com.*")
            # whenever we use requests to .get this URL, we intercept it
            m.get(url_matcher, **MOCK_GOOD_BBY_RESPONSE)
            response = avail_check.handler(event=event, context={})

        self.assertTrue(response["status"] == 400)

    @patch("boto3.client")
    def test_no_api_key(self, mocked_boto):
        """
            If we don't have an API key set, we should fail hard
        """

        del os.environ["BEST_BUY_API_KEY"]
        event = {
            "queryStringParameters": {
                "skus": "12345,54321,90123,24601",
                "zip_code": "23223",
            }
        }

        response = avail_check.handler(event=event, context={})

        self.assertTrue(response["status"] == 500)

    @patch("boto3.client")
    def test_no_params(self, mocked_boto):
        """
            If we don't have an API key set, we should fail hard
        """

        event = {}

        response = avail_check.handler(event=event, context={})

        self.assertTrue(response["status"] == 400)

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

