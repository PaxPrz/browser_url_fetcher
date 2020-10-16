import psutil
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, create_engine
from sqlalchemy.engine.result import RowProxy
from sqlalchemy.sql.expression import literal_column, label
from typing import List, TypeVar, Tuple, Dict, Union, Set
from pathlib import Path
import shutil
import os
import re
from datetime import datetime
from contextlib import suppress
import time
from dotenv import load_dotenv
import logging

load_dotenv(dotenv_path="geturls.env")

Ps = TypeVar('Process', bound=psutil.Process)

FIREFOX = ("firefox",)
CHROMIUM = ("chrome", "opera", "brave", "edge")

log = logging.getLogger('__name__')

class CannotFindDatabase(Exception):
    def __str__(self):
        return "Database file cannot be found!!"

class CannotFindProcess(Exception):
    def __init__(self, browser):
        self.browser = browser

    def __str__(self):
        return f"Cannot find the {self.browser} process!!"

def get_process(browser: str)-> List[Ps]:
    '''
        Returns browser processes
    '''
    ps_list = []
    for p in psutil.process_iter():
        if browser.lower() in p.name().lower():
            ps_list.append(p)
    return ps_list

def get_parent_process(ps_list: List[Ps], browser: str)-> Set[Ps]:
    '''
        Returns only parent processes of all active browser processses
    '''
    parent_set = set()
    for ps in ps_list:
        backup = ps
        with suppress(TypeError):
            while True:
                ps = ps.parent()
                if ps is None or browser.lower() not in ps.name().lower():
                    parent_set.add(backup)
                    break
                backup = ps
    return parent_set

def get_database_path(ps_set: Set[Ps], browser: str)-> Set[Path]:
    '''
        Returns set of sqlite database paths
    '''
    regex = None
    db_paths = set()
    if browser.lower() in CHROMIUM:
        regex = r'^.+(\\|\/)History$'
    elif browser.lower() in FIREFOX:
        regex = r'^.+(\\|\/)places.sqlite$'
    for ps in ps_set:
        search_children = True
        try:
            open_files = map(lambda x:x.path, ps.open_files())
            for file_loc in open_files:
                if re.match(regex, file_loc):
                    db_paths.add(Path(file_loc))
                    search_children = False
            # search in child processes of parent process
            if search_children:
                children = ps.children()
                for c in children:
                    if browser.lower() in c.name().lower():
                        for file_loc in map(lambda x:x.path, c.open_files()):
                            if re.match(regex, file_loc):
                                db_paths.add(Path(file_loc))
        except psutil.AccessDenied:
            log.error(f"User don't have permission for {browser} browser")
            continue
    return db_paths

def duplicate_file(file_loc: Path, browser: str, dont_cp: bool=False)-> Path:
    '''
        Copies the sqlite database and returns the copied folder
    '''
    database_dir = os.getenv("DATABASE_COPY_DIR", default="database")
    if not os.path.isdir(database_dir):
        os.mkdir(database_dir)
    dest_loc = Path(os.path.join(database_dir, f'{browser}.sqlite'))
    if dont_cp:
        return dest_loc
    shutil.copy(file_loc, dest_loc)
    return dest_loc

def read_urls(browser: str, file_loc: Path, result_limit: int=5, fetch_time: datetime=None)-> List[RowProxy]:
    '''
        Reads the urls from sqlite db and formats timestamp for both firefox and chromium
    '''
    CHROMIUM_OFFSET = 11_644_473_600_000_000
    browser = browser.lower()
    engine = create_engine('sqlite:///'+os.path.join(file_loc))
    metadata = MetaData(bind=engine)
    if browser in FIREFOX:
        table_name = 'moz_places'
        last_visit = 'last_visit_date'
    elif browser in CHROMIUM:
        table_name = 'urls'
        last_visit = 'last_visit_time'
    url_table = Table(table_name, metadata,
        Column('id', Integer, primary_key=True),
        Column('url', String),
        Column('title', String),
        Column(last_visit, Integer)
    )
    query = None
    if browser in FIREFOX:
        query = sa.select(
            [*url_table.c, literal_column('last_visit_date').label('timestamp')]
        )
    elif browser in CHROMIUM:
        query = sa.select(
            [*url_table.c, label('timestamp', url_table.c.last_visit_time - CHROMIUM_OFFSET)]
        )
    if fetch_time:
        timestamp = int(time.mktime(fetch_time.timetuple()) * 1_000_000)
        if browser in CHROMIUM:
            timestamp += CHROMIUM_OFFSET
        query = query.where(url_table.c[last_visit] > timestamp)
    else:
        query = query.order_by(
            url_table.c[last_visit].desc()
        ).limit(result_limit)
    return query.execute().fetchall()

