#! /usr/bin/env python3

import argparse
import base64
import io
import math
import os
import re
import time
import urllib.request
from PIL import Image
from lxml import html
from ebooklib import epub
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tqdm

# ==============================================================================


def read_auth_file(auth_file):
    """
    Read a file and extract Base64 encoded username and password.

    Args:
        auth_file (file): File descriptor to a file

    Returns:
        Tuple of (username, password)
    """
    username = None
    password = None
    for line in auth_file:
        line = line.strip()
        if not line:
            continue

        key, value = line.split(':')
        if key.strip().lower() == 'username':
            username = base64.b64decode(value.strip())
        elif key.strip().lower() == 'password':
            password = base64.b64decode(value.strip())

    if username is None:
        raise RuntimeError('Unable to find username in credential file')
    if password is None:
        raise RuntimeError('Unable to find password in credential file')
    return username.decode('utf8'), password.decode('utf8')


def initialize_driver():
    """
    Initialize a selenium.webdriver using a headless Chrome

    Note:
        Requires the chromedriver program to be installed
    """
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    chromedriver = webdriver.Chrome(options=options)
    chromedriver.implicitly_wait(10)
    chromedriver.maximize_window()
    return chromedriver


def login_to_webbnovels(driver, username, password):
    """
    Use the driver to login into webnovel.com using an email address

    Args:
        driver (selenium.webdriver): driver used to get web data
        username (str): Username (email address)
        password (str): Password
    """
    driver.get('https://passport.webnovel.com/emaillogin.html?appid=900' +
               '&areaid=1&returnurl=https%3A%2F%2Fwww.webnovel.com%2F' +
               'loginSuccess&auto=1&autotime=0&source=&ver=2&fromuid=0' +
               '&target=iframe&option=')
    email_field = driver.find_element_by_name('email')
    email_field.send_keys(username)
    password_field = driver.find_element_by_name('password')
    password_field.send_keys(password)
    submit = driver.find_element_by_id('submit')
    submit.click()

    current_url = driver.current_url
    WebDriverWait(driver, 10).until(EC.url_changes(current_url))

    # print new URL
    body = driver.find_element_by_xpath("/html/body")
    if body.text:
        # Take care of the security code
        code = driver.find_element_by_class_name('_int')
        # driver.save_screenshot('./screenshot01.png')
        verification_code = input("Enter verification code: ")
        code.send_keys(str(verification_code))
        submit = driver.find_element_by_id('checkTrust')
        submit.click()
        # os.remove('./screenshot01.png')


def get_novel_list(driver, category_website, novel_title_filter):
    """
    Retrieve the list of novels from the given category on webnovel.com

    Args:
        driver (selenium.webdriver): driver used to get web data
        category_website (str): URL to a novel category on webnovel.com

    Returns:
        Tuple of (URL, title) for the selected novel
    """

    driver.get(category_website)
    book_list = driver.find_element_by_class_name(
        'j_bookList').find_element_by_tag_name('ul')
    book_items = book_list.find_elements_by_tag_name('li')
    result = [{
        'link':
        book.find_element_by_tag_name('a').get_attribute("href"),
        'title':
        book.find_element_by_tag_name('a').get_attribute("title")
    } for book in book_items]

    result = [
        book for book in result
        if novel_title_filter.lower() in book['title'].lower()
    ]

    if len(result) == 1:
        return (result[0]['link'], result[0]['title'])

    for idx, book in enumerate(result):
        print('{:02}. {}'.format(idx + 1, book['title']))

    select = -1
    while select < 1 or select > len(result):
        select = int(input("Which novel do you want to read?: "))
    return (result[select - 1]['link'], result[select - 1]['title'])


def cleanup_chapter_title(chapter_title):
    """
    Cleanup the title of a chapter

    Args:
        chapter_title (str): Title of a chapter

    Returns:
        Cleaned up chapter title
    """
    chapter_title = re.sub(
        r'[0-9]+\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|' +
        r'Oct|Nov|Dec)\s+[0-9]+', '', chapter_title)
    chapter_title = re.sub(
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|' +
        r'Dec)\s+[0-9]+,\s*[0-9]+', '', chapter_title)
    chapter_title = re.sub(r'[0-9]+\s+(?:hours|day|days)\s+ago', '',
                           chapter_title)
    return chapter_title


