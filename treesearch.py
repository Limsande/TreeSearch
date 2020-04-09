#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TreeSearch - a synonym-aware location search tool for tree species.
# Copyright (C) 2020  Luis Imsande
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""
TreeSearch - a synonym-aware location search tool for tree species.

Queries publicly available online data bases to implement a synonym-aware location lookup. Currently,
Plants of the World online <plantsoftheworldonline.org> is used for synonym lookup and GlobalTreeSearch
<https://www.bgci.org/global_tree_search.php> provides location data.

Usage:
    tree_search.py GENUS SPECIES AUTHOR [--output=FILE]
    tree_search.py --input=FILE [--output=FILE]
    tree_search.py [-h|-v]

Options:
    -h, --help  Print this help text and exit.
    -i, --input=FILE  Input file to read tuples of (genus, species, author) from (as CSV). Must contain columns "Name"
        and "Author", additional columns are ignored and preserved in the output.
    -o, --output=FILE  Output file to write results to (as CSV).
    -v, --version  Print version info and exit.

Author:
    Written by Luis Imsande (limsande(at)yahoo dot com).

Report bugs:
    Please report any bugs at <https://github.com/Limsande/TreeSearch/issues>.

Copyright:
    Copyright (C) 2020, Luis Imsande. License GPLv2+: GNU GPL version 2 or later
    <https://www.gnu.org/licenses/old-licenses/gpl-2.0>.
