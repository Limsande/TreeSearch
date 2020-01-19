# TreeSearch

TreeSearch is a synonym-aware location search tool for tree species. For a given species name it uses publicly available online data bases, namely [Plants of the World online](plantsoftheworldonline.org) and [GlobalTreeSearch](https://www.bgci.org/global_tree_search.php), to search for known locations of all available synonyms.

# Installation
TreeSearch requires Python 3. To install all dependencies with pip, type
```bash
pip install -r requirements.txt
```

Once pip finished downloading and installing the dependencies, you should be able to run TreeSearch by typing
```bash
python3 -m treesearch.py -h
```
which will show you instructions on how to use it (as the next section of this document does).

# Usage
To search for locations of the stone pine (*Pinus pinea*, described by L.), for example, simply type
```bash
python3 -m treesearch.py Pinus pinea L.
```

It is also possible to write the results to file in CSV format with the `-o` (or `--output`) flag:
```bash
python3 -m treesearch.py Pinus pinea L. -o output_file.csv
```

TreeSearch can also operate in batch mode by accepting a CSV file with multiple species names as input via the `-i` (or `--input`) flag:
```bash
python3 -m treesearch.py -i input_file.csv -o output_file.csv
```
This input file must (at least) contain a column *"Name"*, and a column *"Author"*. All additional columns are preserved and ignored.


# Contact and bug reports
You can contact the author via e-mail at <limsande(at)yahoo dot com>. Feature suggestions and feedback of any kind are very appreciated.

To file a bug report, please use this project's [issue tracker](https://github.com/Limsande/TreeSearch/issues).