def get_novel_data(driver, novel_website, chapter_num_start, chapter_num_end):
    """
    Retrieve data for a given novel on webnovel.com

    Data includes:
        - author
        - translator
        - editor
        - synopsis
        - list of chapters

    Args:
        driver (selenium.webdriver): driver used to get web data
        novel_website (str): URL to a novel on webnovel.com
        chapter_num_start (int): starting chapter number
        chapter_num_end (int): ending chapter number

    Returns:
        Tuple of (synopsis, author, translator, editor, chapter_list) for the
        selected novel

        chapter_list is a list containing dictionaries for each chapter
        with two keys: 'link' (URL) and 'title' (title of chapter as a string)
    """
    driver.get(novel_website)
    img = driver.find_element_by_xpath('//i[@class="g_thumb"]/img[2]')

    cover_name = None
    cover_data = None
    try:
        request = urllib.request.urlopen(img.get_attribute('src'))
        if request.code == 200:
            cover_data = request.read()
            _, ext = os.path.splitext(img.get_attribute('src').split('?')[0])
            cover_name = 'cover{}'.format(ext)
    except URLError:
        pass
    
    synopsis_anchor = driver.find_element_by_id('about')
    synopsis = synopsis_anchor.find_element_by_tag_name('p').text

    author = None
    translator = None
    editor = None
    element_list = driver.find_elements_by_xpath('//address/p/*')
    element_list.reverse()
    while element_list:
        element = element_list.pop()
        if element.text.lower().startswith('author'):
            author = element_list.pop().text
        if element.text.lower().startswith('translator'):
            translator = element_list.pop().text
        if element.text.lower().startswith('editor'):
            editor = element_list.pop().text

    popup = driver.find_element_by_class_name('j_show_contents')
    popup.click()
    time.sleep(0.5)

    chapter_list_raw = driver.find_elements_by_xpath(
        '//div[@class="volume-item"]/ol/li/a')
    if chapter_num_start:
        if chapter_num_end is None:
            chapter_list_raw = chapter_list_raw[chapter_num_start - 1:]
        else:
            chapter_list_raw = chapter_list_raw[chapter_num_start -
                                                1:chapter_num_end]
    elif chapter_nunm_end:
        chapter_list_raw = chapter_list_raw[:chapter_num_end]

    chapter_list = []
    for element in tqdm.tqdm(
            chapter_list_raw, desc='Extracting chapter data', unit='chapter'):
        chapter_list.append({
            'link': element.get_attribute('href'),
            'title': cleanup_chapter_title(element.text)
        })

    return synopsis, (cover_name, cover_data), author, translator, editor, \
        chapter_list


def get_chapter_text(driver, url):
    """
    Retrieve the text of a chapter located on webnovel.com

    Args:
        driver (selenium.webdriver): driver used to get web data
        url (str): URL to a chapter on webnovel.com

    Returns:
        Text of chapter as a string
    """
    driver.get(url)
    anchor = driver.find_element_by_class_name('cha-words')
    text = ''
    for element in anchor.find_elements_by_tag_name('p'):
        text += '<p>{}</p>'.format(element.text)
    return text


def chunks(alist, chunk_size):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(alist), chunk_size):
        yield alist[i:i + chunk_size]


