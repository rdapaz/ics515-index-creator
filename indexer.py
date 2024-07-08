from pathlib import Path
import fitz  # PyMuPDF
import os
import time
import sqlite3
import re
from textwrap import dedent
from io import StringIO
from icecream import ic


def extract_text_from_pdf(pdf_path):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)
    output_file_path = os.path.splitext(pdf_path)[0] + '.txt'
    s = ''
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        s += page.get_text()
    with open(os.path.join(Path.cwd() / 'pdfs', output_file_path), 'w') as fout:
        fout.write(s)
    return s


def split_text_into_chunks(text: str) -> list:
    rex_text = r"""
    © SANS Institute \d{4}
    [0-9a-z]+
    [a-zA-Z@_]+
    [0-9]+
    [A-Za-z ]+
    [a-zA-Z0-9]+
    live
    Licensed To: .*
    Licensed To: .*
    """
    rex_text = dedent(rex_text).strip()
    rex = re.compile(pattern=rex_text)
    ret_val: list = rex.split(text)
    return ret_val


def consume_chunks(chunks: list, db_conn: sqlite3.Connection, book_number: int) -> None:
    c = db_conn.cursor()
    sql = "INSERT INTO ics515 (title, book_no, page_no, blurb) VALUES (?, ?, ?, ?)"
    for chunk in chunks:
        ic(chunk)
        page_no = None
        offset = 0
        header_found = False
        out = StringIO()
        unit_code_pattern = re.compile(r'ICS\d+')
        unit_code_found = unit_code_pattern.search(chunk)
        if unit_code_found:
            last_line = ''
            for line in chunk.splitlines():
                if re.search(r'ICS\d+', line):
                    header_found = True
                if header_found:
                    offset += 1
                    if offset == 3:
                        title = line
                        if re.search(r'^\d+$', title):
                            title = last_line
                        rex = re.compile(r'{}(.*)^(\d\d?\d?)$(.*)\2'.format(title), re.MULTILINE | re.DOTALL)
                        my_match = rex.search(chunk)
                        if my_match:
                            if my_match.group(2):
                                page_no = int(my_match.group(2))
                            blurb = f"{my_match.group(1)}\n{my_match.group(3)}"
                            for blurb_line in blurb.splitlines():
                                if '© 2021 Robert M. Lee' not in blurb_line and not re.search(r'^$', blurb_line):
                                    print(blurb_line, file=out)
                        blurb = out.getvalue()
                        c.execute(sql, (title, book_number, page_no, blurb))
                        db_conn.commit()
                last_line = line

        else:
            for line in chunk.splitlines():
                if not re.match(r"^\d\d?\d?$", line):
                    if '© 2021 Robert M. Lee' not in line and not re.search(r'^$', line):
                        print(line, file=out)
                else:
                    page_no = int(line)
            blurb = out.getvalue()
            if page_no is not None:
                get_last_id_sql = """
                SELECT title FROM ICS515 WHERE ID = (SELECT MAX(ID) FROM ICS515)
                """
                title = c.execute(get_last_id_sql).fetchone()[0]
                c.execute(sql, (title, book_number, page_no, blurb))
                db_conn.commit()


def init_db(db_conn):
    sql = """
    DROP TABLE IF EXISTS ics515
    """
    sql = dedent(sql).strip()
    db_conn.execute(sql)
    db_conn.commit()

    sql = """
    CREATE TABLE IF NOT EXISTS ics515 (
    id INTEGER PRIMARY KEY,
    title TEXT,
    book_no INTEGER,
    page_no INTEGER,
    blurb TEXT,
    my_notes TEXT,
    summary TEXT
    )
    """
    sql = dedent(sql).strip()
    db_conn.execute(sql)
    db_conn.commit()


if __name__ == "__main__":
    start_time = time.time()
    conn = sqlite3.connect(os.path.join(Path.cwd() / 'ics515.sqlite3'))
    init_db(conn)
    root_dir = os.path.join(Path.cwd() / 'pdfs')
    regex = re.compile(r'.*_book([1-5])\.pdf')
    for subdir, dirs, files in os.walk(root_dir):
        for file in files:
            match = regex.search(file)
            if match:
                pdf_file = os.path.join(subdir, file)
                print(f'[+] Processing {pdf_file}...')
                book_no = int(match.group(1))
                text_to_parse = extract_text_from_pdf(pdf_file)
                arr = split_text_into_chunks(text_to_parse)
                consume_chunks(arr, conn, book_no)
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"[+] Completed in {execution_time:.3f} seconds")
