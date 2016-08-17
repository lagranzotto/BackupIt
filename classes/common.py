class Common(object):

    def __init__(self, id, description):
        self.id = id
        self.description = description

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return (self.id < other.id)    

    def __repr__(self):
        return str(self.__dict__)


class Folder(Common):

    def __init__(self, id, description, path, active):
        super().__init__(id, description)
        self.path = path
        self.active = active

    def __str__(self):
        status  = 'Active' if self.active else 'Inactive'
        string  = '  '   + 'Id: {0}\n'.format(self.id)
        string += ' --------------------------------------------------------------------------------\n'
        string += '    ' + 'Status: {0}\n'.format(status)
        string += '    ' + 'Description: {0}\n'.format(self.description)
        string += '    ' + 'Path: {0}\n'.format(self.path)
        return string