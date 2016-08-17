from cursesmenu        import CursesMenu, SelectionMenu, clear_terminal
from cursesmenu.items  import FunctionItem, SubmenuItem, ExitItem
from prompter          import prompt, yesno
from datetime          import datetime
from functools         import reduce
from classes.classes   import *
from classes.util      import XMLFactory
from shutil            import copyfile
from peewee            import *
from datetime          import date

import time
import signal
import sys
import subprocess
import os
import psutil
import tempfile

db = SqliteDatabase('database.db')

class Game(Model):

    name = CharField()
    path = CharField()

    class Meta:

        database = db

class Savegame(Model):

    game = ForeignKeyField(Game, related_name = 'saves')
    date = DateField()
    comment = TextField()
    filename = CharField()

    class Meta:

        database = db

def renderMenu():

    # Menu loop control variable
    loop = True

    # Arrays change control variable
    dirtyBit = False

    while loop:

        # Recover active backup destinations and sources
        ActiveDestinations = [x for x in filter(lambda x: x.active, Destinations['items'])]
        ActiveSources = [x for x in filter(lambda x: x.active, Sources['items'])]

        # Recover names of active backup sources
        ActiveSourcesNames = [x.description for x in ActiveSources]

        # Recover activable cloud based destinations sync clients
        ActivableClients = [SyncClient(c) for c in filter(lambda x: x.start, ActiveDestinations)]

        # Menu instantiation
        menu = CursesMenu('BackupIt - Savegame Backup Utility', 'Menu', False)

        # If there is at least one active backup subject
        if ActiveSourcesNames:

            ActiveSourcesWithBackups = []

            # Building backup and restore submenus options list
            options = ActiveSourcesNames + ['Return']

            # Declare backup submenu
            backupSelection = SelectionMenu(options, 'Backup', 'Select backup source:',    False)
            backupMenuItem = SubmenuItem('Backup', backupSelection, menu, True)

            for a in ActiveSources:
                try:
                    game = Game.get(Game.name == a.description)
                except Game.DoesNotExist:
                    game = None
                if game:
                    if game.saves:
                        ActiveSourcesWithBackups.append(a)

            ActiveSourcesWithBackupsNames = [x.description for x in ActiveSourcesWithBackups]

            options = ActiveSourcesWithBackupsNames + ['Return']

            # Declare restore submenu
            restoreSelection = SelectionMenu(options, 'Restore', 'Select restore destination:', False)
            restoreMenuItem = SubmenuItem('Restore', restoreSelection, menu, True)
        
        # Declare backup destinations management menu
        if not Destinations['items']:
            opt = manageOptionsEmpty
        else:
            opt = manageOptions

        manageDestinationsSelection = SelectionMenu(opt, 'Manage backup destinations', 'Select action:', False)
        manageDestinationsMenuItem = SubmenuItem('Manage backup destinations', manageDestinationsSelection, menu, True)
        
        # Declare backup sources management menu
        if not Sources['items']:
            opt = manageOptionsEmpty
        else:
            opt = manageOptions

        manageSourcesSelection = SelectionMenu(opt, 'Manage backup sources', 'Select action:', False)
        manageSourcesMenuItem = SubmenuItem('Manage backup sources', manageSourcesSelection, menu, True)

        # About menu Item
        aboutMenuItem =    FunctionItem('About', about, None, None, menu, True)

        # Exit menu Item
        exitMenuItem = ExitItem('Exit', menu)

        # Define main menu items
        if ActiveSources:
            if ActiveSourcesWithBackups:
                menu_items = [
                    backupMenuItem,
                    restoreMenuItem,
                    manageSourcesMenuItem,
                    manageDestinationsMenuItem,
                    aboutMenuItem,
                    exitMenuItem
                ]
            else:
                menu_items = [
                    backupMenuItem,
                    manageSourcesMenuItem,
                    manageDestinationsMenuItem,
                    aboutMenuItem,
                    exitMenuItem
                ]
        else:
            menu_items = [
                manageSourcesMenuItem,
                manageDestinationsMenuItem,
                aboutMenuItem,
                exitMenuItem
            ]

        for item in menu_items:
            menu.append_item(item)

        menu.show()
        menu.join()

        # Get main menu selected item
        menuId = menu.selected_option
        menuItem = menu.items[menuId].text

        # Backup menu item
        if menuItem == 'Backup':
            selected = getSubject(backupSelection)
            if selected:
                createBackup(selected, ActiveDestinations, ActivableClients)
        # Restore backup menu item
        elif menuItem == 'Restore':
            selected = getSubject(restoreSelection)
            if selected:
                restoreBackup(selected)
        # Manage backup destinations menu item
        elif menuItem == 'Manage backup destinations':
            # Get Manage backup destinations submenu item
            submenuItem = getMenuSelection(manageDestinationsSelection)
            # List backup destination
            if   submenuItem == 'List':   listItems(Destinations)
            # Add backup destination
            elif submenuItem == 'Add':    dirtyBit = createItem(Destinations)
            # Modify backup destination
            elif submenuItem == 'Modify': dirtyBit = modifyItem(Destinations)
            # Remove backup destination
            elif submenuItem == 'Remove': dirtyBit = removeItem(Destinations)
        # Manage backup sources menu item
        elif menuItem == 'Manage backup sources':
            # Get Manage backup sources submenu item            
            submenuItem = getMenuSelection(manageSourcesSelection)
            # List backup sources
            if   submenuItem == 'List':   listItems(Sources)
            # Add backup subject
            elif submenuItem == 'Add':    dirtyBit = createItem(Sources)
            # Modify backup subject
            elif submenuItem == 'Modify': dirtyBit = modifyItem(Sources)
            # Remove backup subject
            elif submenuItem == 'Remove': dirtyBit = removeItem(Sources)
        # Exit app'
        elif menuItem == 'Exit':
            # If arrays of backup destinations or backup sources suffers changes, save it again
            if dirtyBit:
                XMLFactory.write(Destinations, Sources)
            db.close()
            loop = False;

