
from jinja2 import Template, Environment, FileSystemLoader

import string

def c_ident(value):
    if value:
        return ''.join([i if i in string.ascii_lowercase + string.digits else '_' for i in value.lower()])

jinja_env = Environment(extensions=['jinja2.ext.loopcontrols'],
                        loader=FileSystemLoader('templates'),
                        lstrip_blocks=True)
jinja_env.filters['c_ident'] = c_ident

def sort_by_priority(value):
    if value:
        return sorted(value, key=lambda x: int(x.metadata.annotations.get('priority', '50')))

jinja_env.filters['sort_by_priority'] = sort_by_priority


def interestingNodeFilter(old, new):
    if not old or not new:
        return True
    return old.spec == new.spec and old.status.addresses == new.status.addresses and \
        old.status.nodeInfo == new.status.nodeInfo
#		readyEqual := api.IsNodeReady(oldNode) == api.IsNodeReady(curNode)

def quotestring(s):
    return str('"' + s.replace("\n", "\\n").replace('"','\\"') + '"')
