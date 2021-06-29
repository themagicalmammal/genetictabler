from setuptools import setup, find_packages
import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

VERSION = '1.0.1'
DESCRIPTION = 'Time Table scheduling using genetic algorithm.'
LONG_DESCRIPTION = 'Time Table scheduling using with a modified genetic algorithm which is tailored as per the requirments.'

# Setting up
setup(
    name="genetictabler",
    version=VERSION,
    author="Dipan Nanda and Ashish Shah",
    author_email="d19cyber@gmail.com",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=long_description,
    packages=find_packages(),
    install_requires=[],
    keywords=['python', 'geneticalgorithm', 'genes', 'chromosomes', 'timetable'],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ]
)