def listItems(list):
    print('')
    if list['items']:
        for item in list['items']:
            print(' ================================================================================')
            print(item, end='')
        print(' ================================================================================')
    else:
        print(' ' + 'No items available!')
    waitInput()

def createItem(array):
    itemType = 'destination' if array['type'] == 'D' else 'source'
    numId = str(int(reduce(lambda a, b: (a if a > b    else b), [int(x.id) for x in array['items']], 0)) + 1) 
    description = None
    path = None
    client = None
    active = True
    print('')
    while not description:
        description = prompt(' Backup {0} description:'.format(itemType))
    while not path:
        path = prompt(' Backup {0} path:'.format(itemType))
    if array['type'] == 'D':
        cloud = yesno(' Is this a cloud storaged backup folder?')
        if cloud:
            while not client:
                client = prompt(' Sync client path:')
            start = not yesno(' Start sync client after backup?', default = "no")
        else:
            client = ''
            start = False
        newItem = BackupDestination(numId, description, path, active, client, start)
    elif array['type'] == 'S':
        newItem = BackupSource(numId, description, path, active)
    print('')
    print(newItem)
    saveIt = yesno(' Save new backup {0}?'.format(itemType))
    if saveIt:
        array['items'].append(newItem)
        print('\n Backup {0} created successfully!'.format(itemType))
        waitInput()
        return True
    else:
        print('\n Backup {0} creation cancelled!'.format(itemType))
        waitInput()
    return False

def modifyItem(array):
    names = [x.description for x in array['items']]
    itemType = 'destination' if array['type'] == 'D' else 'source'
    menu = 'Modify backup {0}'.format(itemType)
    submenu = 'Select backup {0}:'.format(itemType)
    selected = SelectionMenu.get_selection(names, menu, submenu)
    if selected < len(array['items']):
        bkp = array['items'][selected]
        print('')
        description = prompt(' Backup {0} description:'.format(itemType), default = bkp.description)
        path =  prompt(' Backup {0} path:'.format(itemType), default = bkp.path)
        if array['type'] == 'D':
            cloud = yesno(' Is this a cloud storaged backup folder?')
            if cloud:
                client = prompt(' Sync client path:', default = bkp.client)
            else:
                client = ''
            if client:
                start = not yesno(' Start sync client after backup?', default= "no")
            else:
                start = False
        activated = yesno(' Activate backup {0}?'.format(itemType))
        if array['type'] == 'D':
            newItem = BackupDestination(bkp.id, description, path, activated, client, start)
        elif array['type'] == 'S':
            newItem = BackupSource(bkp.id, description, path, activated)
        print('')
        print(newItem)
        saveIt = yesno(' Confirm backup {0} changes?'.format(itemType))
        if saveIt:
            array['items'].remove(bkp)
            array['items'].append(newItem)
            array['items'].sort()
            print('\n Backup {0} modified successfully!'.format(itemType))
            waitInput()
            return True
        else:
            print('\n Changes to backup {0} cancelled!'.format(itemType))
            waitInput()
    return False

def removeItem(array):
    names = [x.description for x in array['items']]
    itemType = 'folder' if array['type'] == 'D' else 'subject'
    menu = 'Remove backup {0}'.format(itemType)
    submenu = 'Select backup {0}:'.format(itemType)
    selected = SelectionMenu.get_selection(names, menu, submenu)
    if selected < len(array['items']):
        confirm = yesno('\n Confirm exclusion of {0}?'.format(names[selected]))
        if confirm:
            array['items'].remove(array['items'][selected])
            array['items'].sort()
            print('\n Backup {0} deleted successfully!'.format(itemType))
            waitInput()
            return True
        else:
            print('\n Deletion of backup {0} cancelled!'.format(itemType))
            waitInput()
    return False

def getMenuSelection(selection):
    Id = selection.selected_option
    return selection.items[Id].text

def getSubject(selection):
    Name = getMenuSelection(selection)
    return next((subject for subject in Sources['items'] if subject.description == Name), None)

