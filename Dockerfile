FROM ubuntu:latest

MAINTAINER Norman Radtke <radtke@informatik.uni-leipzig.de>

ENV DEBIAN_FRONTEND noninteractive

# http://jaredmarkell.com/docker-and-locales/
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# update ubuntu as well as install python3
RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get install -qy python3 python3-pip && \
    apt-get install -qy git && \
    apt-get clean
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN ln -s /usr/bin/pip3 /usr/bin/pip


ENV QUIT_HOME /opt/quit
RUN mkdir $QUIT_HOME
WORKDIR $QUIT_HOME
COPY quit.py $QUIT_HOME/quit.py
RUN chmod +x $QUIT_HOME/quit.py
COPY quitFiles.py $QUIT_HOME/quitFiles.py
COPY handleexit.py $QUIT_HOME/handleexit.py
COPY requirements.txt $QUIT_HOME/requirements.txt
RUN pip install -r requirements.txt
RUN ln -s $QUIT_HOME/quit.py /usr/local/bin/quit

RUN mkdir /data
COPY start.nq /data/graph.nq

VOLUME /data
EXPOSE 80

ENV RDF_SER nquads
ENV GRAPH_FILE /data/graph.nq
CMD /opt/ldow/ldowapi.py $GRAPH_FILE --input $RDF_SER --port 80 --host 0.0.0.0
