import os
import git
from rdflib import ConjunctiveGraph


class FileReference:
    """A class that manages n-quad files.

    This class stores inforamtation about the location of a n-quad file and is
    able to add and delete triples/quads to that file.
    """

    directory = '../store/'

    def __init__(self, filelocation, versioning=True):
        """Initialize a new FileReference instance.

        Args:
            filelocation: A string of the filepath.
            versioning: Boolean if versioning is enabled or not. (Defaults true)

        Raises:
            ValueError: If no file at the filelocation, or in the given directory + filelocation.
        """
        self.content = None
        self.modified = False

        # Try to open file and set the new path if file was not part of the git store, yet
        if os.path.isfile(os.path.join(self.directory, filelocation)):
            self.path = os.path.join(self.directory, filelocation)
            self.filename = filelocation
        elif os.path.isfile(filelocation):
            # File is read the first time
            filename = os.path.split(filelocation)
            # Set path to
            self.path = os.path.join(self.directory, filename[1])
            self.filename = filename[1]
        else:
            raise ValueError

        if not versioning:
            self.versioning = False
        else:
            try:
                self.repo = git.Repo(self.directory)
                assert not self.repo.bare
            except:
                print(
                    'Error:',
                    self.directory,
                    ' is not a valid Git repository.',
                    'Versioning will fail. Aborting'
                )
                raise

        return

    def __getcontent(self):
        """Return the content of a n-quad file.

        Returns:
            content: A list of strings where each string is a quad.
        """
        return self.content

    def __setcontent(self, content):
        """Set the content of a n-quad file.

        Args:
            content: A list of strings where each string is a quad.
        """
        self.content = content
        return

    def getgraphfromfile(self):
        """Return a Conjunctive Graph generated from the referenced file.

        Returns:
            A ConjunctiveGraph
        """
        graph = ConjunctiveGraph()

        try:
            graph.parse(self.path, format='nquads', publicID='http://localhost:5000/')
            print('Success: File', self.path, 'parsed')
            # quadstring = graph.serialize(format="nquads").decode('UTF-8')
            # quadlist = quadstring.splitlines()
            # self.__setcontent(quadlist)
        except:
            # Given file contains non valid rdf data
            # print('Error: File', self.path, 'not parsed')
            # self.__setcontent([[None][None][None][None]])
            pass

        return graph

    def getcontent(self):
        """Public method that returns the content of a nquad file.

        Returns:
            content: A list of strings where each string is a quad.
        """
        return self.__getcontent()

    def setcontent(self, content):
        """Public method to set the content of a n-quad file.

        Args:
            content: A list of strings where each string is a quad.
        """
        self.__setcontent(content)
        return

    def savefile(self):
        """Save the file."""
        f = open(self.path, "w")

        content = self.__getcontent()
        for line in content:
            f.write(line + '\n')
        f.close

        print('File saved')

    def sortcontent(self):
        """Order file content."""
        content = self.__getcontent()

        try:
            self.__setcontent(sorted(content))
        except AttributeError:
            pass

    def addquads(self, quad):
        """Add quads to the file content."""
        self.content.append(quad)
        self.sortcontent()

        return

    def searchquad(self, quad):
        """Look if a quad is in the file content.

        Returns:
            True if quad was found, False else
        """
        searchPattern = quad + '\n'

        if searchPattern in self.content:
            return True

        return False

    def deletequad(self, quad):
        """Add quads to the file content."""
        searchPattern = quad
        try:
            self.content.remove(searchPattern)
            self.modified = True
        except ValueError:
            # not in list
            return False

        return True

    def isversioned(self):
        """Check if a File is part of version control system."""
        return(self.versioning)
