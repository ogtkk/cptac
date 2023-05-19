#   Copyright 2018 Samuel Payne sam_payne@byu.edu
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#       http://www.apache.org/licenses/LICENSE-2.0
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os.path as path
import sys
import warnings
import webbrowser
import pandas as pd

# cptac base path
CPTAC_BASE_DIR = path.abspath(path.dirname(__file__))

# Function imports
from cptac.tools.download_tools.download import download
from cptac.exceptions import CptacError, CptacWarning, NoInternetError
from utils.other_utils import df_to_tree

# Dataset imports
from cptac.cancers.brca import Brca
from cptac.cancers.ccrcc import Ccrcc
from cptac.cancers.coad import Coad
from cptac.cancers.gbm import Gbm
from cptac.cancers.hnscc import Hnscc
from cptac.cancers.lscc import Lscc
from cptac.cancers.luad import Luad
from cptac.cancers.ov import Ov
from cptac.cancers.pdac import Pdac
from cptac.cancers.ucec import Ucec


#### This code generates the __OPTIONS__ dataframe which shows all possible cancer, source, datatype combinations
def _load_options():
    """Load the tsv file with all the possible cancer, source, datatype combinations"""
    options_file = path.join(CPTAC_BASE_DIR, "options.tsv")
    df = pd.read_csv(options_file, sep="\t")
    return df

__OPTIONS__ = _load_options()

def get_options():
    return __OPTIONS__.copy()

def get_cancer_options():
    df = __OPTIONS__.copy()
    return list(df["Cancers"].unique())

def get_source_options():
    df = __OPTIONS__.copy()
    return list(df["Sources"].unique())

def list_datasets(print_tree=False):
    """List all available datasets."""
    df = __OPTIONS__.\
    copy().\
    drop("Loadable datatypes", axis=1)
    if print_tree:
        print(df_to_tree)
    else:
        return df
#### End __OPTIONS__ code

def embargo():
    """Open CPTAC embargo details in web browser."""
    message = "Opening embargo details in web browser..."
    print(message, end = '\r')
    webbrowser.open("https://proteomics.cancer.gov/data-portal/about/data-use-agreement")
    print(" " * len(message), end='\r') # Erase the message

def version():
    """Return version number of cptac package."""
    version = {}
    version_path = path.join(CPTAC_BASE_DIR, "version.py")
    with open(version_path) as fp:
        exec(fp.read(), version)
    return version['__version__']

def how_to_cite():
    """Give instructions for citing CPTAC datasets."""
    print("If you use the API to generate results, please cite our manuscript describing the API - Lindgren et al. 2021, PMID:33560848, https://pubs.acs.org/doi/10.1021/acs.jproteome.0c00919")
    print('\n')
    print("For instructions on how to cite a specific dataset, please call its how_to_cite method, e.g. cptac.Endometrial().how_to_cite()")

#### Helper functions for handling exceptions and warnings

# Because Python binds default arguments when the function is defined,
# default_hook's default will always refer to the original sys.excepthook
def _exception_handler(exception_type, exception, traceback, default_hook=sys.excepthook): 
    """Catch cptac-generated exceptions, and make them prettier."""
    if issubclass(type(exception), CptacError):
        print(f"cptac error: {str(exception)} ({traceback.tb_frame.f_code.co_filename}, line {traceback.tb_lineno})", file=sys.stderr) # We still send to stderr
    else:
        default_hook(exception_type, exception, traceback) # This way, exceptions from other packages will still be treated the same way

def _warning_displayer(message, category, filename, lineno, file=None, line=None, default_displayer=warnings.showwarning): # Python binds default arguments when the function is defined, so default_displayer's default will always refer to the original warnings.showwarning
    """Catch cptac-generated warnings and make them prettier."""
    if issubclass(category, CptacWarning):
        print(f"cptac warning: {str(message)} ({filename}, line {lineno})", file=sys.stderr) # We still send to stderr
    else:
        default_displayer(message, category, filename, lineno, file, line) # This way, warnings from other packages will still be displayed the same way

sys.excepthook = _exception_handler # Set our custom exception hook
warnings.showwarning = _warning_displayer # And our custom warning displayer
warnings.simplefilter("always", category=CptacWarning) # Edit the warnings filter to show multiple occurences of cptac-generated warnings
