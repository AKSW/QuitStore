# Quit-Store

Status of `master` branch:

[![Build Status](https://travis-ci.org/AKSW/QuitStore.svg?branch=master)](https://travis-ci.org/AKSW/QuitStore)
[![Coverage Status](https://coveralls.io/repos/github/AKSW/QuitStore/badge.svg?branch=master)](https://coveralls.io/github/AKSW/QuitStore)

This project runs a SPARQL endpoint for Update and Select Queries and enables versioning with Git for each [Named Graph](https://en.wikipedia.org/wiki/Named_graph).

## Preparation of the Store repository

1. Create a directory, which will contain your RDF data
2. Run `git init` in this directory
3. Put your RDF data formated as [N-Quads](https://www.w3.org/TR/2014/REC-n-quads-20140225/) into this directory (an empty file should work as well)
4. Add the data to the repository (`git add …`) and create a commit (`git commit -m "init repository"`)
5. Create a configuration file named `config.ttl` (an example is contained in this directory)

## Configuaration of config.ttl

Adjust the `config.ttl`.
Make sure you put the correct path to your git repository (`"../store"`) and the URI of your graph (`<http://example.org/>`) and name of the file holding this graph (`"example.nq"`).

```
conf:store a <YourQuitStore> ;
    <pathOfGitRepo> "../store" ; # Set the path to the repository that contains the files .
    <origin> "git:github.com/your/repository.git" . # Optional a git repo that will be cloned into dir given in line above on startup.


conf:example a <Graph> ; # Define a Graph resource for a named graph
    <graphUri> <http://example.org/> ; # Set the URI of named graph
    <isVersioned> 1 ; # Defaults to True, future work
    <graphFile> "example.nq" . # Set the filename
```

The `config.ttl` could as well be put under version control for collaboration, but this is not necessary.

## Run from command line

Install [libgit2](https://libgit2.github.com/) needed for pygit2 bindings.
Install [pip](https://pypi.python.org/pypi/pip/) and optionally [virtualenv resp. virtualenvwrapper](http://virtualenvwrapper.readthedocs.io/en/latest/install.html):
```
pip install virtualenv
cd /path/to/this/repo
mkvirtualenv -p /usr/bin/python3.5 quit
```

Install the required dependencies and run the store:
```
pip install -r requirements.txt
./quit.py
```

### Command line options
`-cm`, `--configmode`

Quit-Store can be started in three different modes.
These modes differ in how the store choses the named graphs and the corresponding files that will be part of the store.

1. `localconfig` - Use the graphs specified in a local config file (e.g. `config.ttl`).
2. `repoconfig` - Search for a `config.ttl` file in the specified repository.
3. `graphfiles` - Graph URIs are read from `*.graph` files for each RDF file (as also used by the [Virtuoso bulk loading process](https://virtuoso.openlinksw.com/dataspace/doc/dav/wiki/Main/VirtBulkRDFLoader#Bulk%20loading%20process)), furthermore found N-Quads files are analyzed to get the URI of named graphs from the used context.

`-t`, `--targetdir`

Specifiy a target directory where the repository can be found or will be cloned (if remote is given) to.

`-r`, `-repourl`

Specifiy a link/URI to a remote repository.

`-c`, `--configfile`

Specify a path to a configuration file. (Defaults to ./config.ttl)

`-nv`, `--disableversioning`

Run Quit-Store without versioning activated

`-gc`, `--garbagecollection`

Enable garbage collection. With this option activated, git will check for garbage collection after each commit. This may slow down response time but will keep the repository size small.

`-f`, `--features`

This option enables additional features of the store:

- `provenance` - Store provenance information for each revision.
- `persistance` - Store all internal data as RDF graph.

`-v`, `--verbose` and `-vv`, `--verboseverbose`

Set the loglevel for the standard output to verbose (INFO) respective extra verbose (DEBUG).

`-l`, `--logfile`

Write the log output to the given path.
The path is interpreted relative to the current working directory.
The loglevel for the logfile is always extra verbose (DEBUG).

## API

Execute a query with curl

```
curl -X POST -L -T path/to/query/file  http://your.host/sparql
```

Get commits, messages, committer and date of commits

```
http://your.host/git/log
```

## Tips and Tricks

If you want to convert an N-Triples file to N-Quads where all data is in the same graph, the following line might help.

    sed "s/.$/<http:\/\/example.org\/> ./g" data.nt > data.nq

## Docker

We also provide a [Docker image for the Quit Store](https://hub.docker.com/r/aksw/quitstore/) on the public docker hub.
The Image will expose port 80 by default.
An existing repository can be linked to the volume `/data`.
The default configuration is located in `/etc/quit/config.ttl`, which can also be overwritten using a respective volume or by setting the `QUIT_CONFIGFILE` environment variable.

To run the image execute the following command:

```
docker run --name containername -v /existing/store/repo:/data aksw/quitstore
```

The following example will map the quit store port to the host port 8080.

```
docker run --name containername -p 8080:80 -v /existing/store.repo:/data aksw/quitstore
```

There is also the `QUIT_PORT` environment variable, which changes the port, to which the Quit Store binds inside the docker container.

## TODO:

Reinit store with data from commit with id

```
http://your.host/git/checkout?commitid=12345
```

## License

Copyright (C) 2017 Norman Radtke <http://aksw.org/NormanRadtke> and Natanael Arndt <http://aksw.org/NatanaelArndt>

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program; if not, see <http://www.gnu.org/licenses>.
Please see [LICENSE](LICENSE) for further information.
