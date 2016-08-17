from .common import Common, Folder


class BackupSource(Folder):

    def __init__(self, id, description, path, active):
        super().__init__(id, description, path, active)


class BackupDestination(Folder):

    def __init__(self, id, description, path, active, client, start):
        super().__init__(id, description, path, active)
        self.client = client
        self.start = start

    def __str__(self):
        string  = super().__str__()
        if self.client:
            start = 'Yes' if self.start else 'No'
            string += '    ' + 'Sync client path: {0}\n'.format(self.client)
            string += '    ' + 'Auto-start: {0}\n'.format(start)
        return string


class SyncClient(Common):

    def __init__(self, client):
        super().__init__(id, client.description)
        self.client = client.client
        self.exe = self.client.split('/')[-1]