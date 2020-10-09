import psutil
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, create_engine
from sqlalchemy.engine.result import RowProxy
from sqlalchemy.sql.expression import literal_column, label
from typing import List, TypeVar, Tuple, Dict, Union
from pathlib import Path
import shutil
import os
import re
from datetime import datetime
from prettytable import PrettyTable
from contextlib import suppress
import argparse
import sys

Ps = TypeVar('Process', bound=psutil.Process)

class CannotFindDatabase(Exception):
    def __str__(self):
        print("Database file cannot be found!!")

def get_process(browser: str)-> List[Ps]:
    ps_list = []
    for p in psutil.process_iter():
        if browser.lower() in p.name().lower():
            ps_list.append(p)
    return ps_list

def get_parent_process(ps: Ps, browser: str)-> Ps:
    backup = ps
    while True:
        ps = ps.parent()
        if browser.lower() not in ps.name().lower():
            return backup
        backup = ps

def get_database_path(ps: Ps, browser: str)-> Path:
    regex = None
    if browser.lower() in ("chrome",):
        regex = r'^\S+History$'
    elif browser.lower() in ("firefox",):
        regex = r'^\S+places.sqlite$'
    open_files = map(lambda x:x.path, ps.open_files())
    for file_loc in open_files:
        if re.match(regex, file_loc):
            return Path(file_loc)
    raise CannotFindDatabase

def duplicate_file(file_loc: Path, browser: str, dont_cp: bool=False)-> Path:
    if not os.path.isdir('database'):
        os.mkdir('database')
    dest_loc = Path('./database/firefox.sqlite') if browser.lower() in ('firefox') else Path('./database/chrome.sqlite')
    if dont_cp:
        return dest_loc
    shutil.copy(file_loc, dest_loc)
    return dest_loc

def read_urls_firefox(file_loc: Path, result_limit: int=5)-> List[RowProxy]: # List[Dict[str, Union[str, int, datetime]]]:
    engine = create_engine('sqlite:///'+file_loc.as_posix())
    metadata = MetaData(bind=engine)
    url_table = Table('moz_places', metadata,
        Column('id', Integer, primary_key=True),
        Column('url', String),
        Column('title', String),
        Column('last_visit_date', Integer)
    )
    query = sa.select(
            [*url_table.c, literal_column('last_visit_date').label('timestamp')]
        ).order_by(
            url_table.c.last_visit_date.desc()
        ).limit(
            result_limit
        )
    return query.execute().fetchall()

def read_urls_chrome(file_loc: Path, result_limit: int=5)-> List[RowProxy]:
    engine = create_engine('sqlite:///'+os.path.join(file_loc))
    metadata = MetaData(bind=engine)
    url_table = Table('urls', metadata,
        Column('id', Integer, primary_key=True),
        Column('url', String),
        Column('title', String),
        Column('last_visit_time', Integer)
    )
    query = sa.select(
            [*url_table.c, label('timestamp', url_table.c.last_visit_time - 11644473600)]
        ).order_by(
            url_table.c.last_visit_time.desc()
        ).limit(
            result_limit
        )
    return query.execute().fetchall()

def show_data(data: List[RowProxy], column_limit: int=25)-> None:
    table = PrettyTable(['ID', 'Title', 'URL', 'Last Visited'])
    for row in data:
        with suppress(ValueError):
            table.add_row([
                row.id,
                '' if not row.title else row.title[:column_limit],
                '' if not row.url else row.url[:column_limit],
                'NA' if (time := int(((row.timestamp or 0)-116_444_736_00)/1_000_000)) < 0 else datetime.fromtimestamp(time).strftime('%m/%d %H:%M %p')
            ])
    print(table)

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Get running browser history from sqlite database")
    parser.add_argument('-b', '--browser', type=str, choices=['firefox','chrome'], required=True)
    parser.add_argument('-c', '--count', type=int, default=5)
    parser.add_argument('-d', '--dont-copy', action="store_true")
    parser.add_argument('-l', '--rowlength', type=int, default=25)
    args = parser.parse_args()

    browser = args.browser
    db_path = None
    if not args.dont_copy:
        ps_list = get_process(browser)
        if len(ps_list) == 0:
            print(f"Cannot get {browser} Process! The browser must be active.")
            sys.exit(404)
        parent_ps = get_parent_process(ps_list[0], browser)
        db_path = get_database_path(parent_ps, browser)
    dup_path = duplicate_file(db_path, browser, bool(args.dont_copy))
    urls = None
    if browser == "firefox":
        urls = read_urls_firefox(dup_path, args.count)
    elif browser == "chrome":
        urls = read_urls_chrome(dup_path, args.count)
    show_data(urls, column_limit=args.rowlength)

