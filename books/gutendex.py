from io import BytesIO
from time import sleep

import requests
from django.utils.text import slugify
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .epub_importer import import_epub
from .models import Book


GUTENDEX_BASE_URL = "https://gutendex.com/books/"

session = requests.Session()

retry = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)

adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)

REQUEST_HEADERS = {
    "User-Agent": "bookvo-personal/1.0 (personal learning application)",
    "Accept": "application/json",
}


def _get(url, **kwargs):
    last_error = None

    for _ in range(3):
        try:
            response = session.get(
                url,
                headers=REQUEST_HEADERS,
                timeout=(20, 90),
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            last_error = error
            sleep(2)

    raise last_error


def _get_epub_url(formats):
    return (
        formats.get("application/epub+zip")
        or formats.get("application/epub+zip; charset=binary")
        or ""
    )


def _author_names(authors):
    return ", ".join(
        author.get("name", "")
        for author in authors
        if author.get("name")
    )


def get_catalog_books(query="", page=1):
    params = {
        "languages": "en",
        "page": page,
    }

    if query:
        params["search"] = query

    response = _get(GUTENDEX_BASE_URL, params=params)
    data = response.json()

    results = []

    for item in data.get("results", []):
        formats = item.get("formats", {})

        results.append({
            "gutenberg_id": item["id"],
            "title": item.get("title", ""),
            "author": _author_names(item.get("authors", [])),
            "languages": item.get("languages", []),
            "subjects": item.get("subjects", []),
            "bookshelves": item.get("bookshelves", []),
            "download_count": item.get("download_count", 0),
            "cover_url": formats.get("image/jpeg", ""),
            "epub_url": _get_epub_url(formats),
            "text_url": (
                formats.get("text/plain; charset=utf-8")
                or formats.get("text/plain")
                or ""
            ),
        })

    return {
        "count": data.get("count", 0),
        "next": data.get("next"),
        "previous": data.get("previous"),
        "results": results,
    }


def get_catalog_book(gutenberg_id):
    response = _get(f"{GUTENDEX_BASE_URL}{gutenberg_id}")
    item = response.json()
    formats = item.get("formats", {})

    return {
        "gutenberg_id": item["id"],
        "title": item.get("title", ""),
        "author": _author_names(item.get("authors", [])),
        "cover_url": formats.get("image/jpeg", ""),
        "epub_url": _get_epub_url(formats),
    }


def import_gutenberg_book(owner, gutenberg_id):
    if Book.objects.filter(
        owner=owner,
        gutenberg_id=gutenberg_id,
    ).exists():
        raise ValueError(
            "Эта книга уже импортирована в вашу библиотеку."
        )

    catalog_book = get_catalog_book(gutenberg_id)

    if not catalog_book["epub_url"]:
        raise ValueError(
            "Для этой книги в каталоге нет EPUB-версии."
        )

    response = _get(catalog_book["epub_url"])
    epub_file = BytesIO(response.content)
    epub_file.name = (
        f"{slugify(catalog_book['title']) or gutenberg_id}.epub"
    )

    book = import_epub(owner, epub_file)

    book.gutenberg_id = gutenberg_id
    book.cover_url = catalog_book["cover_url"]
    book.title = catalog_book["title"] or book.title
    book.author = catalog_book["author"] or book.author
    book.save()

    return book