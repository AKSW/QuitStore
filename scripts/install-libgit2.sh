#!/bin/sh

wget https://github.com/libgit2/libgit2/releases/download/v1.1.0/libgit2-1.1.0.tar.gz
tar xzf libgit2-1.1.0.tar.gz
cd libgit2-1.1.0/
cmake .
make
make install
cd ..
rm -r libgit2-1.1.0
