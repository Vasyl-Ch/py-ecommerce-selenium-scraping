import logging
import csv
import sys
from dataclasses import dataclass, asdict, fields
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as es
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException
)

BASE_URL = "https://webscraper.io/"
URLS = [
    urljoin(BASE_URL, "test-sites/e-commerce/more/"),
    urljoin(BASE_URL, "test-sites/e-commerce/more/computers"),
    urljoin(BASE_URL, "test-sites/e-commerce/more/computers/laptops"),
    urljoin(BASE_URL, "test-sites/e-commerce/more/computers/tablets"),
    urljoin(BASE_URL, "test-sites/e-commerce/more/phones"),
    urljoin(BASE_URL, "test-sites/e-commerce/more/phones/touch"),
]

_driver: WebDriver | None = None


def set_driver(driver: WebDriver) -> None:
    global _driver
    _driver = driver


def get_driver() -> WebDriver:
    return _driver


@dataclass
class Product:
    title: str
    description: str
    price: float
    rating: int
    num_of_reviews: int


PRODUCT_FIELDS = [f.name for f in fields(Product)]

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def expand_dynamic_content(driver: WebDriver, locator: str) -> None:
    while True:
        try:
            button = WebDriverWait(driver, 2).until(
                es.presence_of_element_located((By.CSS_SELECTOR, locator))
            )
            if not button.is_displayed():
                break
            driver.execute_script("arguments[0].click();", button)
        except (TimeoutException, ElementClickInterceptedException):
            break


def parse_single_product(product_tag: Tag) -> Product:
    title_elem = product_tag.select_one(".title")
    title = title_elem["title"] if title_elem else "No Title"

    description = " ".join(product_tag.select_one(".description").text.split())
    price = float(product_tag.select_one(".price").text.replace("$", ""))

    rating_elem = product_tag.select_one("p[data-rating]")
    rating = int(rating_elem["data-rating"]) if rating_elem else len(
        product_tag.select(".ws-icon-star")
    )

    num_of_reviews = int(
        product_tag.select_one(".review-count").text.split()[0]
    )

    return Product(
        title=title,
        description=description,
        price=price,
        rating=rating,
        num_of_reviews=num_of_reviews,
    )


def write_products_to_csv(products: list[Product], filename: str) -> None:
    if not products:
        logging.warning(f"{filename}: нет данных")
        return

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=PRODUCT_FIELDS)
        writer.writeheader()

        for product in products:
            writer.writerow(asdict(product))


def get_all_products() -> None:
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")

    with webdriver.Chrome(options=options) as driver:
        set_driver(driver)

        for url in URLS:
            logging.info(f"Processing category: {url}")
            driver.get(url)

            expand_dynamic_content(driver, "a.ecomerce-items-scroll-more")

            soup = BeautifulSoup(driver.page_source, "html.parser")
            product_tags = soup.select(".thumbnail")

            products = [
                parse_single_product(tag)
                for tag in product_tags
            ]

            if url.endswith("/more") or url.endswith("/more/"):
                name = "home"
            else:
                name = url.rstrip("/").split("/")[-1]

            write_products_to_csv(products, f"{name}.csv")


if __name__ == "__main__":
    get_all_products()
