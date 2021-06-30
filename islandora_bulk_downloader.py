#!/usr/bin/env python3
import sys
import os
import csv
import re
import logging
import argparse
import urllib.request
import requests
from PIL import Image
from PyPDF2 import PdfFileMerger
# from shutil import rmtree

# Functions
def pid_to_path(pid):
    # Converts PID into a string suitable for use in filesystem paths.
    # Uses __ in case some PIDs contain a single _.
    return pid.replace(':', '__')

def get_rels_ext_properties(pid):
    rels_ext_properties = dict()
    url = args.host.rstrip('/') + '/islandora/object/' + pid + '/datastream/RELS-EXT/view'
    request_url = urllib.request.urlopen(url)
    rels_ext_xml = request_url.read().decode('utf-8').strip()
    rels_ext_properties['PID'] = pid

    # <fedora:isMemberOfCollection rdf:resource="info:fedora/km:collection"/>
    isMemberOfCollections = re.findall('fedora:isMemberOfCollection rdf:resource="info:fedora/.*"', rels_ext_xml)
    if len(isMemberOfCollections) > 0:
        isMemberOfCollection = isMemberOfCollections[0].replace('fedora:isMemberOfCollection rdf:resource="info:fedora/', '')
        isMemberOfCollection = isMemberOfCollection.strip('"')
        rels_ext_properties['isMemberOfCollection'] = isMemberOfCollection
    else:
        rels_ext_properties['isMemberOfCollection'] = None

    # Newspaper issues use isMemberOf in relationship to their newspaper and isSequenceNumber to sequence within that newspaper.
    # <fedora:isMemberOf rdf:resource="info:fedora/ctimes:1"/>
    # <islandora:isSequenceNumber>16219</islandora:isSequenceNumber>
    isMemberOfs = re.findall('fedora:isMemberOf rdf:resource="info:fedora/.*"', rels_ext_xml)
    if len(isMemberOfs) > 0:
        isMemberOf = isMemberOfs[0].replace('fedora:isMemberOf rdf:resource="info:fedora/', '')
        isMemberOf = isMemberOf.strip('"')
        rels_ext_properties['isMemberOf'] = isMemberOf
    else:
        rels_ext_properties['isMemberOf'] = None

    # Objects of cmodel islandora:newspaperPageCModel and islandora:pageCModel use this property.
    isSequenceNumbers = re.findall('<islandora:isSequenceNumber>.*<', rels_ext_xml)
    if len(isSequenceNumbers) > 0:
        # Assumes that the object has only one parent.
        isSequenceNumber = isSequenceNumbers[0].replace('<.*', '')
        isSequenceNumbers = re.findall('>.*<', isSequenceNumber)
        isSequenceNumber = isSequenceNumbers[0].lstrip('>')
        isSequenceNumber = isSequenceNumber.rstrip('<')
        rels_ext_properties['isSequenceNumber'] = isSequenceNumber
    else:
        rels_ext_properties['isSequenceNumber'] = None

    # isPageOf is used in pages of books and newspaper issues. <islandora:isPageOf rdf:resource="info:fedora/aldine:12541"/>
    isPageOfs = re.findall('fedora:isPageOf rdf:resource="info:fedora/.*"', rels_ext_xml)
    if len(isPageOfs) > 0:
        isPageOf = isPageOfs[0].replace('fedora:isPageOf rdf:resource="info:fedora/', '')
        isPageOf = isPageOf.strip('"')
        rels_ext_properties['isPageOf'] = isPageOf
    else:
        rels_ext_properties['isPageOf'] = None

    # isConstituentOf is used in children of compound objects.
    isConstituentOfs = re.findall('fedora:isConstituentOf rdf:resource="info:fedora/.*"', rels_ext_xml)
    if len(isConstituentOfs) > 0:
        # Assumes that the object has only one parent.
        isConstituentOf = isConstituentOfs[0].replace('fedora:isConstituentOf rdf:resource="info:fedora/', '')
        isConstituentOf = isConstituentOf.strip('"')
        rels_ext_properties['isConstituentOf'] = isConstituentOf
    else:
        rels_ext_properties['isConstituentOf'] = None

    # isSequenceNumberOf{PID} is used in paged content (of books, newspapers), and in children of compound objects.
    # <islandora:isSequenceNumberOfkm_8352>5</islandora:isSequenceNumberOfkm_8352>
    isSequenceNumberOfs = re.findall('<islandora:isSequenceNumberOf.*>.*<', rels_ext_xml)
    if len(isSequenceNumberOfs) > 0:
        # Assumes that the object has only one parent.
        isSequenceNumberOf = isSequenceNumberOfs[0].replace('<.*', '')
        isSequenceNumberOfs = re.findall('>.*<', isSequenceNumberOf)
        isSequenceNumberOf = isSequenceNumberOfs[0].lstrip('>')
        isSequenceNumberOf = isSequenceNumberOf.rstrip('<')
        rels_ext_properties['isSequenceNumberOf'] = isSequenceNumberOf
    else:
        rels_ext_properties['isSequenceNumberOf'] = None

    # Standard models:
    # islandora:collectionCModel
    # islandora:pageCModel
    # islandora:sp_pdf
    # islandora:sp-audioCModel
    # islandora:sp_disk_image
    # islandora:sp_videoCModel
    # islandora:sp_basic_image
    # islandora:sp_web_archive
    # islandora:sp_large_image_cmodel
    # ir:citationCModel
    # ir:thesisCModel

    # islandora:bookCModel
    # islandora:newspaperCModel
    # islandora:newspaperPageCModel
    # islandora:newspaperIssueCModel
    # islandora:compoundCModel

    # Note: it is possible for objects of these content models to have multiple content models.
    # islandora:entityCModel
    # islandora:eventCModel
    # islandora:placeCModel
    # islandora:personCModel
    # islandora:organizationCModel

    models = re.findall('fedora-model:hasModel rdf:resource="info:fedora/.*"', rels_ext_xml)
    # Assumes a single model.
    model = models[0].replace('fedora-model:hasModel rdf:resource="info:fedora/', '')
    model = model.strip('"')
    rels_ext_properties['model'] = model

    return rels_ext_properties


