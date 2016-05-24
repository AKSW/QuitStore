# Quit-Store

This project runs a SPARQL endpoint for Update and Select Queries and enables versioning with Git per named graph.

## Preparation of the Store repository

1. create a directory, which will contain your RDF data
2. run `git init` in this directory
3. put your RDF data formated as [N-Quads](https://www.w3.org/TR/2014/REC-n-quads-20140225/) into this directory (an empty file should work as well)
4. add the data to the repository (`git add …`) and create a commit (`git commit -m "init repository"`)

## Run in docker

For tests build a local docker image and run the container
```
docker build  -t "quit" .
docker run --name=quit -p port:80 --link config.ttl/config.ttl quit:latest
```
with "port" being an unused port of your host and a updated config.ttl (see below)

## Configuaration of config.ttl

Adjust the config.ttl. Make sure you put the correct path to your git repository (`"../store"`) and the URI of your graph (`<http://example.org/>`) and name of the file holding this graph (`"example.nq"`).

```
conf:store a <YourQuitStore> ;
    <pathOfGitRepo> "../store" . # Set the path to the repository that contains the files .

conf:example a <Graph> ; # Define a Graph resource for a named graph
    <graphUri> <http://example.org/> ; # Set the URI of named graph
    <isVersioned> 1 ; # Defaults to True, future work
    <hasQuadFile> "example.nq" . # Set the filename
```

## API

Execute a query with curl

```
curl -X POST -L -T path/to/query/file  http://your.host/sparql
```

Get commits, messages, committer and date of commits

```
http://your.host/git/log
```

## TODO:

Reinit store with data from commit with id

```
http://your.host/git/checkout?commitid=12345
```

## Local install with python environment

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

## License

This project is licensed under the terms of the GNU General Public License (GPL), please see [LICENSE](LICENSE) for further information.