def generate_epub(epub_file, novel_title, cover, author, editor, translator,
                  synopsis, chapter_data_list):
    """
    Generate an EPUB file.

    Args:
        epub_file (str): Path to the EPUB file to generate
        novel_title (str): Title of the novel
        author (str): Name of the author of the novel
        editor (str): Name of the editor of the novel
        translator (str): Name of the translator
        synopsis (str): Synopsis of the novel
        chapter_data_list (list): list of tuples with chapter data:
                                    - title (str): chapter title
                                    - num (int): chapter number
                                    - content (str): chapter content
    """
    book = epub.EpubBook()

    # add metadata
    book.set_identifier(re.sub(r'\s', '_', novel_title))
    book.set_title(novel_title)
    book.set_language('en')
    book.add_author(author)

    if synopsis:
        book.add_metadata('DC', 'description', synopsis, {})

    # add cover image
    cover_name, cover_data = cover
    if cover_data is not None:
        # The titlepage will serve as cover
        book.set_cover(cover_name, cover_data, create_page=False)

    # create chapter items and add them to the book
    chapter_num_start = chapter_data_list[0][1]
    chapter_list = []
    utf8_parser = html.HTMLParser(encoding='utf-8')
    for title, num, content in chapter_data_list:
        title_clean = title.strip().replace('\n', ' ')
        m = re.match(r'^{}\s+(.*)'.format(num), title_clean)
        if m:
            title_clean = m.group(1)
        
        regen_html = False
        html_tree = html.document_fromstring(content, parser=utf8_parser)
        html_root = html_tree.getroottree()
        title_tag = html_root.find('body').getchildren()[0]
        if title_tag.tag not in ['h1', 'h2', 'h3', 'h4']:
            content = '<h1>{}</h1>'.format(title_clean) + content
        elif title_tag.tag in ['h1', 'h2', 'h3', 'h4']:
            title_tag.tag = 'h1'
            title_tag.text = title_clean
            regen_html = True
            

        for p in html_root.xpath('/html/body/p[position()<4]'):
            if p.text and re.match(r'^[Cc]hapter\s+{}\s+-\s+{}'.format(num, title_clean), p.text):
                p.getparent().remove(p)
                regen_html = True
                break
        if regen_html:
            content = html.tostring(html_tree, pretty_print=True)            

        chapter = epub.EpubHtml(
            title=title_clean,
            file_name=os.path.join('chapters', '{:04}.xhtml'.format(num)),
            content=content,
            lang='hr')
        chapter_list.append(chapter)
        book.add_item(chapter)

    titlepage_content = '''<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
        <title>Cover</title>
        <style type="text/css" title="override_css">
            @page {{padding: 0pt; margin:0pt}}
            body {{ text-align: center; padding:0pt; margin: 0pt; }}
        </style>
    </head>
    <body>
        <div>
            <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" width="100%" height="100%" viewBox="0 0 {0} {1}" preserveAspectRatio="none">
                <image width="{0}" height="{1}" xlink:href="{2}"/>
            </svg>
        </div>
    </body>
</html>
'''
    cover_width, cover_height = Image.open(io.BytesIO(cover_data)).size
    titlepage = epub.EpubLiteralXHtml(title='Cover Image',
                                      uid='titlepage',
                                      file_name='titlepage.xhtml',
                                      content=titlepage_content.format(
                                          cover_width,
                                          cover_height,
                                          cover_name).encode('utf-8'))
    book.add_item(titlepage)

    # create sections for every 100 chapters
    volume_incr = 100
    section_chapter_list = chunks(chapter_list, volume_incr)
    volume_start = int(
        math.floor(int(chapter_num_start) /
                   (volume_incr * 1.0))) * int(volume_incr) + 1
    volume_end = volume_start + volume_incr - 1
    section_list = []
    for section_chapters in section_chapter_list:
        try:
            section_list.append(
                (epub.Section('Chapters {} - {}'.format(volume_start, volume_end),
                              start=volume_start,
                              end=volume_end), (section_chapters)))
        except TypeError:
            section_list.append(
                (epub.Section('Chapters {} - {}'.format(volume_start, volume_end)),
                 (section_chapters)))
        volume_start += volume_incr
        volume_end += volume_incr

    # create table of contents
    # - add manual link
    # - add section
    # - add auto created links to chapters

    book.toc = tuple(section_list)

    # add navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # define css style
    style = '''
@namespace epub "http://www.idpf.org/2007/ops";
body {
    font-family: Cambria, Liberation Serif, Bitstream Vera Serif,
Georgia, Times, Times New Roman, serif;
}
h2 {
     text-align: left;
     text-transform: uppercase;
     font-weight: 200;
}
ol {
        list-style-type: none;
}
ol > li:first-child {
        margin-top: 0.3em;
}
nav[epub|type~='toc'] > ol > li > ol  {
    list-style-type:square;
}
nav[epub|type~='toc'] > ol > li > ol > li {
        margin-top: 0.3em;
}
'''
    # add css file
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style)
    book.add_item(nav_css)

    # create spin, add cover page as first page
    book.spine = [titlepage, 'nav', *chapter_list]
    book.guide = [{'href': 'titlepage.xhtml',
                   'title': 'Cover',
                   'type': 'cover'},
                  {'href': 'nav.xhtml',
                   'title': 'Table of Contents',
                   'type': 'toc'},
                  {'href': chapter_list[0].file_name,
                   'title': 'Start of Content',
                   'type': 'bodymatter'}]

    # create epub file
    epub.write_epub(epub_file, book, {'epub2_guide': False})


