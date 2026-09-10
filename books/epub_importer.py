import re
from pathlib import Path
from uuid import uuid4

from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from ebooklib import ITEM_DOCUMENT, ITEM_IMAGE, epub

from .models import Book, Chapter


def clean_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def detect_title(html_content, fallback):
    soup = BeautifulSoup(html_content, "html.parser")
    heading = soup.find(["h1", "h2", "h3"])

    if heading:
        title = heading.get_text(" ", strip=True)
        if title:
            return title

    return fallback


def save_epub_cover(book, epub_book):
    image_items = list(epub_book.get_items_of_type(ITEM_IMAGE))

    if not image_items:
        return

    cover_item = next(
        (
            item
            for item in image_items
            if "cover" in item.get_name().lower()
            or "cover" in str(item.get_id()).lower()
        ),
        image_items[0],
    )

    suffix = Path(cover_item.get_name()).suffix.lower() or ".jpg"
    filename = f"{uuid4().hex}{suffix}"

    book.cover_image.save(
        filename,
        ContentFile(cover_item.get_content()),
        save=True,
    )


def import_epub(owner, uploaded_file):
    epub_book = epub.read_epub(uploaded_file)

    title_metadata = epub_book.get_metadata("DC", "title")
    author_metadata = epub_book.get_metadata("DC", "creator")

    title = (
        title_metadata[0][0]
        if title_metadata
        else uploaded_file.name.rsplit(".", 1)[0]
    )
    author = author_metadata[0][0] if author_metadata else ""

    book = Book.objects.create(
        owner=owner,
        title=title,
        author=author,
        status="reading",
    )

    save_epub_cover(book, epub_book)

    chapters = []
    chapter_number = 1

    for item in epub_book.get_items_of_type(ITEM_DOCUMENT):
        content = clean_text(item.get_content())

        # Ignores tiny service files such as navigation documents.
        if len(content) < 80:
            continue

        title = detect_title(
            item.get_content(),
            f"Chapter {chapter_number}",
        )

        chapters.append(
            Chapter(
                book=book,
                number=chapter_number,
                title=title,
                content=content,
            )
        )

        chapter_number += 1

    Chapter.objects.bulk_create(chapters)

    return book