# Combinato Spike Sorting

## Introduction
_Combinato Spike Sorting_ is a software for spike extraction, automatic spike sorting, manual improvement of sorting, artifact rejection, and visualization of continuous recordings and spikes. It offers a toolchain that transforms raw data into single/multi-unit spike trains. The software is largely modular, thus useful also if you are interested in just extraction or just sorting of spikes.

Combinato Spike Sorting works very well with large raw data files (tested with 100-channel, 15-hour recordings, i.e. > 300 GB of raw data). Most parts make use of multiprocessing and scale well with tens of CPUs.

Combinato is a collection of a few command-line tools and two GUIs, written in Python and depending on a few standard modules. It is being developed mostly for Linux, but it works on Linux and OS X, too.

The documentation of Combinato is maintained as a [Wiki](../../wiki). 

## Installing Combinato
- [Installation on Linux](../../wiki/Installation-on-Linux) (recommended)
- [Installation on Windows](../../wiki/Installation-on-Windows)
- [Installation on OS X](../../wiki/Installation-on-OSX)

## Tutorial
Please walk through our instructive Tutorial.
- [Part I](../../wiki/Tutorial-Synthetic-Data)
- [Part II](../../wiki/Tutorial-Synthetic-Data-II)
- [Part III](../../wiki/Tutorial-Real-Data)

## More Information
- [FAQ](../../wiki/FAQ)
- [Details](../../wiki/Details)

## Contact
Please feel free to use the GitHub infrastructure for questions, bug reports, feature requests, etc.

Johannes Niediek, 2016, `jonied@posteo.de`.
