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

Communicates with plantsoftheworldonline.org and [GlobalTreeSearch](https://www.bgci.org/global_tree_search.php) to
implement a synonym-aware location lookup.

Usage:
    tree_search.py GENUS SPECIES AUTHOR [--output=FILE]
    tree_search.py --input=FILE [--output=FILE]
    tree_search.py [-h|-v]

Options:
    -h, --help  Print this help text and exit.
    -i, --input=FILE  Input file to read tuples of (genus, species, author) from (as CSV).
    -o, --output=FILE  Output file to write results to (as CSV).
    -v, --version  Print version info and exit.

Author:
    Written by Luis Imsande (limsande(at)gmail dot com).

Report bugs:
    Please report any bugs at <https://github.com/Limsande/TreeSearch/issues>.

Copyright:
    Copyright (C) 2020, Luis Imsande. License GPLv2+: GNU GPL version 2 or later
    <https://www.gnu.org/licenses/old-licenses/gpl-2.0>.
"""

__author__ = 'Luis Imsande'
__email__ = 'limsande(at)gmail dot com'
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


def get_locations(name: str, author: str) -> set:
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
    global TOTAL_NAMES_PROCESSED
    TOTAL_NAMES_PROCESSED += 1
    genus, species = name.split(' ')[:2]
    res = set()
    print('Querying tools.bgci.org/global_tree_search.php for locations of "{}"...'.format(name))
    try:
        resp = requests.get(
            'http://data.bgci.org/treesearch/genus/{genus}/species/{species}'.format(genus=genus, species=species))
        resp = resp.json()
        if len(resp['results']) > 0:
            # Locations seem to be not always free of duplicates.
            res = set([loc['country'] for result in resp['results'] for loc in result['TSGeolinks']])
            print('Retrieved {} locations:'.format(len(res)))
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


if __name__ == '__main__':
    # Get arguments provided via command line.
    args = docopt(__doc__)

    if args['--version']:
        print('TreeSearch version', __version__)
        sys.exit()
    elif args['--input'] is not None:
        try:
            data = pd.read_csv(args['--input'])
        except IOError as e:
            sys.exit('Could not read file: {}'.format(e))

        if 'Name' not in data.columns or 'Author' not in data.columns:
            sys.exit('Missing columns: Expected at least "Name" and "Author", but got {}'.format(data.columns))
    else:
        data = pd.DataFrame({'Name': ['{} {}'.format(args['GENUS'], args['SPECIES'])], 'Author': [args['AUTHOR']]})

    if len(data) is 0:
        print('No data.')
        sys.exit()

    locations = [''] * len(data)
    start_time = time.process_time()
    for i, d in data.iterrows():
        if not (isinstance(d.Author, float) and np.isnan(d.Author)):
            print('-' * 80)
            print('{:^80}'.format('Now: {} ({})'.format(d.Name, d.Author)))
            print('-' * 80)
            try:
                current_locs = get_locations(d.Name, d.Author)
                current_locs = '; '.join(current_locs)
                locations[i] = current_locs
            except RequestException:
                break
        else:
            print('-' * 80)
            print('{:^80}'.format('Skipping {}: Missing author'.format(d.Name)))
            print('-' * 80)

    data['Locations'] = locations

    print('-' * 80)
    print('{:^80}'.format('Done.'))
    print('-' * 80)
    print('Processed {} names in {:.2f} seconds.'.format(TOTAL_NAMES_PROCESSED, time.process_time() - start_time))

    if args['--output'] is not None:
        try:
            if not os.path.exists(os.path.dirname(args['--output'])):
                os.makedirs(os.path.dirname(args['--output']), exist_ok=True)
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
                print(data)
                sys.exit(1)
    else:
        print('-' * 80)
        print('{:^80}'.format('Summary'))
        print('-' * 80)
        if args['--input'] is None:
            print(data.Locations.iloc[0])
        else:
            print(data)
