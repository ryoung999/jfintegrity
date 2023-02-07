# jfintegrity
cli tool to check traceability of artifacts in artifactory

## overview
This simple tool takes input from various sources, including the command line itself, and compiles a list of artifacts in an artifactory server then traces them. Input options include artifacts listed in a file, repositories listed in a file, and repositories listed on the command line. Delete mode allows removal of multiple artifacts.

The tool outputs a log of its operation plus three other files:  a list of traceable artifacts, a list of untraceable artifacts, and a list of artifacts whose trace was interrupted by an error of some sort.

Access token (.access_token) and the Artifactory server url (.url)  can both be stored in files on disk in the jfintegrity directory if you don't want to pass them on the command line.

The tool is threaded for improved performance.

For more information, run `python jfintegrity.py --help`.

## requirements
- python 3
- pip (see requirements.txt)

## installation
Just run `make install`. Or more manually with python virtualenv:

```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```