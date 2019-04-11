from enum import Enum
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ------------------------------------------------------------------------------


class WebDriverType(Enum):
    firefox = 1
    chrome = 2


# ------------------------------------------------------------------------------


def chrome_default_user_data():
    """
    Get the default path to the user data directory for Google Chrome.

    Returns:
        Path to user's data directory
    """
    if sys.platform.startswith('linux'):
        # linux
        root_dir = '~/.config/google-chrome/'
    elif sys.platform == 'darwin':
        # OS X
        root_dir = '~/Library/Application Support/Google/Chrome/'

    elif sys.platform == 'win32':
        root_dir = os.path.join(os.path.expandvars(r'%LOCALAPPDATA%'),
                                'Google', 'Chrome', 'User Data')

    root_dir = os.path.expanduser(root_dir)
    if os.path.isdir(root_dir):
        return root_dir
    else:
        return None


def firefox_default_profile():
    """
    Get the default path to the user's Firefox profile.

    Returns:
        Path to user's default profile if only a single profile can be found,
        otherwise returns None.
    """
    if sys.platform.startswith('linux'):
        # linux
        root_dir_list = ['~/.mozilla/firefox/']
    elif sys.platform == 'darwin':
        # OS X
        root_dir_list = [
            '~/Library/Application Support/Firefox/Profiles',
            '~/Library/Mozilla/Firefox/Profiles'
        ]
    elif sys.platform == 'win32':
        root_dir_list = [
            os.path.join(os.path.expandvars(r'%APPDATA%'), 'Mozilla',
                         'Firefox', 'Profiles')
        ]

    profile_dir_list = []
    for directory in root_dir_list:
        directory = os.path.expanduser(directory)
        if os.path.isdir(directory):
            for d in next(os.walk(directory))[1]:
                profile_dir_list.append(os.path.join(directory, d))

    if len(profile_dir_list) == 1:
        return profile_dir_list[0]
    else:
        return None


# ==============================================================================


def wait_until_url_changes(driver, timeout=10):
    """
    Makes the driver wait for a URL change with a given timeout

    Args:
        driver (selenium.webdriver): driver used to get web data
        timeout (int): number of seconds to use as timeout
    """
    current_url = driver.current_url
    WebDriverWait(driver, timeout).until(EC.url_changes(current_url))


def wait_until_id_appears(driver, element_id, timeout=10):
    """
    Makes the driver wait for an HTML tag with a particular id appears

    Args:
        driver (selenium.webdriver): driver used to get web data
        element_id (str): HTML id to look for
        timeout (int): number of seconds to use as timeout
    """
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.ID, element_id)))


def wait_until_class_appears(driver, element_class, timeout=10):
    """
    Makes the driver wait for an HTML tag with a particular class appears

    Args:
        driver (selenium.webdriver): driver used to get web data
        element_class (str): HTML class to look for
        timeout (int): number of seconds to use as timeout
    """
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CLASS_NAME, element_class)))


class text_to_change(object):
    def __init__(self, locator, text):
        self._locator = locator
        self._text = text

    def __call__(self, driver):
        text = EC._find_element(driver, self._locator).text
        return text != self._text


def wait_until_class_text_changes(driver,
                                  element_class,
                                  text_before,
                                  timeout=10):
    """
    Makes the driver wait until an HTML tag with a particular class has a 
    change in its text content

    Args:
        driver (selenium.webdriver): driver used to get web data
        element_class (str): HTML class to look for
        timeout (int): number of seconds to use as timeout
    """
    WebDriverWait(driver, 10).until(
        text_to_change((By.CLASS_NAME, element_class), text_before))


def wait_until_name_appears(driver, element_name, timeout=10):
    """
    Makes the driver wait for an HTML tag with a particular name appears

    Args:
        driver (selenium.webdriver): driver used to get web data
        element_name (str): HTML tag to look for
        timeout (int): number of seconds to use as timeout
    """

    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.NAME, element_name)))


def _initialize_chrome_driver(headless, user_data_path):
    """
    Initialize a Chrome driver

    Args:
        headless (bool): whether to run headless or not
        user_data_path (str): path to folder containing user data

    Returns:
        A selenium.webdriver object with a Chrome instance
    """
    options = webdriver.ChromeOptions()
    if headless:
        options.headless = True
    if user_data_path is not None:
        options.add_argument('--user-data-dir={}'.format(user_data_path))
    chrome_driver = webdriver.Chrome(options=options)
    return chrome_driver


