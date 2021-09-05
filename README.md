
<img alt="The QuitStore Logo: A glass of quinch jam (German: Quittenmarmelade) with the Git logo on the lid. 'Graph jam in a git glass'" src="https://raw.githubusercontent.com/AKSW/QuitStore/master/assets/quitstore.png" width="512" />

# Quit Store

Build status of `master` branch:

[![Build Status](https://travis-ci.org/AKSW/QuitStore.svg?branch=master)](https://travis-ci.org/AKSW/QuitStore)
[![Coverage Status](https://coveralls.io/repos/github/AKSW/QuitStore/badge.svg?branch=master)](https://coveralls.io/github/AKSW/QuitStore)

The *Quit Store* (stands for <em>Qu</em>ads in G<em>it</em>) provides a workspace for distributed collaborative Linked Data knowledge engineering.
You are able to read and write [RDF Datasets](https://www.w3.org/TR/rdf11-concepts/#section-dataset) (aka. multiple [Named Graphs](https://en.wikipedia.org/wiki/Named_graph)) through a standard SPARQL 1.1 [Query](https://www.w3.org/TR/sparql11-query/) and [Update](https://www.w3.org/TR/sparql11-update/) interface.
To collaborate you can create multiple branches of the Dataset and share your repository with your collaborators as you know it from Git.

If you want to read more about the Quit Store we can recommend our paper:

[*Decentralized Collaborative Knowledge Management using Git*](https://natanael.arndt.xyz/bib/arndt-n-2018--jws)
by Natanael Arndt, Patrick Naumann, Norman Radtke, Michael Martin, and Edgard Marx in Journal of Web Semantics, 2018
[[@sciencedirect](https://www.sciencedirect.com/science/article/pii/S1570826818300416)] [[@arXiv](https://arxiv.org/abs/1805.03721)]

## Getting Started

To get the Quit Store you have three options:

- Download a binary from https://github.com/AKSW/QuitStore/releases (Currently works for amd64 Linux)
- Clone it with Git from our repository: https://github.com/AKSW/QuitStore
- Use Docker and see the section [Docker](#docker) in the README

### Installation from Source

Install [pip](https://pypi.python.org/pypi/pip/) and optionally [virtualenv resp. virtualenvwrapper](http://virtualenvwrapper.readthedocs.io/en/latest/install.html) (`pip install virtualenvwrapper`).

Get the Quit Store source code:
```
$ git clone https://github.com/AKSW/QuitStore.git
$ cd QuitStore
```
If you are using virtualenvwrapper:
```
$ mkvirtualenv -p /usr/bin/python3 -r requirements.txt quit
$ workon quit # this has to be executed befor you use quit store
…
$ deactivate # this can be used after you are done with quit and want to get back your “normal” environment
```
If you are not using virtualenvwrapper:
```
$ pip install -r requirements.txt
```

### Git configuration

Configure your name and email for Git.
This information will be stored in each commit you are creating with Git and the Quit Store on your system.
It is relevant so people know which contribution is coming from whom. Execute the following command if you haven't done that before.

    $ git config --global user.name "Your Name"
    $ git config --global user.email "you@e-mail-provider.org"

### Start with Existing Data (Optional)

If you already have data which you want to use in the quit store follow these steps:

1. Create a repository which will contain your RDF data.

```
$ git init /path/to/repo
```

2. Put your RDF data formatted as [N-Triples](https://www.w3.org/TR/n-triples/) and sorted (e.g. using `cat data-in.nt | LC_ALL=C sort -u > data-out.nt`) into files like `<graph>.nt` into this directory.
3. For each `<graph>.nt` file create a corresponding `<graph>.nt.graph` file which must contain the IRI for the respective graph. (These `.graph` files are also used by the [Virtuoso bulk loading process](https://virtuoso.openlinksw.com/dataspace/doc/dav/wiki/Main/VirtBulkRDFLoader#Bulk%20loading%20process)).
4. Add the data to the repository and create a commit.

```
$ git add …
$ git commit -m "init repository"
```

To ingest further versions of your data into the Quit Store you can add further commits by going through steps 2.-4..
Alternatively you are also able to execute SPARQL 1.1. Update operations to create new versions on the Quit Store.

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

`-b`, `--basepath`

Specify a base path/application root. This will work with WSGI and docker only.

`-t`, `--targetdir`

Specify a target directory where the repository can be found or will be cloned (if remote is given) to.

`-r`, `-repourl`

Specify a link/URL to a remote repository.

`-c`, `--configfile`

Specify a path to a configuration file. (Defaults to ./config.ttl)

`-nv`, `--disableversioning`

Run Quit-Store without versioning activated

`-f`, `--features`

This option enables additional features of the store:

- `provenance` - Enable browsing interfaces for provenance information.
- `persistance` - Store all internal data as RDF graph.
- `garbagecollection` - Enable garbage collection. With this feature enabled, git will check for garbage collection after each commit. This may slow down response time but will keep the repository size small.

`-v`, `--verbose` and `-vv`, `--verboseverbose`

Set the log level for the standard output to verbose (INFO) respective extra verbose (DEBUG).

`-l`, `--logfile`

Write the log output to the given path.
The path is interpreted relative to the current working directory.
The log level for the logfile is always extra verbose (DEBUG).

## Configuration File

If you want to work with configuration files you can create a `config.ttl` file.
This configuration file consists of two parts, the store configuration and the graph configuration.
The store configuration manages everything related to initializing the software, the graph configuration maps graph files to their graph IRIs.
The graph configuration in the `config.ttl` is an alternative to using `<graph>.nt.graph` files next to the graphs.
Make sure you put the correct path to your git repository (`"../store"`) and the IRI of your graph (`<http://example.org/>`) and name of the file holding this graph (`"example.nt"`).

```
conf:store a <YourQuitStore> ;
    <pathOfGitRepo> "../store" ; # Set the path to the repository that contains the files .
    <origin> "git:github.com/your/repository.git" . # Optional a git repo that will be cloned into dir given in line above on startup.


conf:example a <Graph> ; # Define a Graph resource for a named graph
    <graphUri> <http://example.org/> ; # Set the IRI of named graph
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
If you are sure that the store does not follow the W3C recommendation please [file an issue](https://github.com/AKSW/QuitStore/issues/new).

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
To use the provenance browsing feature you have to enable it with the argument `--feature=provenance`.
The provenance browsing feature extracts provenance meta data for the revisions and makes it available through a SPARQL endpoint and the blame interface.
The provenance interface is available under the following two URLs:

- `http://your-quit-host/provenance` which is a SPARQL query interface (see above) to query the provenance graph
- `http://your-quit-host/blame` to get a `git blame` like output per statement in the store

### Git Management Interface

The git management interface allows access to some operations of quit in conjunction with the underlying git repository.
You can access them with your browser at the following paths.

- `/commits`: See commits, messages, committer, and date of commits.
- `/branch`, `/merge`: allows to manage branches and merge branches with different strategies.
- `/pull`, `/fetch`, `/push` work similar to the respective git commands. (These operations will only works if you have configured remotes on the repository.)

## Docker

We also provide a [Docker image for the Quit Store](https://hub.docker.com/r/aksw/quitstore/) on the public docker hub.
The Image will expose port 8080 by default.
An existing repository can be linked to the volume `/data`.
The default configuration is located in `/etc/quit/config.ttl`, which can also be overwritten using a respective volume or by setting the `QUIT_CONFIGFILE` environment variable.

Further options which can be set are:

* `QUIT_TARGETDIR` - the target repository directory on which quit should run
* `QUIT_CONFIGFILE` - the path to the config.ttl (default: `/etc/quit/config.ttl`)
* `QUIT_LOGFILE` - the path where quit should create its logfile
* `QUIT_BASEPATH` - the HTTP base path where quit will be served
* `QUIT_OAUTH_CLIENT_ID` - the GitHub OAuth client id (for OAuth see also the [github docu](https://developer.github.com/apps/building-oauth-apps/authorization-options-for-oauth-apps/))
* `QUIT_OAUTH_SECRET` - the GitHub OAuth secret

You need a local directory where you want to store the git repository.
In the example below `mkdir /store/repo`.
Make sure the quit process in the docker container has write access to this directory by executing:
```
sudo chown 1000 /store/repo
sudo chmod u+w /store/repo
```
To run the image execute the following command (maybe you have to replace `docker` with `sudo docker`):

```
docker run -it --name containername -p 8080:8080 -v /store/repo:/data aksw/quitstore
```

The following example will start the quit store in the background in the detached mode.

```
docker run -d --name containername -p 8080:8080 -v /store/repo:/data aksw/quitstore
```

Now you should be able to access the quit web interface under `http://localhost:8080` and the SPARQL 1.1 interface under `http://localhost:8080/sparql`.

## Troubleshooting

### Use on Windows with restricted permissions

On Windows you might not be able to download the `.exe` file directly.
If so, use the `curl` command in the power shell.

When you start the QuitStore (e.g. with `quit.exe -t .`) it will try to open a port that is available from outside, which will require permission by the administrator user.
To open the port only locally you should start the QuitStore with:

    quit.exe -t . -h localhost

The default port is `5000` (`http://localhost:5000/`).

## Migrate from old Versions

### Update to 2018-11-20 from 2018-10-29 and older

If you are migrating from an NQuads based repository, as used in older versions of the QuitStore (release 2018-10-29 and older), to an NTriples based repository (release 2018-11-20 and newer) you can use teh following commands to migrate the graphs.
You should know that it is possible to have multiple graphs in one NQuads file, which is not possible for NTriples files.
Thus, you should make sure to have only one graph per file.
You may execute the steps for each NQuads file and replace `graphfile.nq` according to your filenames.

```
sed "s/<[^<>]*> .$/./g" graphfile.nq | LC_ALL=C sort -u > graphfile.nt
mv graphfile.nq.graph graphfile.nt.graph
git rm graphfile.nq
git add graphfile.nq.graph graphfile.nt graphfile.nt.graph
git commit -m "Migrate from nq to nt"
```

## License

Copyright (C) 2017 Norman Radtke <http://aksw.org/NormanRadtke> and Natanael Arndt <http://aksw.org/NatanaelArndt>

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program; if not, see <http://www.gnu.org/licenses>.
Please see [LICENSE](LICENSE) for further information.