def show_data(data: List[RowProxy], column_limit: int=25)-> None:
    '''
        Uses PrettyTable to print the title, urls and timestamp in format
    '''
    from prettytable import PrettyTable
    table = PrettyTable(['ID', 'Title', 'URL', 'Last Visited'])
    for row in data:
        with suppress(ValueError):
            table.add_row([
                row.id,
                '' if not row.title else row.title[:column_limit],
                '' if not row.url else row.url[:column_limit],
                'NA' if (time := int(((row.timestamp or 0))/1_000_000)) < 0 else datetime.fromtimestamp(time).strftime('%m/%d %H:%M %p')
            ])
    print(table)

def fetch_urls(browser: str, count: int=5, from_time: datetime=None):
    '''
        Covers overall function. Fetches url and return dictionary with keys = profile_name.
        Note: Use timestamp key for converting to date: datetime.fromtimestamp(timestamp/1_000_000)

        Args:
            browser (str): The browser to fetch url (Use a piece from process name)
            count (int): Returns last n history. Disabled when from_time is defined
            from_time (datetime): Return history from defined timestamp

        Returns:
            Dict[str, List[RowProxy]]: maps profile_name with corresponding urls; incase of multiple profile browser like chrome

    '''
    ps_list = get_process(browser)
    if len(ps_list) == 0:
        raise CannotFindProcess(browser)
    parent_ps_set = get_parent_process(ps_list, browser)
    db_paths = get_database_path(parent_ps_set, browser)
    if len(db_paths) == 0:
        raise CannotFindDatabase
    result_dict = {}
    for db_path in db_paths:
        dup_path = duplicate_file(db_path, browser, dont_cp=False)
        urls = read_urls(browser, dup_path, count, from_time)
        result_dict.update({db_path.parent.name: urls})
    return result_dict

if __name__=="__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Get running browser history from sqlite database")
    parser.add_argument('-b', '--browser', type=str, choices=['firefox','chrome','opera','brave','edge'], required=True)
    parser.add_argument('-c', '--count', type=int, default=5, help="Doesn't work with --fromtime")
    parser.add_argument('-d', '--dont-copy', action="store_true")
    parser.add_argument('-l', '--rowlength', type=int, default=25)
    parser.add_argument('-t', '--fromtime', type=str, default=None, help="YYYY-MM-DDTHH:MM:SS")
    args = parser.parse_args()

    def just_print(db_path, browser):
        dup_path = duplicate_file(db_path, browser, bool(args.dont_copy))
        urls = read_urls(browser, dup_path, args.count, datetime.fromisoformat(args.fromtime) if args.fromtime else None)
        if db_path:
            print(f"Profile: {db_path.parent.name}")
        show_data(urls, column_limit=args.rowlength)

    browser = args.browser
    db_path = None
    if not args.dont_copy:
        ps_list = get_process(browser)
        if len(ps_list) == 0:
            log.warn(f"Cannot get {browser} Process! The browser must be active.")
            sys.exit(404)
        parent_ps_set = get_parent_process(ps_list, browser)
        db_paths = get_database_path(parent_ps_set, browser)
        if len(db_paths) == 0:
            log.warn(f"Cannot find database file")
            sys.exit(500)
        for db_path in db_paths:
            just_print(db_path, browser)
    else:
        just_print(db_path, browser)

