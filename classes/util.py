from .classes import BackupDestination, BackupSource
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.dom import minidom


class XMLFactory(object):

    def read(string, segment, type):
        group = 'destinations' if type == 'D' else 'sources'
        root = parse(string).getroot().find(segment).find(group)
        returnArray = []
        for leaf in root:
            id = leaf.attrib['id']
            description = leaf.find('description').text
            path = leaf.find('path').text
            active = 'active' not in leaf.attrib
            if type == 'D':
                client = ''
                start = False
                if leaf.find('client') is not None:
                    client = leaf.find('client').text
                    start = 'start' not in leaf.find('client').attrib
                newDestination = BackupDestination(id, description, path, active, client, start)
                returnArray.append(newDestination)
            elif type == 'S':
                newSource = BackupSource(id, description, path, active)
                returnArray.append(newSource)
        return returnArray

    def write(destinations, sources):
        configTag = Element('configuration')
        backupTag = SubElement(configTag, 'backup')
        sourcesTag = SubElement(backupTag, 'sources')
        for subject in sources['items']:
            locationTag = SubElement(sourcesTag, 'location')
            locationTag.set('id', str(subject.id))
            if not subject.active:
                locationTag.set('active', str(subject.active))
            descriptionTag = SubElement(locationTag, 'description')
            descriptionTag.text = subject.description
            pathTag = SubElement(locationTag, 'path')
            pathTag.text = subject.path
        destinationsTag = SubElement(backupTag, 'destinations')
        for destination in destinations['items']:
            locationTag = SubElement(destinationsTag, 'location')
            locationTag.set('id', str(destination.id))
            if not destination.active:
                locationTag.set('active', str(destination.active))
            descriptionTag = SubElement(locationTag, 'description')
            descriptionTag.text = destination.description
            pathTag = SubElement(locationTag, 'path')
            pathTag.text = destination.path
            if destination.client:
                clientTag = SubElement(locationTag, 'client')
                if not destination.start:
                    clientTag.set('start', str(destination.start))
                clientTag.text = destination.client
        logfile = open('config.xml', 'w')
        print(prettify(configTag), file = logfile)
        logfile.close()


def prettify(elem):
    rough_string = tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent = "\t")