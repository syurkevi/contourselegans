# Contours.Elegans -- Nematode Analysis Program
    This python script allows the "slicing" of microscope video into segments of backwards locomotion.
    The segments provide contour analysis for the dorsal and ventral segments of a C.Elegans nematode.
    Several metrics are measured:
            - Average Curvature
            - Maximum/Minimum Curvature
            - Local Curvature

##Dependencies
The script is written in Python 2. It has the depencies of OpenCV, NumPy, matplotlib, and JSON tricks.
### Linux installation
```
sudo apt-get install python python-pip python-numpy python-opencv python-matplotlib
pip install json-tricks
git clone https://github.com/syurkevi/contourselegans && cd contourselegans
python worms.py --help
```
### Windows installation
Python: Download Python 2.7 here: https://www.python.org/downloads/  
NumPy: Download the NumPy installers here: http://www.scipy.org/scipylib/download.html  
OpenCV: Download the OpenCV 2 installer here: http://opencv.org/downloads.html  
matplotlib: Installation instructions here: http://matplotlib.org/users/installing.html  
JSON tricks: This is a pip package. Consult this guide on pip installation on windows:   https://github.com/BurntSushi/nfldb/wiki/Python-&-pip-Windows-installation  
If pip is installed, the package can then be installed simply by invoking the pip command   
```
pip install json-tricks
```
The other python dependencies can be installed just as simply through pip.


## Running the script
The script is currently set up to be launched from a command line interface. 
```
python worms.py --mutant n2 --file  Full/Path/To/File/N2.avi
```
There are two mandatory flags.
The `--mutant` flag which specifies which mutant is shown in the video.
The `--file` flag which is the full path to the video that will be analyzed

For additional flags use the help flag
```
python worms.py --help
```
or for more information on the usage of the UI, use the tutorial flag
```
python worms.py --tutorial
```


