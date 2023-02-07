# jfintegrity
cli tool to check traceability of artifacts in artifactory

## overview
this simple tool takes input from various sources, including the command line itself, and compiles a list of artifacts in an artifactory server to trace. Input options include artifacts listed in a file, repositories listed in a file, and repositories listed on the command line. Delete mode allows removal of multiple artifacts.

The tool outputs a log of its operation plus three other files:  a list of traceable artifacts, a list of untraceable artifacts, and a list of artifacts whose trace was interrupted by an error of some sort.

The tool is threaded for improved performance.

For more information, run `python jfintegrity.py --help`.

## requirements
- python 3
- pip (see requirements.txt)