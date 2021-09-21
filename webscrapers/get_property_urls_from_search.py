"""Web scrapes properties from zillow search URL."""
import selenium.webdriver.common.action_chains
from bs4 import BeautifulSoup
from selenium import webdriver
import requests
import time


PROPERTIES_PER_PAGE = 40  # Number of properties zillow displays per search page
DRIVER_DELAY = 0.05  # Delay between actions for selenium driver
url_search: str
zillow: BeautifulSoup
page: requests.Session()
driver: webdriver.Chrome


def _set_url_search(url) -> str:
    """Gets zillow search URL from user or file when running analysis"""

    if url:
        _url = url
    else:
        _url = str(input("Enter full URL from zillow search: "))

    while _url[:23] != 'https://www.zillow.com/' or len(_url) < 29:
        _url = str(input("Enter full URL from zillow search: "))
    print()

    return _url


def set_page_search(url) -> None:
    """Gets html page to parse"""

    global url_search, zillow, page

    # Zillow has bot detection. This handles it.
    req_headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.8',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                      ' (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
    }
    with requests.Session() as s:
        url_search = _set_url_search(url)
        zillow_page = s.get(url_search, headers=req_headers).text
        page = zillow_page  # Hoping this reduces unnecessary calls to zillow for certain functions

    # Creates beautiful soup object
    zillow = BeautifulSoup(zillow_page, 'html.parser')


def load_js_elements_on_page() -> None:
    """Runs chrome browser with selenium"""

    global zillow

    chrome = webdriver.Chrome()
    chrome.get(url_search)

    # Use this url to test captcha
    # chrome.get('https://www.zillow.com/captchaPerimeterX/?url=%2fhomes%2fCT_rb%2f&uuid=dd265dba-1ac2-11ec-a883-615050666d69&vid=')

    if 'captcha' in chrome.current_url.lower():
        time.sleep(1)
        target = chrome.find_element_by_id('px-captcha')
        action = webdriver.ActionChains(chrome)
        action.click_and_hold(on_element=target)
        action.perform()
        time.sleep(5)
        action.release(on_element=target)
        action.perform()
        time.sleep(10)

    from selenium.webdriver.common.keys import Keys
    target = chrome.find_element_by_tag_name("body")
    for i in range(10):
        target.send_keys(Keys.PAGE_DOWN)
        time.sleep(DRIVER_DELAY)

    zillow_page = chrome.page_source
    zillow = BeautifulSoup(zillow_page, 'html.parser')


def is_url_valid(url) -> bool:
    """Checks if URL was incorrectly inputted by looking for an error page"""

    # Zillow has bot detection. This handles it.
    req_headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.8',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                      ' (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
    }
    with requests.Session() as s:
        zillow_page = s.get(url, headers=req_headers).text

    # Creates beautiful soup object
    temp = BeautifulSoup(zillow_page, 'html.parser')

    valid = False if temp.find(id="zillow-error-page") else True

    return valid


def get_url() -> str:
    """Returns URL for property"""
    return url_search


def get_num_pages_and_lisings() -> tuple:
    """Returns the number of pages in the search"""

    # Checks if looking at agent listings or other listings. Other listings will always have 'cat2' in url.
    if 'cat2' not in url_search:
        listings = int(zillow.find_all(class_="total-text")[0].string.replace(',', ''))
        num_pages = -(-listings // PROPERTIES_PER_PAGE)  # Ceiling division
    else:
        listings = int(zillow.find_all(class_="total-text")[1].string.replace(',', ''))
        num_pages = -(-listings // PROPERTIES_PER_PAGE)  # Ceiling division

    return num_pages, listings


def get_all_urls_and_prices() -> dict:
    """Gets urls and prices for all properties on a zillow search page"""

    load_js_elements_on_page()

    base = zillow.find('div', id="grid-search-results").find('ul')

    properties_url_price = {}
    for li in base.contents:
        if li.find('div', id="nav-ad-container"):
            continue
        properties_url_price[_get_property_url_from_search(li)] = _get_price_from_search(li)

    return properties_url_price


def _get_property_url_from_search(li) -> str:
    """Gets url for property from search url"""

    property_url = li.find('a', href=True)['href']

    return property_url


def _get_price_from_search(li) -> int:
    """Gets price for property from search url"""

    price = int(li.find('div', class_="list-card-price").string.lstrip('$').replace(',', ''))

    return price

set_page_search('https://www.zillow.com/homes/CT_rb/')
print(get_all_urls_and_prices())
