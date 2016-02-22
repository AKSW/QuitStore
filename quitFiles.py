from rdflib import ConjunctiveGraph
from rdflib.plugins.sparql import parser
from rfc3987 import parse
import os
import sys
import git
from dulwich.repo import Repo


class GraphFile:
    def __init__(self, directory, graphfile, versioning):
        self.graphfile = graphfile
        self.modified = False
        self.versioining = False

        if directory.endswith('/'):
            filepath = directory + graphfile
            directory = directory[:-1]
            self.repodir = directory
        else:
            filepath = directory + '/' + graphfile
            self.repodir = directory

        if os.path.isfile(filepath):
            try:
                with open(filepath, 'r') as f:
                    self.content = f.readlines()
                f.close
                self.path = filepath
            except:
                print('Error: Path ' +  filepath + ' could not been opened')
                raise ValueError
        else:
            print('Error: Path ' + filepath + ' is no file')
            raise ValueError

        print('Success: File ' + filepath + ' is now known as a graph')

        if versioning == True:
            self.versioning = True
            try:
                #print(test[0])
                self.repo = git.Repo(directory)
                assert not self.repo.bare
            except:
                print('Error: ' + directory + ' is not a valid git repository. Versioning will fail. Aborting')
                raise
        return

    def savefile(self):
        if self.modified == False:
            return

        f = open(self.path, "w")

        for line in self.content:
            f.write(line)
        f.close

        print('File saved')

    def sortfile(self):
        try:
            self.content = sorted(self.content)
        except AttributeError:
            pass

    def commit(self):
        if self.versioning == False or self.modified == False:
            return

        gitstatus = self.repo.git.status('--porcelain')

        if gitstatus == '':
            self.modified = False
            return

        try:
            print("Trying to stage " + self.graphfile)
            self.repo.index.add([self.graphfile])
        except:
            print('Couldn\'t stage file: ' + self.graphfile)
            raise

        msg = '\"New commit from quit-store\"'
        committer = str.encode('Quit-Store <quit.store@aksw.org>')
        #commitid = self.repo.do_commit(msg, committer)

        try:
            print("Trying to commit " + self.graphfile)
            self.repo.git.commit('-m', msg)
        except:
            print('Couldn\'t commit file: ' + self.path)
            raise

        self.modified == False

    def addtriple(self, triple, resort = True):
        print('Trying to add: ' + triple)
        self.content.append(triple + '\n')
        self.modified = True

    def searchtriple(self, triple):
        searchPattern = triple + '\n'

        if searchPattern in self.content:
            return True

        return False

    def deletetriple(self, triple):
        searchPattern = triple + '\n'
        try:
            self.content.remove(searchPattern)
            self.modified = True
        except ValueError:
            #not in list
            pass
        except AttributeError:
            pass

    def getcontent(self):
        return(self.content)

    def setcontent(self, content):
        self.content = content

    def isversioned(self):
        return(self.versioning)

class GitRepo:
    def __init__(self, path):
        self.path = path

class FileList:
    def __init__(self):
        self.store = ConjunctiveGraph()
        self.files = {}

    def getgraphobject(self, graphuri):
        for k, v in self.files.items():
            if k == graphuri:
                return v
        return

    def graphexists(self, graphuri):
        graphuris = list(self.files.keys())
        try:
            graphuris.index(graphuri)
            return True
        except ValueError:
            return False

    def addFile(self, graphuri, graphFileObject):
        try:
            self.files[graphuri] = graphFileObject
            self.store.parse(graphFileObject[''])
        except:
            print('Something went wrong with file: ' + name)
            raise ValueError

    def getgraphlist(self):
        return list(self.files.keys())

class QueryCheck:
    def __init__(self, querystring, graphs):
        try:
            self.parsedQuery = parser.parseQuery(querystring)
            print('SELECT Query')
            self.queryType = 'SELECT'
        except:
            pass

        try:
            self.parsedQuery = parser.parseUpdate(self.query)
            print('Update Query')
            self.queryType = 'UPDATE'
        except:
            pass

        if self.parsedQuery == None:
            print('Mit der Query stimmt etwas nicht')
            raise Exception()

        self.query = querystring
        return

    '''
    This method checks the given SPARQL query. All Select Queries will return
    an empty diff.
    Queries containing the keywords 'insert' or 'delete' may return a diff.
    To generate the diffs each occurence of 'insert' or 'delete' will be
    rewritten into a construct query.
    '''
    def getParsedQuery(self):
        return self.parsedQuery

    def getResult(self):
        return

    def getdiff(self):
        try:
            delstart = self.query.find('DELETE')
        except:
            # no DELETE part
            pass

        try:
            insstart = self.query.find('INSERT')
        except:
            # no INSERT part
            pass

        try:
            insstart = self.query.find('INSERT')
        except:
            # no DELETE part
            pass

        return

    def getquery(self):
        return self.query

    def __isvalidquery(self):
        query = str(request.args.get('query'))
        return

    def __parse(self):
        return
