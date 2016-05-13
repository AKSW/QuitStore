# Run in docker

For tests build a local docker image and run the container
```
docker build  -t "quit" .
docker run --name=quit -p port:80 quit:latest
```
with "port" being an unused port of your host.

# Configuaration

edit config.ttl

```
conf:store a <YourQuitStore> ;
    <pathOfGitRepo> "../store" . # Set the path to the repository that contains the files .

conf:example a <Graph> ; # Define a Graph resource for a named graph
    <graphUri> <http://example.org/> ; # Set the URI of named graph
    <isVersioned> 1 ; # Defaults to True, future work
    <hasQuadFile> "example.nq" . # Set the filename
```


# API


Execute a query with curl

```
curl -X POST -L -T path/to/query/file  http://your.host/sparql
```

Get commits, messages, committer and date of commits

```
http://your.host/git/log
```


# TODO:

Reinit store with data from commit with id

```
http://your.host/git/checkout?commitid=12345
```

# Local install with python environment

Install [pip](https://pypi.python.org/pypi/pip/) to be able to do the following:
```
pip install virtualenv
cd /path/to/this/repo
mkvirtualenv -p /usr/bin/python3.5 quit
pip install -r requirements.txt
./quit.py
```
