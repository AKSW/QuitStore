"""
Quit Store
----------------

Quads in Git - Distributed Version Control for RDF Knowledge Bases

The Quit Store (stands for Quads in Git) provides a workspace for distributed
collaborative Linked Data knowledge engineering. You are able to read and write
RDF datasets (aka. multiple Named Graphs) through a standard SPARQL 1.1 Query
and Update interface. To collaborate you can create multiple branches of the
dataset and share your repository with your collaborators as you know it from
Git.
"""
from setuptools import setup
import os

setup(
    name='quit-store',
    version='0.24.0',
    url='https://github.com/AKSW/QuitStore',
    license='GPLv3+',
    author='Natanael Arndt, Norman Radtke',
    author_email='arndtn@gmail.com',
    description='Distributed Version Control for RDF Knowledge Bases',
    long_description=__doc__,
    entry_points={
        'console_scripts': ['quit-store=quit.run:main'],
    },
    packages=[
        'quit',
        'quit.plugins',
        'quit.plugins.serializers',
        'quit.plugins.serializers.results',
        'quit.tools',
        'quit.web',
        'quit.web.extras',
        'quit.web.modules'
    ],
    package_data={
        'quit.web': [
            'static/css/*',
            'static/fonts/*',
            'static/js/*',
            'static/octicons/*',
            'static/octicons/svg/*',
            'templates/*'
        ]
    },
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'rdflib [sparql] >4',
        'Flask',
        'Flask-Cors',
        'sortedcontainers',
        'uritools',
        'pygit2>=1.0.0'
    ],
    dependency_links=[
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Database',
        'Topic :: Database :: Database Engines/Servers',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Version Control :: Git',
        'Topic :: System :: Archiving',
        'Topic :: System :: Distributed Computing'
    ]
)
