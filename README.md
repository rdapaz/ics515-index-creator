# ics515-index-creator
Hacky tools to automatically create a SANS index based off the course pdf files.

## How to use
1) Create a DB in sqlite3 with the content of the course
2) Run the indexer.py
3) Create the index file

This relies heavily on the scripts in ancailliau/sans-indexes:main.

You will need to install Latex locally
You will also need to copy the generated index folder into the other repo and create a folder appropriately named