"""

__author__ = 'Luis Imsande'
__email__ = 'limsande(at)yahoo dot com'
__date__ = 'January 2020'
__copyright__ = '(C) 2020, Luis Imsande'
__license__ = 'GPLv2'
__version__ = '0.1'

import csv
import os
import random
import sys
import time

import numpy as np
import pandas as pd
import pykew.ipni as ipni
import pykew.powo as powo
import requests
from docopt import docopt
from pykew.ipni_terms import Name
from requests.exceptions import RequestException

TOTAL_NAMES_PROCESSED = 0
TOTAL_LOCATION_QUERIES_SUCCEEDED = 0


def get_locations(name: str, author: str) -> set:
    """
    Fetches synonyms and locations for (name, author).
    """

    # Only names with two parts (genus, species) supported.
    name_parts = name.split(' ')
    if len(name_parts) > 1:
        genus, species = name_parts[:2]
    else:
        print("ERROR: Invalid name: {}. Skipping.".format(name), file=sys.stderr)
        return set()

    # Get the unique IPNI ID for this tuple of (genus, species, author).
    ipni_id = get_ipni_id(genus, species, author)

    # With this ID, we can look up a synonym list.
    synonyms = get_synonyms(ipni_id)
    synonyms.append(name)

    # Query GTS for locations of each synonym.
    locations = []
    for syn in synonyms:
        locations.extend(get_locations_from_gts(syn))

    return set(locations)


def get_ipni_id(genus: str, species: str, author: str) -> str:
    """
    Looks up the IPNI ID (International Plant Name Index) from ipni.org for (genus, species, author) via their API.
    With this, we can later get all synonyms. If anything fails, an empty string is returned.

    :return: the IPNI ID, if found; an empty sting otherwise
    """
    print('Querying beta.ipni.org for record with genus: {}, species: {}, and author: {}...'.format(genus, species, author))
    res = ''
    try:
        search_res = ipni.search({Name.genus: genus, Name.species: species, Name.author: author, Name.in_powo: 'True'})
    except RequestException as e:
        print('ERROR: Query failed: {}. Going directly to GTS.'.format(e), file=sys.stderr)
    else:
        print('Retrieved {} hit(s).'.format(search_res.size()))
        if search_res.size() is 1:
            res = [r['fqId'] for r in search_res][0]
            print('Result has IPNI ID: {}'.format(res))
        elif search_res.size() is 0:
            print('Going directly to GTS.')
        else:
            print('ERROR: Retrieved unambiguous results. Expected 1, got {}. Going directly to GTS.'.format(search_res.size()), file=sys.stderr)

    return res


def get_synonyms(ipni_id: str) -> list:
    """
    Fetches all synonyms for this IPNI ID from plantsoftheworldonline.org via their API. If the query returns, that this
    ID itself is a synonym, the corresponding accepted name is used instead for another query, which result is then
    returned. If the input is an empty string, this function returns immediately with an empty list. If anything fails,
    also an empty list is returned.

    :return: a list of synonyms, if found any; an empty list otherwise
    """
    res = []
    if ipni_id is not '':
        print('Querying plantsoftheworldonline.org for synonyms of "{}"...'.format(ipni_id))
        try:
            lookup_res = powo.lookup(ipni_id)
        except RequestException as e:
            print('ERROR: Query failed: {}. Going directly to GTS.'.format(e), file=sys.stderr)
        else:
            if lookup_res['taxonomicStatus'] == 'Accepted':
                if 'synonyms' in lookup_res.keys():
                    res = [syn['name'] for syn in lookup_res['synonyms']]
                    print('Retrieved list of {} synonyms: '.format(len(res)))
                    for r in res:
                        print(r)
                    print()
                else:
                    print('Retrieved list of 0 synonyms.')
            elif lookup_res['taxonomicStatus'] == 'Synonym':
                print('In fact, this itself is a synonym of accepted species {}. Looking up synonyms for that...'.format(lookup_res['accepted']['name']))
                try:
                    res = [syn['name'] for syn in powo.lookup(lookup_res['accepted']['fqId'])['synonyms']]
                    if 'synonyms' in lookup_res.keys():
                        res = [syn['name'] for syn in lookup_res['synonyms']]
                        print('Retrieved {} synonyms: '.format(len(res)))
                        for r in res:
                            print(r)
                        print()
                    else:
                        print('Retrieved 0 synonyms.')
                except RequestException as e:
                    print('ERROR: Query failed: {}. Going directly to GTS.'.format(e), file=sys.stderr)

    return res


def get_locations_from_gts(name: str) -> set:
    """
    Fetches and returns a set of all locations (if any) for the given name from bgci.org via a GET request. If the query
    fails due to a network error, user is prompted for how to succeed (just skip or quit entirely).

    :return: a (possibly empty) set of all locations for this species name
    :raises RequestException: if the query fails due to a network error and user decides to quit
    """
    global TOTAL_NAMES_PROCESSED, TOTAL_LOCATION_QUERIES_SUCCEEDED
    TOTAL_NAMES_PROCESSED += 1
    genus, species = name.split(' ')[:2]
    res = set()
    print('Querying tools.bgci.org/global_tree_search.php for locations of "{}"...'.format(name))
    try:
        resp = requests.get(
            'http://data.bgci.org/treesearch/genus/{genus}/species/{species}'.format(genus=genus, species=species))
        resp = resp.json()
        if len(resp['results']) > 0:
            TOTAL_LOCATION_QUERIES_SUCCEEDED += 1
            # Locations seem to be not always free of duplicates.
            res = set([loc['country'] for result in resp['results'] for loc in result['TSGeolinks']])
            print('{} hit(s):'.format(len(res)))
            for r in res:
                print(r)
            print()
        else:
            print('No hit.')
    except RequestException as e:
        print('ERROR: Query failed: {}'.format(e), file=sys.stderr)
        reply = input('Continue? [y/n]: ')
        if 'y' not in reply.lower():
            raise e

    return res


def print_data_frame(df: pd.DataFrame):
    for _, d in df.iterrows():
        if d.Locations == '':
            continue
        else:
            print('{}, {}:'.format(d.Name, d.Author))
            for loc in d.Locations.split('; '):
                print(loc)
            print()


if __name__ == '__main__':
    # Get arguments provided via command line.
    args = docopt(__doc__)

    if len(sys.argv[1:]) is 0:
        print(__doc__)
        sys.exit()

    if args['--version']:
        print('TreeSearch version', __version__)
        sys.exit()

    # Two forms of input possible:
    # 1) If we received an input file, try to load it as data frame. Make sure, that all required columns are present.
    # 2) If input came directly via command line, build a new data frame with it.
    if args['--input'] is not None:
        try:
            # sep=None + engine='python' automatically determines field separator
            data = pd.read_csv(args['--input'], sep=None, engine='python')
        except IOError as e:
            sys.exit('Could not read file: {}'.format(e))

        if 'Name' not in data.columns or 'Author' not in data.columns:
            sys.exit(
                'Missing columns: Expected at least "Name" and "Author", but got {}'.format(
                    [col for col in data.columns]))

        if len(data) is 0:
            print('No data.')
            sys.exit()
    else:
        data = pd.DataFrame({'Name': ['{} {}'.format(args['GENUS'], args['SPECIES'])], 'Author': [args['AUTHOR']]})

    # Now iteratively fetch locations for all given species names and collect them as one list we can later append as
    # new column 'Locations' to our data frame. Be careful with empty name or author, pandas would have converted them
    # into NaN while loading the input file. This would cause problems. Therefor skip those records (we cannot do much
    # with incomplete data anyway).
    locations = [''] * len(data)
    start_time = time.time()
    for i, d in data.iterrows():
        print('-' * 80)
        if not any([(isinstance(val, float) and np.isnan(val)) for val in [d.Name, d.Author]]):
            print('{:^80}'.format('Now: {} ({})'.format(d.Name, d.Author)))
            print('-' * 80)
            try:
                current_locs = get_locations(d.Name, d.Author)
                current_locs = '; '.join(current_locs)
                locations[i] = current_locs
            except RequestException:
                # This means the user requested to quit.
                break
        elif isinstance(d.Name, float) and np.isnan(d.Name):
            print('{:^80}'.format('Skipping record #{}: Missing name'.format(i)))
            print('-' * 80)
        else:
            print('{:^80}'.format('Skipping {}: Missing author'.format(d.Name)))
            print('-' * 80)

    data['Locations'] = locations

    print('-' * 80)
    print('{:^80}'.format('Summary'))
    print('-' * 80)
    print('Processed {names} names in {secs:.2f} seconds and found locations for {hits} of {specs} species.'.format(
        names=TOTAL_NAMES_PROCESSED, secs=time.time() - start_time, hits=TOTAL_LOCATION_QUERIES_SUCCEEDED,
        specs=len(data)))
    print()

    # Two possible ways of output:
    # 1) If an output file is given, try to write it (create all directories if needed). If this fails, try to
    #    create the file in user home. If this fails, too, just print everything to stdout.
    # 2) If no output file is given, just print everything to stdout.
    if args['--output'] is not None:
        try:
            output_dir = os.path.dirname(args['--output'])
            if output_dir != '' and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            data.to_csv(args['--output'], index=False, quoting=csv.QUOTE_NONNUMERIC)
            print('Results written to', args['--output'])
        except IOError as e:
            print('Could not write results: {}'.format(e), file=sys.stderr)
            print('Trying home directory...', file=sys.stderr)
            try:
                # Generate random 5-digit suffix for file name.
                random_suffix = random.randint(1000, 9999)
                file = os.path.join(os.path.expanduser('~'), 'treesearch_{}.csv'.format(random_suffix))
                data.to_csv(file, index=False, quoting=csv.QUOTE_NONNUMERIC)
                print('Results written to', file, file=sys.stderr)
            except IOError as e:
                print('Could not write results: {}'.format(e), file=sys.stderr)
                print_data_frame(data[['Name', 'Author', 'Locations']])
                sys.exit(1)
    else:
        print_data_frame(data[['Name', 'Author', 'Locations']])
