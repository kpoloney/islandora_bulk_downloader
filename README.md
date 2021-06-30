# Islandora Bulk Downloader

## Overview

A utility script to download objects from an Islandora 7.x repository. Its input is a CSV file listing PIDs for all the objects you want to download in a column with the header "PID"; this file may contain other columns too, but they are ignored. The script fetches the RELS-EXT datastream of every object named in the input file and determines its parent, collection membership, etc. and writes the OBJ datastream to a directory named after the parent object. A file's sequence within its parent is indicated in the OBJ filename.

## Requirements

Python 3. That's it.

## Usage

The script takes four parameters, all required:

* `--pid_file`: Relative or absolute path to the file listing all PIDs to harvest.
* `--log`: Relative or absolute path to the log file.
* `--host`: The Islandora repository's hostname, including the "https://". Trailing / is optional.
* `--output_dir`: Relative or absolute path to the directory to put the harvested content in. Created if does not exist.

For example:

`python3 islandora_bulk_downloader --pid_file=pids.csv --log=mylog.txt --host=https://digital.lib.sfu.ca --output_dir=/tmp/output`

