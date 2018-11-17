# Quit Store

Build status of `master` branch:

[![Build Status](https://travis-ci.org/AKSW/QuitStore.svg?branch=master)](https://travis-ci.org/AKSW/QuitStore)
[![Coverage Status](https://coveralls.io/repos/github/AKSW/QuitStore/badge.svg?branch=master)](https://coveralls.io/github/AKSW/QuitStore)

The *Quit Store* (stands for <em>Qu</em>ads in G<em>it</em>) provides a worspace for distributed collaborative Linked Data knowledge engineering.
You are able read and write [RDF Datasets](https://www.w3.org/TR/rdf11-concepts/#section-dataset) (aka. multiple [Named Graphs](https://en.wikipedia.org/wiki/Named_graph)) through a standard SPARQL 1.1 Query and Update interface.
To colaborate you can create mutiple branches of the Dataset and share your repository with your collaborators as you know if form Git.

## Getting Started

To get the Quit Store you have three options:

- Download a binary from https://github.com/AKSW/QuitStore/releases (Currently works for amd64 Linux)
- Clone it with Git from our repository: https://github.com/AKSW/QuitStore
- Use Docker and see the section [Docker](#docker) in the README

### Installation from Source

Install [libgit2](https://libgit2.github.com/) including the headers (e.g. `libgit2-27` and `libgit2-dev` on ubuntu) which is needed for the pygit2 bindings.
Find out which version of libgit2 you've got on your system and adjust the respective line in the `requirements.txt` of the Quit Store. The minor levels of the versions have to be equal (libgit2 `0.27.4` -> `pygit2==0.27.2`).

Install [pip](https://pypi.python.org/pypi/pip/) and optionally [virtualenv resp. virtualenvwrapper](http://virtualenvwrapper.readthedocs.io/en/latest/install.html) (`pip install virtualenvwrapper`).

Get the Quit Store source code:
```
$ git clone https://github.com/AKSW/QuitStore.git
$ cd QuitStore
```
If you are using virtualenvwrapper:
```
$ mkvirtualenv -p /usr/bin/python3.5 -r requirements.txt quit
```
If you are not using virtualenvwrapper:
```
$ pip install -r requirements.txt
```

### Git configuration

Configure your name and email for Git. This information will be stored in each commit you are creating with Git and the QuitStore on your system. It is relevant so people know which contribution is comming from whome. Execute the following command if you havn't done that before.

    $ git config --global user.name="Your Name"
    $ git config --global user.email=you@e-mail-provider.org

### Start with Existing Data (Optional)

If you already have data which you want to use in the quit store follow these steps:

1. Create a repository which will contain your RDF data

```
$ git init /path/to/repo
```

2. Put your RDF data formated as [N-Triples](https://www.w3.org/TR/n-triples/) into files like `<graph>.nt` into this directory
3. For each `<graph>.nt` file create a corresponding `<graph>.nt.graph` file which must contain the IRI for the respsective graph
4. Add the data to the repository and create a commit

```
$ git add …
$ git commit -m "init repository"
```

### Start the Quit Store

If you are using the binary:
```
$ chmod +x quit #
$ ./quit -t /path/to/repo
```

If you have it installed from the sources:
```
$ quit/run.py -t /path/to/repo
```

Open your browser and go to [`http://localhost:5000/`](http://localhost:5000/).

Have a lot of fun!

For more command line options check out the section [Command Line Options](#command-line-options) in the README.



## Command Line Options
`-cm`, `--configmode`

Quit-Store can be started in three different modes.
These modes differ in how the store choses the named graphs and the corresponding files that will be part of the store.

2. `configfile` - Search for a `config.ttl` file in the repository.
3. `graphfiles` - Graph URIs are read from `*.graph` files for each RDF file (as also used by the [Virtuoso bulk loading process](https://virtuoso.openlinksw.com/dataspace/doc/dav/wiki/Main/VirtBulkRDFLoader#Bulk%20loading%20process)).

`-b`, `--basepath`

Specifiy a basepath/application root. This will work with WSGI and docker only.

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

## Configuaration File

If you want to work with configuration files you can create a `config.ttl` file.
This configuration file consists of two parts, the store configuration and the graph configuration.
The store configuration manages everything related to initializing the software, the graph configuration maps graph files to their graph IRIs.
The graph configuration in the `config.ttl` is an alternative to using `<graph>.nt.graph` files next to the graphs.
Make sure you put the correct path to your git repository (`"../store"`) and the URI of your graph (`<http://example.org/>`) and name of the file holding this graph (`"example.nt"`).

```
conf:store a <YourQuitStore> ;
    <pathOfGitRepo> "../store" ; # Set the path to the repository that contains the files .
    <origin> "git:github.com/your/repository.git" . # Optional a git repo that will be cloned into dir given in line above on startup.


conf:example a <Graph> ; # Define a Graph resource for a named graph
    <graphUri> <http://example.org/> ; # Set the URI of named graph
    <isVersioned> 1 ; # Defaults to True, future work
    <graphFile> "example.nt" . # Set the filename
```

## API

The Quit-Store comes with three kinds of interfaces, a SPARQL update and query interface, a provenance interface, and a Git management interface.

### SPARQL Update and Query Interface
The SPARQL interface support update and select queries and is meant to adhere to the [SPARQL 1.1 Protocol](https://www.w3.org/TR/sparql11-protocol/).
You can find the interface to query the current `HEAD` of your repository under `http://your-quit-host/sparql`.
To access any branch or commit on the repository you can query the endpoints under `http://your-quit-host/sparql/<branchname>` resp. `http://your-quit-host/sparql/<commitid>`.
Since the software is still under development there might be some missing features or strange behavior.
If you are sure that the store does not follow the W3C recommandation please [file an issue](https://github.com/AKSW/QuitStore/issues/new).

#### Examples

Execute a select query with curl
```
curl -d "select ?s ?p ?o ?g where { graph ?g { ?s ?p ?o} }" -H "Content-Type: application/sparql-query" http://your-quit-host/sparql
curl -d "select ?s ?p ?o ?g where { graph ?g { ?s ?p ?o} }" -H "Content-Type: application/sparql-query" http://your-quit-host/sparql/develop
```
If you are interested in a specific result mime type you can use the content negotiation feature of the interface:
```
curl -d "select ?s ?p ?o ?g where { graph ?g { ?s ?p ?o} }" -H "Content-Type: application/sparql-query" -H "Accept: application/sparql-results+json" http://your-quit-host/sparql
```

Execute an update query with curl

```
curl -d "insert data { graph <http://example.org/> { <urn:a> <urn:b> <urn:c> } }" -H "Content-Type: application/sparql-update"  http://your-quit-host/sparql
```

### Provenance Interface
The provenance interface is available under the following two URIs:

- `http://your-quit-host/provenance` which is a SPARQL query interface (see above) to query the provenance graph
- `http://your-quit-host/blame` to get a `git blame` like output per statement in the store

### Git Management Interface

- `/commits`: Get commits, messages, committer and date of commits
- `/pull`, `/fetch`, `/push`, `/merge`, `/revert` which are parallel to the respective Git commands

```
http://your.host/git/log
```

## Docker

We also provide a [Docker image for the Quit Store](https://hub.docker.com/r/aksw/quitstore/) on the public docker hub.
The Image will expose port 80 by default.
An existing repository can be linked to the volume `/data`.
The default configuration is located in `/etc/quit/config.ttl`, which can also be overwritten using a respective volume or by setting the `QUIT_CONFIGFILE` environment variable.

Further options which can be set are:

* QUIT_TARGETDIR - the target repository directory on which quit should run
* QUIT_CONFIGFILE - the path to the config.ttl (default: `/etc/quit/config.ttl`)
* QUIT_LOGFILE - the path where quit should create its logfile
* QUIT_BASEPATH - the HTTP basepath where quit will be served
* QUIT_OAUTH_CLIENT_ID - the GitHub OAuth client id (for oauth see also the [github docu](https://developer.github.com/apps/building-oauth-apps/authorization-options-for-oauth-apps/))
* QUIT_OAUTH_SECRET - the GitHub OAuth secret

To run the image execute the following command:

```
docker run --name containername -v /existing/store/repo:/data aksw/quitstore
```

The following example will map the quit store port to the host port 8080.

```
docker run --name containername -p 8080:80 -v /existing/store.repo:/data aksw/quitstore
```

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
