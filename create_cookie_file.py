#! /usr/bin/env python3

import pickle
from _webdrivers import WebDriverType, wait_until_id_appears, \
    wait_until_name_appears, wait_until_class_appears, \
    initialize_driver


def _main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Generate a Pickle file containing cookie data for ' +
        'logging into webnovel.com')
    parser.add_argument(
        'output',
        type=argparse.FileType('wb'),
        metavar='FILE',
        help='File name to store the cookie data')

    args = parser.parse_args()

    driver = initialize_driver(WebDriverType.chrome, headless=False)
    driver.get('https://www.webnovel.com')
    login = driver.find_element_by_class_name('j_login')
    login.click()
    wait_until_id_appears(driver, 'loginIfr', timeout=10)

    driver.switch_to.frame('frameLG')
    with_email = driver.find_element_by_class_name('_e')
    with_email.click()
    wait_until_name_appears(driver, 'email')

    print('Please login into webnovel.com within the browser window that ' +
          'just opened')

    wait_until_class_appears(driver, 'j_user_name', timeout=3600)
    pickle.dump(driver.get_cookies(), args.output)
    driver.quit()
    print('Job done, exitting now...')


if __name__ == '__main__':
    _main()