# ==============================================================================


def _main():
    parser = argparse.ArgumentParser(
        description='Download novels from webnovel.com and export them in ' +
        'EPUB format',
        epilog='By specifying either `--with-chapter-start` or ' +
        '`--with-chapter-end`, the script will not prompt you to choose ' +
        'starting and ending chapter numbers.')
    parser.add_argument(
        '-o',
        '--output',
        metavar='FILE',
        default=[],
        help='Output EPUB file. If empty, automatically ' +
        'generate a filename based on the novel\'s title and selection of ' +
        'chapters (default: [])')
    parser.add_argument(
        '--with-chapter-start',
        type=int,
        metavar='N',
        help='Starting chapter number.')
    parser.add_argument(
        '--with-chapter-end',
        type=int,
        metavar='N',
        help='Ending chapter number. ' +
        'If negative, the latest available chapter will be selected')
    parser.add_argument(
        '--with-title',
        type=str,
        metavar='STR',
        default='',
        help='Title of novel to download. ' +
        'Can be a partial match (ie. avatar for "The King\'s avatar") ')
    parser.add_argument(
        '--with-category',
        choices=[
            'competitive-sports',
            'eastern-fantasy',
            'fan-fiction',
            'fantasy',
            'historical-fiction',
            'horror-thriller',
            'magical-realism',
            'martial-arts',
            'realistic-fiction',
            'romance-fiction',
            'science-fiction',
            'video-games',
            'war-military',
        ],
        metavar='',
        help='Specify a particular category of novels to consider.' +
        'If not specified, the user will be prompted to choose a ' +
        'category. Allowed values are: competitive-sports, ' +
        'eastern-fantasy, fan-fiction, fantasy, historical-fiction, ' +
        'horror-thriller, magical-realism, martial-arts, ' +
        'realistic-fiction, romance-fiction, science-fiction, ' +
        'video-games, war-military')

    group = parser.add_argument_group(title='Authentication')
    group.add_argument(
        '-c',
        '--with-credentials',
        type=argparse.FileType(),
        metavar='FILE',
        help='File containing the username and password encoded with Base64. '
        + 'This file must contain two key-value pairs separated by a colon: ' +
        '`username` and `password`. The values need to be Base64 encoded.')
    group.add_argument(
        '-u',
        '--with-username',
        type=str,
        help='Username for logging into webnovel.com')
    group.add_argument(
        '-p',
        '--with-password',
        type=str,
        help='Password for logging into webnovel.com')

    username = None
    password = None
    args = parser.parse_args()
    if args.with_credentials or args.with_username or args.with_password:
        if args.with_credentials:
            if args.with_username or args.with_password:
                parser.error(
                    'Cannot specify --with-username or --with-password with ' +
                    '--with-credentials')
            else:
                username, password = read_auth_file(args.with_credentials)
        else:
            if not args.with_username or not args.with_password:
                parser.error('Must specify either --with-credentials or both '
                             + '--with-username and --with-password')
            else:
                username = args.with_username
                password = args.with_password

    driver = initialize_driver()

    if username is not None and password is not None:
        print('Logging into webnovels.com... ', end='', flush=True)
        login_to_webbnovels(driver, username, password)
        print('DONE')

    base_url = 'https://www.webnovel.com/category/list?category='
    novel_categories = {
        'competitive-sports': base_url + 'Competitive%20Sports',
        'eastern-fantasy': base_url + 'Eastern%20Fantasy',
        'fan-fiction': base_url + 'Fan-fiction%20',
        'fantasy': base_url + 'Fantasy',
        'historical-fiction': base_url + 'Historical%20Fiction',
        'horror-thriller': base_url + 'Horror%20%26%20Thriller',
        'magical-realism': base_url + 'Magical%20Realism',
        'martial-arts': base_url + 'Martial%20Arts',
        'realistic-fiction': base_url + 'Realistic%20Fiction',
        'romance-fiction': base_url + 'Romance%20Fiction',
        'science-fiction': base_url + 'Science%20Fiction',
        'video-games': base_url + 'Video%20Games',
        'war-military': base_url + 'War%20%26%20Military%20Fiction'
    }
    if not args.with_category:
        print('Select Category:')
        print('')
        print('01. Competitive Sports')
        print('02. Eastern Fantasy')
        print('03. Fan-fiction')
        print('04. Fantasy')
        print('05. Historical Fiction')
        print('06. Horror & Thriller')
        print('07. Magical Realism')
        print('08. Martial Arts')
        print('09. Realistic Fiction')
        print('10. Romance Fiction')
        print('11. Science Fiction')
        print('12. Video Games')
        print('13. War & Military')

        base_url = 'https://www.webnovel.com/category/list?category='
        category_website = None
        while category_website is None:
            x = int(input('Select a category (Enter Number): '))
            if x == 1:
                category_website = novel_categories['competitive-sports']
            elif x == 2:
                category_website = novel_categories['eastern-fantasy']
            elif x == 3:
                category_website = novel_categories['fan-fiction']
            elif x == 4:
                category_website = novel_categories['fantasy']
            elif x == 5:
                category_website = novel_categories['historical-fiction']
            elif x == 6:
                category_website = novel_categories['horror-thriller']
            elif x == 7:
                category_website = novel_categories['magical-realism']
            elif x == 8:
                category_website = novel_categories['martial-arts']
            elif x == 9:
                category_website = novel_categories['realistic-fiction']
            elif x == 10:
                category_website = novel_categories['romance-fiction']
            elif x == 11:
                category_website = novel_categories['science-fiction']
            elif x == 12:
                category_website = novel_categories['video-games']
            elif x == 13:
                category_website = novel_categories['war-military']
    else:
        category_website = novel_categories[args.with_category]

    print("Getting novel list...", flush=True)
    novel_website, novel_title = get_novel_list(driver, category_website,
                                                args.with_title)
    print('  -> selected {}'.format(novel_title))

    print("Getting chapter names, links, cover and metadata...", flush=True)

    chapter_num_start = None
    chapter_num_end = None
    if args.with_chapter_end:
        chapter_num_end = args.with_chapter_end

    if args.with_chapter_start:
        chapter_num_start = args.with_chapter_start
    else:
        chapter_num_start = 1

    synopsis, cover, author, translator, editor, chapter_list_raw = \
        get_novel_data(driver, novel_website, chapter_num_start, chapter_num_end)

    if not args.with_chapter_start and not args.with_chapter_end:
        print("There are currently " + str(len(chapter_list_raw)) +
              " available")
        chapter_num_start = int(input("What's the starting chapter number?: "))
        chapter_num_end = int(input("What's the ending chapter number?: "))

    if chapter_num_end is None or chapter_num_end < 0:
        chapter_num_end = chapter_num_start + len(chapter_list_raw) - 1

    chapter_num_list = list(range(chapter_num_start, chapter_num_end + 1))
    if len(chapter_num_list) > len(chapter_list_raw):
        # In this case, we did not filter the chapter list in get_novel_data(),
        # so we need to do it here
        chapter_list_raw = chapter_list_raw[:chapter_num_end-chapter_num_start]
    assert len(chapter_num_list) == len(chapter_list_raw)

    chapter_data_list = []
    for idx, chapter in enumerate(
            tqdm.tqdm(
                chapter_list_raw,
                desc='Downloading chapter content',
                unit='chapter')):
        chapter_data_list.append((chapter['title'], chapter_num_list[idx],
                                  get_chapter_text(driver, chapter['link'])))

    epub_filename = '{}_{}-{}.epub'.format(novel_title, chapter_num_start,
                                           chapter_num_end)
    if args.output:
        epub_filename = args.output

    generate_epub(epub_filename, novel_title, cover, author, editor,
                  translator, synopsis, chapter_data_list)


# ==============================================================================

if __name__ == '__main__':
    _main()
