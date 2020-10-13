import unittest
import psutil
from geturls import (CannotFindDatabase, CannotFindProcess, get_process, get_parent_process, get_database_path, duplicate_file, read_urls, show_data, fetch_urls)
from random import randint
from datetime import datetime, timedelta

BROWSER_LIST = (
    'firefox',
    'chrome',
    'opera',
    'brave',
    'edge',
)

class GetUrlsTest(unittest.TestCase):
    def test_unavailable_browser(self):
        unavailable_browser = "never_developed_browser"
        try:
            data = fetch_urls(unavailable_browser)
        except CannotFindProcess:
            self.assertTrue(1==1)
        else:
            self.assertTrue(1==2, "Cannot fetch data from unavailable browser")
    
    def test_closed_browser(self):
        all_ps = ' '.join(map(lambda x:x.name().lower(), psutil.process_iter()))
        for browser in BROWSER_LIST:
            if browser not in all_ps:
                try:
                    data = fetch_urls(browser)
                except CannotFindProcess:
                    self.assertTrue(1==1)
                else:
                    self.assertTrue(1==2, "Cannot fetch data from closed browser")
                finally:
                    return
        print("Require any browser to be closed")

    def test_open_browser(self):
        all_ps = ' '.join(map(lambda x:x.name().lower(), psutil.process_iter()))
        for browser in BROWSER_LIST:
            if browser in all_ps:
                try:
                    ps_list = get_process(browser)
                    parent_ps_set = get_parent_process(ps_list, browser)
                    db_paths = get_database_path(parent_ps_set, browser)
                    if len(db_paths) == 0:
                        continue
                    db_path = db_paths.pop()
                    if not os.access(db_path, os.R_OK):
                        continue
                    dup_path = duplicate_file(db_path, browser, dont_cp=False)
                    urls = read_urls(browser, dup_path)
                    self.assertIsInstance(urls, list)
                    return
                except Exception as e:
                    print(e)
                    self.assertTrue(1==2, "Cannot read from open browser with permission")
                    return
        print("Require any browser to be open")

    def test_firefox_browser(self):
        all_ps = ' '.join(map(lambda x:x.name().lower(), psutil.process_iter()))
        for browser in FIREFOX:
            if browser in all_ps:
                try:
                    ps_list = get_process(browser)
                    parent_ps_set = get_parent_process(ps_list, browser)
                    db_paths = get_database_path(parent_ps_set, browser)
                    if len(db_paths) == 0:
                        continue
                    db_path = db_paths.pop()
                    if not os.access(db_path, os.R_OK):
                        continue
                    dup_path = duplicate_file(db_path, browser, dont_cp=False)
                    urls = read_urls(browser, dup_path)
                    self.assertIsInstance(urls, list)
                    return
                except Exception as e:
                    print(e)
                    self.assertTrue(1==2, "Cannot read from firefox browser")
                    return
        print(f"Require any {FIREFOX} to be open")

    def test_chromium_browser(self):
        TEST_RAN = False
        all_ps = ' '.join(map(lambda x:x.name().lower(), psutil.process_iter()))
        for browser in CHROMIUM:
            if browser in all_ps:
                try:
                    TEST_RAN = True
                    ps_list = get_process(browser)
                    parent_ps_set = get_parent_process(ps_list, browser)
                    db_paths = get_database_path(parent_ps_set, browser)
                    if len(db_paths) == 0:
                        continue
                    db_path = db_paths.pop()
                    if not os.access(db_path, os.R_OK):
                        continue
                    dup_path = duplicate_file(db_path, browser, dont_cp=False)
                    urls = read_urls(browser, dup_path)
                    self.assertIsInstance(urls, list)
                except Exception as e:
                    print(e)
                    self.assertTrue(1==2, "Cannot read from chromium browser")
                    return
        if not TEST_RAN:
            print(f"Require any {CHROMIUM} to be open")

    def test_active_browsers_fromtime(self):
        for browser in BROWSER_LIST:
            try:
                hr, min = randint(0,2), randint(1,59)
                fetch_time = datetime.now()-timedelta(hours=hr, minutes=min)
                data = fetch_urls(browser, from_time=fetch_time)
                for k, value in data.items():
                    if any(map(lambda x: datetime.fromtimestamp(x['timestamp']/1_000_000) < fetch_time, value)):
                        self.assertTrue(1==2, "Fetched data before fetch_time")
                    else:
                        self.assertTrue(1==1)
            except (CannotFindProcess, CannotFindDatabase):
                continue

if __name__=="__main__":
    unittest.main()