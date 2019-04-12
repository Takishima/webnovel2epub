#! /usr/bin/env python3

import argparse
import re
import ebooklib
from ebooklib import epub
from webnovel2epub import generate_epub

#==============================================================================


def extract_book_metadata(book):
    """
    Extract metadata from an EPUB book.

    Args:
        book (ebooklib.epub.EpubBook): an EPUB book

    Returns:
        A dictionary with the metadata
    """

    cover_name = None
    cover_data = None
    if book.get_item_with_href('cover.jpg'):
        cover_name = 'cover.jpg'
        cover_data = book.get_item_with_href('cover.jpg').get_content()
    elif book.get_item_with_href('cover.png'):
        cover_name = 'cover.png'
        cover_data = book.get_item_with_href('cover.png').get_content()

    return {
        'title': book.get_metadata('DC', 'title')[0][0],
        'creator': book.get_metadata('DC', 'creator')[0][0],
        'language': book.get_metadata('DC', 'language')[0][0],
        'description': book.get_metadata('DC', 'description')[0][0],
        'cover': (cover_name, cover_data),
    }


def extract_book_chapters(book):
    """
    Extract chapter data from an EPUB book.

    Args:
        book (ebooklib.epub.EpubBook): an EPUB book

    Returns:
        A list of tuples (title, number, content) with chapter data
    """
    toc = book.toc
    toc.reverse()

    num_pattern = re.compile(r'([0-9]+)\.xhtml$')

    if isinstance(toc[-1], ebooklib.epub.Link):
        # Assuming that the first item from the TOC is the title so ignoring it
        toc.pop()
    chapter_list = []
    while toc:
        if isinstance(toc[-1], ebooklib.epub.Link):
            number = num_pattern.search(toc[-1].href)
            chapter_list.append((
                toc[-1].title,
                int(number.group(1)),
                book.get_item_with_href(
                    toc[-1].href).get_body_content().decode('utf8'),
            ))
        elif isinstance(toc[-1], tuple):
            for link in toc[-1][1]:
                number = num_pattern.search(link.href)
                chapter_list.append((
                    link.title,
                    int(number.group(1)),
                    book.get_item_with_href(
                        link.href).get_body_content().decode('utf8'),
                ))
        toc.pop()
    return chapter_list


# ==============================================================================


def _main():
    parser = argparse.ArgumentParser(
        description='Merge two existing EPUB files into one',
        epilog='The main purpose of this script is to allow easy merging of ' +
        'two EPUB files that were generated using webnovel2epub.py. ' +
        'Typically, if you downloaded chapters 1-1000 and then 1001-1102 ' +
        'you can merge both books into a single EPUB files while retaining ' +
        'all the metadata and chapter data.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('epub1', type=str, help='First EPUB file')
    parser.add_argument('epub2', type=str, help='Second EPUB file')
    parser.add_argument('output',
                        type=str,
                        help='Output EPUB file. Can be identical to ' +
                        'either epub1 or epub2')
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force merge (even if metadata consistency check fails)')

    args = parser.parse_args()

    book1 = epub.read_epub(args.epub1)
    book2 = epub.read_epub(args.epub2)

    book1_data = extract_book_metadata(book1)
    book2_data = extract_book_metadata(book2)

    # This might be too restrictive...
    if not args.force and book1_data != book2_data:
        cover_str = '__cover_match__'
        if book1_data['cover'] != book2_data['cover']:
            cover_str = '__cover_*mis*match__'
        book1_data['cover'] = cover_str
        book2_data['cover'] = cover_str
        raise RuntimeError(
            'Unable to combine epub1 and epub2: metadata are ' +
            'not identical!\n{}\nvs.\n{}'.format(book1_data, book2_data))

    book1_chapters = extract_book_chapters(book1)
    book2_chapters = extract_book_chapters(book2)

    book1_chapter_start = book1_chapters[0][1]
    book1_chapter_end = book1_chapters[-1][1]
    book2_chapter_start = book2_chapters[0][1]
    book2_chapter_end = book2_chapters[-1][1]

    if book2_chapter_end < book1_chapter_end:
        raise RuntimeError(
            ('epub2\'s final chapter {} is lower than ' +
             'epub1\'s final chapter {}').format(book2_chapter_end,
                                                 book1_chapter_end))

    print('Found chapters {} to {} in first EPUB'.format(
        book1_chapter_start, book1_chapter_end))
    print('Found chapters {} to {} in second EPUB'.format(
        book2_chapter_start, book2_chapter_end))
    if book2_chapter_start <= book1_chapter_end:
        print('  -> will discard chapters {} to {} from second EPUB'.format(
            book2_chapter_start, book1_chapter_end))
        diff = book1_chapter_end - book2_chapter_start + 1
        book2_chapter_start = book1_chapter_end + 1
        book2_chapters = book2_chapters[diff:]
        assert book1_chapters[-1][1] + 1 == book2_chapters[0][1]

    if book1_chapter_end + 1 != book2_chapter_start:
        raise RuntimeError(
            ('Both input EPUB files are not contibuous!\n' +
             '  EPUB1: chapters {} - {}\n  EPUB2: chapters ' +
             '{} - {}').format(book1_chapter_start, book1_chapter_end,
                               book2_chapter_start, book2_chapter_end))

    output_chapters = book1_chapters
    for chapter in book2_chapters:
        output_chapters.append(chapter)

    generate_epub(args.output, book1_data['title'], book1_data['cover'],
                  book1_data['creator'], None, None, book1_data['description'],
                  output_chapters)


# ==============================================================================

if __name__ == '__main__':
    _main()