# Main program logic.

parser = argparse.ArgumentParser()
parser.add_argument('--pid_file', required=True, help='Relative or absolute path to the file listing all PIDs to harvest.')
parser.add_argument('--log', required=True, help='Relative or absolute path to the log file.')
parser.add_argument('--host', required=True, help='Islandora hostname, including the "https://". Trailing / is optional.')
parser.add_argument('--output_dir', required=True, help='Relative or absolute path to the directory to put the harvested content in. Created if does not exist.')
args = parser.parse_args()

logging.basicConfig(
    filename=args.log,
    level=logging.INFO,
    filemode='a+',
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S')

if not os.path.exists(args.pid_file):
    message = "CSV file " + args.pid_file + " does not exist."
    logging.error(message)
    sys.exit("ERROR: " + message)

if os.path.exists(args.output_dir):
    logging.info("Output directory " + args.output_dir + " exists.")
else:
    os.mkdir(args.output_dir)
    logging.info("Creating output directory " + args.output_dir + ".")

with open(args.pid_file, 'r', newline='') as csv_reader_file_handle:
    csv_reader = csv.DictReader(csv_reader_file_handle)
    for row in csv_reader:
        properties = get_rels_ext_properties(row['PID'])
        if properties['model'] == 'islandora:compoundCModel': continue
        obj_url = args.host + '/islandora/object/' + row['PID'] + '/datastream/OBJ/download'
        obj = requests.get(obj_url)
        content_disp = obj.headers['content-disposition']
        m = re.search(r'filename="(.*)"', content_disp)
        fname = m.group(1)
        ext = os.path.splitext(fname)[1]
        if not bool(properties['isConstituentOf']):
            content_path = os.path.join(args.output_dir, (pid_to_path(row['PID'])+ext))
        elif not os.path.exists(os.path.join(args.output_dir, pid_to_path(properties['isConstituentOf']))):
            os.mkdir(os.path.join(args.output_dir, pid_to_path(properties['isConstituentOf'])))
            content_path = os.path.join(args.output_dir, pid_to_path(properties['isConstituentOf']), (properties['isSequenceNumberOf']+"_"+pid_to_path(row['PID']))+ext)
        else:
            content_path = os.path.join(args.output_dir, pid_to_path(properties['isConstituentOf']), (properties['isSequenceNumberOf'] + "_" + pid_to_path(row['PID'])) + ext)
        with open(content_path, 'wb') as file:
            file.write(obj.content)

# loop through folders in output directory (for folders in dir)
for root, dirs, files in os.walk(args.output_dir):
    for dir in dirs:
        if dir.startswith('km'):
            dir_files = os.listdir(os.path.join(root, dir))
            if len(dir_files)>1: #if there's more than one component in folder, sort & save as one pdf
                dir_files.sort(key=lambda x: int(x.split("_")[0]))
                pdfs = []
                merger = PdfFileMerger()
                for img in dir_files:
                    if img.endswith('.jp2') or img.endswith('.tiff'):
                        im = Image.open(os.path.join(root, dir, img))
                        filename = os.path.splitext(img)[0]
                        new_fn = filename + '.pdf'
                        im.save(os.path.join(root, dir, new_fn))
                        im.close()
                        pdfs.append(new_fn)
                        os.remove(os.path.join(root,dir,img))
                for pdf in pdfs:
                    fpath = os.path.join(root, dir, pdf)
                    merger.append(fpath)
                merger.write(os.path.join(root, (dir+'.pdf')))
                merger.close()
            elif len(dir_files)==1:
                item = dir_files[0]
                if item.endswith('.jp2') or item.endswith('.tiff'):
                    im = Image.open(os.path.join(root, dir, item))
                    filename = os.path.splitext(item)[0]
                    new_fn = filename + '.pdf'
                    im.save(os.path.join(root,dir, new_fn))
                    im.close()
                    os.remove(os.path.join(root,dir,item))

# clean up to remove subdirs - assumes all images captured in pdfs
# dir = os.listdir(args.output_dir)
# for item in dir:
#     path = os.path.join(args.output_dir, item)
#     if not os.path.isfile(path):
#         rmtree(path)