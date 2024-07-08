from pathlib import Path
from jinja2 import FileSystemLoader, Environment, Template
from icecream import ic
import sqlite3
import os
import re
import subprocess

conn = sqlite3.connect(os.path.join(Path.cwd() / 'ics515.sqlite3'))
c = conn.cursor()
sql = """
SELECT title, book_no, page_no, my_notes
FROM INDEX_ICS515
"""


def trim_and_strip_whitespace(s):
    rex = re.compile(pattern=r'(^\s+|\s+$)')
    return re.sub(rex, '', s)


def escape_ampersand(s):
    rex = re.compile(pattern=r'^(A|The)\s')
    s = re.sub(rex, '', s)
    return s.replace('&', r'\&').replace('|', r'\|')


arr = []
last_book_no = ''
PRINT_SHORT = False

for db_row in c.execute(sql).fetchall():
    title, book_no, page_no, my_notes = db_row
    if (my_notes and len(my_notes) > 0) and not PRINT_SHORT:
        for note in my_notes.splitlines():
            arr.append([title, book_no, page_no, last_book_no, note])
    else:
        arr.append([title, book_no, page_no, last_book_no, None])
    last_book_no = book_no
ic(arr)

sql = """
SELECT title, book_no, page_no, keywords
FROM INDEX_ICS515
WHERE keywords IS NOT NULL OR length(keywords) > 1
"""

categories = []

for db_row in c.execute(sql).fetchall():
    title, book_no, page_no, keywords = db_row
    for keyword in keywords.split(','):
        categories.append([title, book_no, page_no, trim_and_strip_whitespace(keyword)])

categories = sorted(categories, key=lambda x: x[3])


ordered_categories = []
counter = 0
suffix_idx = 64
suffix = 'A'
last_keyword = ''
last_suffix = ''
for title, book_no, page_no, keyword in categories:
    if last_keyword != keyword:
        counter += 1
        if counter > 10:
            counter = 1
            suffix_idx += 1
            suffix = chr(suffix_idx + counter)
    ordered_categories.append([title, book_no, page_no, keyword, f'{counter}{suffix}'])
    last_keyword = keyword
    last_suffix = suffix

# ic(ordered_categories)


template_text = """
\comment{********************************************************************************************
                                       CATEGORIES SECTION
*****************************************************************************************************
 Sort entries consist of a number to be inserted in the standard 'Numbers' section
 Number composition : [(1) Alphabet order number] [(2) 0]
   (1) Sorting in alphabetical number
   (2) Allows up to 10 subsections / alphabet character }

% note that where Malware is we will have a unique keyword
% from the keywords, we need to enumerate because
% the number in front of the A needs to increment for each entry

%\indexentry{1A@\\textbf{Malware}!BlackEnergy|book{1}}{87}

\BLOCK{ for title, book_no, page_no, keyword, sort_idx in categories }
\indexentry{\VAR{sort_idx}@\\textbf{\VAR{keyword | trim_and_strip_whitespace}}!\VAR{title | escape_ampersand}|book{\VAR{book_no}}}{\VAR{page_no}}   
\BLOCK{ endfor }

\BLOCK{- for title, book_no, page_no, last_book_no, note in master_index }
\BLOCK{ if book_no != last_book_no }


\comment{***********************************************************
                    Book No: \VAR{book_no} Section
********************************************************************}
\BLOCK{ endif }   
\indexentry{\VAR{title | escape_ampersand }|book{\VAR{book_no}}}{\VAR{page_no}}
\BLOCK{ if note  }
\indexentry{\VAR{title | escape_ampersand }!\VAR{note}|book{\VAR{book_no}}}{\VAR{page_no}}
\BLOCK{ endif }
\BLOCK{- endfor }                 
"""

env = Environment(
    block_start_string='\BLOCK{',
    block_end_string='}',
    variable_start_string='\VAR{',
    variable_end_string='}',
    comment_start_string='\#{',
    comment_end_string='}',
    line_statement_prefix='%%',
    line_comment_prefix='%#',
    trim_blocks=True,
    autoescape=False,
)

env.filters['escape_ampersand'] = escape_ampersand
env.filters['trim_and_strip_whitespace'] = trim_and_strip_whitespace

template = env.from_string(template_text)
with open(r'/home/ricdeez/projects/sans-indexes/src-515/main.idx', 'w') as fout:
    fout.write(template.render(
                            master_index=arr,
                            categories=ordered_categories
    ))

# print(template.render(
#                         master_index=arr,
#                         categories=ordered_categories
#                      ))
