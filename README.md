# TreeSearch

TreeSearch is a synonym-aware location search tool for tree species. For a given species name it uses publicly available online data bases, namely [Plants of the World online](plantsoftheworldonline.org) and [GlobalTreeSearch](https://www.bgci.org/global_tree_search.php), to search for known locations of all available synonyms.

# Installation
TreeSearch is written in Python. If you do not have Python 3 installed on your system, see https://www.python.org/. Installation of all dependencies is easy with pip. Just open a command shell, go to the project directory and type:
```
pip install -r requirements.txt
```

Once pip finished downloading and installing the dependencies, you should be able to run TreeSearch by typing
```
python3 -m treesearch.py -h

# On Linux you can also use this form
./treesearch -h
```
which will show you instructions on how to use it (or read the next section of this document).

# Usage
To search for locations of the stone pine (*Pinus pinea*, described by L.), for example, simply type
```
python3 -m treesearch.py Pinus pinea L.
```

# Contact and bug reports
You can contact the author via e-mail at <limsande(at)gmail dot com>. Feature suggestions and feedback of any kind are very appreciated.

To file a bug report, please use this project's [issue tracker](https://github.com/Limsande/TreeSearch/issues).