def _initialize_firefox_driver(headless, user_data_path):
    """
    Initialize a Firefox driver

    Args:
        headless (bool): whether to run headless or not
        user_data_path (str): path to folder containing user data
                              (ie. Firefox profile directory)

    Returns:
        A selenium.webdriver object with a Firefox instance
    """
    options = webdriver.FirefoxOptions()
    if headless:
        options.headless = True
    if user_data_path is not None:
        profile = webdriver.FirefoxProfile(user_data_path)
    firefox_driver = webdriver.Firefox(firefox_profile=profile,
                                       options=options)
    firefox_driver.implicitly_wait(10)
    firefox_driver.maximize_window()
    profile = None
    return firefox_driver


def _webdriver_post_setup(driver):
    """
    Configure some driver after initialisation

    Args:
        driver (selenium.webdriver): driver used to get web data

    Returns:
        The same driver received as input
    """
    driver.implicitly_wait(10)
    driver.maximize_window()
    return driver


def initialize_driver(driver_type, headless=True, user_data_path=None):
    """
    Initialize a selenium.webdriver using a headless Chrome

    Note:
        Requires the chromedriver program to be installed
    """

    if not isinstance(driver_type, WebDriverType):
        raise RuntimeError('driver_type must be an enum of WebDriverType!')
    elif driver_type == WebDriverType.chrome:
        driver = _initialize_chrome_driver(headless, user_data_path)
    elif driver_type == WebDriverType.firefox:
        driver = _initialize_firefox_driver(headless, user_data_path)
    else:
        raise RuntimeError(
            'Unsupported value for driver_type: {}'.format(driver_type))
    return _webdriver_post_setup(driver)


# ==============================================================================


def _login_to_webbnovels(driver, username, password):
    """
    Use the driver to login into webnovel.com using an email address

    Args:
        driver (selenium.webdriver): driver used to get web data
        username (str): Username (email address)
        password (str): Password
    """
    driver.get('https://www.webnovel.com')
    login = driver.find_element_by_class_name('j_login')
    login.click()
    wait_until_id_appears(driver, 'loginIfr', timeout=10)

    driver.switch_to.frame('frameLG')
    with_email = driver.find_element_by_class_name('_e')
    with_email.click()
    wait_until_name_appears(driver, 'email')

    email_field = driver.find_element_by_name('email')
    email_field.send_keys(username)
    password_field = driver.find_element_by_name('password')
    password_field.send_keys(password)
    submit = driver.find_element_by_id('submit')
    submit.click()
    wait_until_class_appears(driver, 'j_user_name')

    # TODO: is this still required ?
    # body = driver.find_element_by_xpath("/html/body")
    # if body.text:
    #     # Take care of the security code
    #     code = driver.find_element_by_class_name('_int')
    #     # driver.save_screenshot('./screenshot01.png')
    #     verification_code = input("Enter verification code: ")
    #     code.send_keys(str(verification_code))
    #     submit = driver.find_element_by_id('checkTrust')
    #     submit.click()
    #     # os.remove('./screenshot01.png')


def _login_to_webbnovels_with_cookies(driver, cookie_file):
    """
    Use the driver to login into webnovel.com using an email address

    Args:
        driver (selenium.webdriver): driver used to get web data
        cookie_file (str): Path to a pickle file with cookie data
    """
    import pickle
    driver.get('https://www.webnovel.com')
    cookies = pickle.load(cookie_file)
    for cookie in cookies:
        driver.add_cookie(cookie)
    driver.get('https://www.webnovel.com')
    if not driver.find_elements_by_class_name('j_user_name'):
        raise RuntimeError(
            'Not logged into webnovel.com after adding cookies!')


def login_to_webbnovels(driver, **kwargs):
    """
    Login into webnovel.com using either cookies or username and password

    Args:
        driver (selenium.webdriver): driver used to get web data
        **kwargs: can be either `cookies` or `username` and `password`
    """
    if 'cookies' in kwargs:
        _login_to_webbnovels_with_cookies(driver, kwargs['cookies'])
    elif 'username' in kwargs and 'password' in kwargs:
        _login_to_webbnovels(driver, kwargs['username'], kwargs['password'])
    else:
        driver.quit()
        raise RuntimeError(
            'Unable to do anything with these arguments: {}'.format(kwargs))


# ==============================================================================


def buy_chapter_with_ss(driver, container_class, content_class):
    container = driver.find_element_by_class_name(container_class)
    text_before = container.find_element_by_class_name(content_class).text

    body = container.find_element_by_class_name('lock-body')
    number_ss = int(body.text)

    buy_button = container.find_element_by_class_name('j_unlockChapter')
    buy_button.click()
    wait_until_class_text_changes(driver, 'cha-content', text_before)

    if container.find_element_by_class_name('cha-content').text == text_before:
        raise RuntimeError('Failed to buy chapter!')

    return number_ss