def createBackup(origin, destiny, clients):
    count = 0
    FNULL = open(os.devnull, 'w')
    dataAgora = datetime.now()
    filename = dataAgora.strftime('%Y-%m-%d_%H-%M-%S') + '.7z'
    if origin and destiny:
        print('\n Starting backup for {0}'.format(origin.description))
        commentary = input(' Enter save comment or hit ENTER to cancel: ')
        if not commentary:
            print(' Backup of {0} save files cancelled'.format(origin.description))
        else:
            count = count + 1
            parameters = ['7zr', 'a', '-t7z', '-mx9', tempfile.gettempdir()+'\\'+filename, origin.path + '*']
            try:
                subprocess.check_call(parameters, stdout = FNULL, stderr = FNULL)
            except subprocess.CalledProcessError as inst:
                 x, y = inst.args
                 if x == 1:
                     print('\n Warning - Non fatal error: check {0} at {1}'.format(filename,d.description))
                 elif x == 2:
                     print('\n Fatal error:\n {0} at {1} not created'.format(filename,d.description))
                 elif x == 8:
                     print('\n Not enough memory:\n check {0} backup point free space'.format(d.description))
            else:
                try:
                    game = Game.get(Game.name == origin.description)
                except Game.DoesNotExist:
                    game = None
                if not game:
                    game = Game(name = origin.description, path = origin.path)
                    game.save()
                for d in destiny:
                    os.makedirs(d.path + '\\' + origin.description + '\\', exist_ok=True)
                    copyfile(tempfile.gettempdir()+'\\'+filename, d.path + '\\' + origin.description + '\\' + filename)
                    print('\n Backup of {0} save files at {1} succesful'.format(origin.description,d.description))
                    savegame = Savegame(game = game, date = dataAgora, comment=commentary, filename=filename)
                    savegame.save()
                os.remove(tempfile.gettempdir()+'\\'+filename)
                db.commit()
        if count == 0:
            print('\n No backups created. Aborting...')
        else:
            if clients:
                startSyncClients(clients)
    waitInput()

def restoreBackup(subject):
    FNULL = open(os.devnull, 'w')
    ActiveDestinations = [x for x in filter(lambda x: x.active, Destinations['items'])]    
    try:
        game = Game.get(Game.name == subject.description)
    except Game.DoesNotExist:
        game = None
    if game:
        saves = game.saves
        savesComments = [a.date.strftime('%d/%m/%Y') + ' - ' + a.comment for a in saves]
        menu = 'Restore backup of {0}'.format(game.name)
        submenu = 'Select backup:'
        selected = SelectionMenu.get_selection(savesComments, menu, submenu)
        if selected < len(saves):
            src = ActiveDestinations[0].path+'\\'+game.name+'\\'+saves[selected].filename
            dest = tempfile.gettempdir()+'\\'+saves[selected].filename
            copyfile(src, dest)
            parameters = ['7zr', 'e', tempfile.gettempdir()+'\\'+saves[selected].filename, '-o'+game.path, '-y']
            try:
                subprocess.check_call(parameters, stdout = FNULL, stderr = FNULL)
            except subprocess.CalledProcessError as inst:
                x, y = inst.args
                if x == 1: print('\n Warning - Non fatal error')
                elif x == 2: print('\n Fatal error!')
                elif x == 8: print('\n Not enough memory')
            else:
                print('\n Restore of {0} save files ({1}) succesful'.format(game.name,savesComments[selected]))
            waitInput()
    else:
        print(' No backups for {0} available!'.format(game.name))
    

def about():
    print('\n By Lucas Alexandre Granzotto - lucasagranzotto@gmail.com')
    waitInput()

def IsClientRunning(client):
    for proc in psutil.process_iter():
        if proc.name() == client.exe:
            return True
    return False

def startSyncClients(list):
    print('')
    count = 0
    for c in list:
        if IsClientRunning(c):
            print(' {0} sync client already running'.format(c.description))
            count = count + 1;
        else:
            print(' Starting {0} sync client'.format(c.description))
            try:
                subprocess.Popen([c.client])
            except FileNotFoundError:
                print(' Error: {0} sync client not found!'.format(c.description))
            else:
                count = count + 1;
                time.sleep(3)
    if count > 0:
        stayOn = yesno(' Maintain sync clients running?')
        if not stayOn:
            print('')
            for c in list:
                for proc in psutil.process_iter():
                    if proc.name() == c.exe:
                        proc.kill()
                        time.sleep(1)
                print(' {0} sync client halted successfully'.format(c.description))

def waitInput():
    input('\n Press Enter to continue...')

if __name__ == "__main__":

    if os.path.isfile('config.xml'):
        Destinations = {'type': 'D', 'items': XMLFactory.read('config.xml', 'backup', 'D')}
        Sources = {'type': 'S', 'items': XMLFactory.read('config.xml', 'backup', 'S')}
    else:
        Destinations = {'type': 'D', 'items': []}
        Sources = {'type': 'S', 'items': []}

    manageOptionsEmpty = ['Add', 'Return']
    manageOptions = ['List', 'Add', 'Modify', 'Remove', 'Return']

    db.connect()

    if not Game.table_exists():
        if not Savegame.table_exists():
            db.create_tables([Game,Savegame])

    renderMenu()