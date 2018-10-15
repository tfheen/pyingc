#! /usr/bin/env python

import threading
import time
import re
import logging
from pprint import pprint

from k8s import config
from k8s.models.service import Service
from k8s.models.ingress import Ingress
from k8s.models.node import Node
from k8s.watcher import Watcher, WatchEvent

import varnish

import pyingc
logging.basicConfig(level=logging.INFO)

config.api_server = 'https://kubernetes.default.svc.cluster.local:8443'
config.verify_ssl = '/home/tfheen/.minikube/ca.crt'
config.cert = ('/home/tfheen/.minikube/client.crt', '/home/tfheen/.minikube/client.key')


class Manager(object):
    def __init__(self, condition):
        self.generation = 0
        self.objects = {}
        self.condition = condition

    def handle_event(self, event, _filter):
        old = self.objects.get(event.object.metadata.name)
        if event.type in (WatchEvent.ADDED, WatchEvent.MODIFIED):
            self.objects[event.object.metadata.name] = event.object
        elif event.type == WatchEvent.DELETED:
            del self.objects[event.object.metadata.name]
        else:
            raise ValueError("Unknown WatchEvent type {}".format(event.type))
        if not _filter or not _filter(old, event.object):
            self.condition.acquire()
            self.condition.notify()
            self.condition.release()

    def watch(self, watchType, _filter=None):
        logging.info("watching for events of type {}".format(watchType))
        for event in Watcher(watchType).watch():
            self.handle_event(event, _filter)


if __name__ == '__main__':
    condition = threading.Condition()
    ingMgr = Manager(condition)
    ingThread = threading.Thread(target=ingMgr.watch, args=(Ingress,))
    svcMgr = Manager(condition)
    svcThread = threading.Thread(target=svcMgr.watch, args=(Service,))
    nodeMgr = Manager(condition)
    nodeThread = threading.Thread(target=nodeMgr.watch, args=(Node, pyingc.interestingNodeFilter))

    condition.acquire()
    ingThread.start()
    svcThread.start()
    nodeThread.start()

    jinja_env = pyingc.jinja_env
    v = varnish.VarnishHandler('localhost:6082', secret=open("/etc/varnish/secret").read().strip())
    time.sleep(3)
    vcls = []

    while True:
        condition.wait()
        tmpl = jinja_env.get_template("template.vcl")
        vcl = re.sub("\n\n\n*", "\n", tmpl.render(ingresses=ingMgr.objects.values(), services=svcMgr.objects.values(), nodes=nodeMgr.objects.values()))
        logging.debug(vcl)
        qs = pyingc.quotestring(vcl)
        try:
            vcl_name = "k8s-{}".format(int(time.time()))
            v.vcl_inline(vcl_name, qs)
            vcls.append(vcl_name)
            while len(vcls) > 3:
                v.vcl_discard(vcls[0])
                vcls.pop(0)
            v.vcl_use(vcl_name)
        except Exception, e:
            logging.exception("Sending stuff")
