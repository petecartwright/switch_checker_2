import datetime
import os

import boto3
import requests

BASE_URL = "https://api.bestbuy.com/v1/"


def format_zip_code(zip_code):
    """
    : param zip_code : Whatever got passed to us in the zipcode query parameter
    : return : a string 6-digit zipcode 
    """

    if len(zip_code) not in (5, 9, 10):
        raise ValueError("zip_code must be 5, 9, or 10 characters")

    zip_code = zip_code[:5]

    try:
        new_zip = int(zip_code)
    except ValueError:
        raise ValueError("zip_code must be a number")

    return new_zip


def format_skus(raw_skus):
    """
    : param raw_skus : Comma seperated string of skus from the queryParameters
    : return : String[] of skus
    """
    skus = raw_skus.split(",")
    for sku in skus:
        try:
            int(sku)
        except ValueError:
            raise ValueError(f"sku {sku} is invalid - must be an integer")

    return skus


def get_stock_near_zip(zip_code, product_id):
    """
    ::param:: zip_code str
    ::param:: product_id str

    ::return:: list of stores within 250miles of zip_code that have the product in stock
    """

    api_key = os.environ.get("BEST_BUY_API_KEY")

    if not api_key:
        print("BEST_BUY_API_KEY variable isn't set (?????)")

    api_url = f"https://api.bestbuy.com/v1/products/{product_id}/stores.json?postalCode={zip_code}&apiKey={api_key}"

    response = requests.get(api_url)
    stores = response.json().get("stores") or []

    return stores


def add_stock_to_table(stock, sku, zip_code):
    # print("****************************************************")
    # print("****************************************************")
    # print(stock)
    # print("****************************************************")
    # print("****************************************************")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client = boto3.client("dynamodb")

    responses = []
    for store in stock:
        response = client.put_item(
            TableName=os.environ["TABLE_NAME"],
            Item={
                "refresh_date": {"S": timestamp},
                "zip_code": {"S": zip_code},
                "sku": {"S": sku},
                "storeID": {"S": store["storeID"]},
                "name": {"S": store["name"]},
                "address": {"S": store["address"]},
                "city": {"S": store["city"]},
                "state": {"S": store["state"]},
                "postalCode": {"S": store["postalCode"]},
                "storeType": {"S": store["storeType"]},
                "lowStock": {"S": str(store["lowStock"])},
                "distance": {"S": str(store["distance"])},
            },
        )
        responses.append(response)

    return responses


def fetch_data(query_params):

    zip_code = format_zip_code(query_params.get("zip_code")) or "23223"
    raw_skus = query_params.get("skus")
    if raw_skus:
        skus = format_skus(raw_skus)
    else:
        skus = [
            "6364255",  # Red/blue switch
            "6364253",  # Gray/gray switch
            "6257142",  # Lite, Yellow
            "6257148",  # Lite, Coral
            "6257139",  # Lite, Turquoise
            "6257135",  # Lite, Gray
        ]

    stock = {sku: [] for sku in skus}
    for sku in skus:
        stock_near_zip = get_stock_near_zip(zip_code=zip_code, product_id=sku)
        stock[sku] = stock_near_zip

        # print(stock_near_zip)
        if stock_near_zip:
            add_stock_to_table(stock=stock, sku=sku, zip_code=zip_code)

    return len(skus), stock


def handler(event, context):
    print("************************")
    print("Event:")
    print(event)
    print("************************")
    print("Context:")
    print(context)
    print("************************")

    query_params = event.get("queryStringParameters")
    if query_params:
        try:
            num_skus, stock_found = fetch_data(query_params)
            return {
                "status": 200,
                "number_of_skus": num_skus,
                "stock_found": stock_found,
                "error": "",
            }

        except ValueError as err:
            return {
                "status": 400,
                "error": f"Bad Request: {err}",
            }
        except Exception as err:
            # If anything else goes wrong, don't leak implementation details
            print("*********************************************")
            print(typeof(err))
            print("*********************************************")
            return {
                "status": 500,
                "error": f"Internal Server Error",
            }

    else:
        return {
            "status": 400,
            "error": "Bad request - query parameters of `sku` or `zip_code` required",
        }
