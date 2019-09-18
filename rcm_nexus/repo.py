# -*- coding: utf-8 -*-
# Copyright (c) 2014 Red Hat, Inc..
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#
# Utility methods for working with Nexus repositories, including content
# management via rsync. Also includes Repository class definition, which
# provides some convenience methods for accessing options associated with a
# repository defintion.
#
# Authors:
#    John Casey (jcasey@redhat.com)
#    Lubomír Sedlář (lsedlar@redhat.com)

from __future__ import print_function

from lxml import (objectify,etree)
from rcm_nexus.session import Enum
import os
import shutil
import re
import sys

WRITE_POLICIES = Enum(read_only='READ_ONLY', read_write='ALLOW_WRITE', write_once='ALLOW_WRITE_ONCE')
REPO_POLICIES = Enum(release='RELEASE', snapshot='SNAPSHOT')
CHECKSUM_POLICIES = Enum(warn='WARN', fail='FAIL')
REPO_TYPES = Enum(hosted='hosted', proxy='proxy', remote='proxy')
    
REPOS_PATH = '/service/local/repositories'
NAMED_REPO_PATH = REPOS_PATH + '/{key}'
COMPRESSED_CONTENT_PATH = NAMED_REPO_PATH + "/content-compressed{delete}"


class progress_report(object):
    def __init__(self, filepath, mode="rb"):
        self.file_size = os.path.getsize(filepath)
        self.read_size = 0
        self.filepath = filepath
        self.width = 60

    def __enter__(self):
        self.file = open(self.filepath, "rb")
        self.print("\033[?25l")
        return self

    def __exit__(self, type_, value, traceback):
        self.file.close()
        self.print("\033[?25h\n")

    def print(self, msg):
        """Print value to stdout if it is attached to a TTY."""
        if sys.stdout.isatty():
            sys.stdout.write(msg)
            sys.stdout.flush()

    def read(self, size=-1):
        data = self.file.read(size)
        perc = int(self.width * self.read_size / self.file_size)
        consumed_perc = 100 * self.read_size / self.file_size
        hashes = "#" * perc
        gap = " " * (self.width - perc)
        self.print("\r {0:3.0f} % [{1}{2}]".format(consumed_perc, hashes, gap))
        self.read_size += len(data)
        return data

    def __len__(self):
        return self.file_size


def push_zip(session, repo_key, zip_file, delete_first=False):
    delete_param = ''
    if delete_first:
        delete_param = '?delete=true'

    url = COMPRESSED_CONTENT_PATH.format(key=repo_key, delete=delete_param)
    if session.debug is True:
        print("POSTing: %s" % url)
    with progress_report(zip_file) as f:
        session.post(
            url, f, expect_status=201, headers={"Content-Type": "application/zip"}
        )


def load(session, key, ignore_missing=True):
    response, xml = session.get(NAMED_REPO_PATH.format(key=key), ignore_404=ignore_missing)
    if ignore_missing and response.status_code == 404:
        return None
    
    doc = objectify.fromstring(xml)
    # return Repository(doc.data.id, doc.data.name)._set_xml_obj(doc)
    return Repository(doc)

def load_all(session, name_pattern=None):
    response, xml = session.get(REPOS_PATH)
    
    doc = etree.fromstring(xml)
    name_re = None
    if name_pattern is not None:
        name_re = re.compile(name_pattern)
        
    repos = []
    for child in doc.xpath('//repositories-item'):
        name = child.xpath('name/text()')
        if len(name) < 1:
            if session.debug is True:
                print("Discarding nameless repository.")
            continue
        else:
            name = name[0]
        
        if session.debug is True:
            print("Checking if '%s' matches: '%s'" % (name_pattern, name))
        
        match = None
        if name_re is not None:
            match = name_re.match(name)
        
        if name_re is None or match is not None:
            rid=child.xpath('id/text()')
            if len(rid) < 1:
                if session.debug is True:
                    print("Discarding: %s (no id element)" % name)
                continue
            else:
                rid = rid[0]
            
            child.tag = 'data'
            r = etree.Element('repository')
            r.insert(0,child)
            child = r
            
            doc = objectify.fromstring(etree.tostring(child))
            # repos.append(Repository(rid, name)._set_xml_obj(doc))
            repos.append(Repository(doc))
            
            if session.debug is True:
                print("+ %s" % name)
    
    return repos
#    return Repository(doc.data.id, doc.data.name)._set_xml_obj(doc)
    

class Repository(object):
    """Wrapper class around repository id (key), name, remote_url, and storage_base.
       Remote url is used to determine whether the repository type is 'remote' (proxy)
       or 'hosted'
       
       Provides parsed xml document (via objectify.fromstring(..)) and convenience
       methods for accessing repository configuration without knowing all of the xml
       structure.
    """
    def __init__(self, key_or_doc, name=None):
        if type(key_or_doc) is objectify.ObjectifiedElement:
            self.new=False
            self._set_xml_obj(key_or_doc)
        elif name is None:
            raise Exception('Invalid new repository; must supply key AND name (name is missing)')
        else:
            self.new = True
            self.xml = objectify.Element('repository')
            self.data = etree.SubElement(self.xml, 'data')
            self.data.id=key_or_doc
            self.data.name=name
            self.data.repoType = 'hosted'
            self.data.writePolicy = WRITE_POLICIES.read_write
            self.data.exposed = 'true'
            self.data.browseable = 'true'
            self.data.indexable = 'true'
            self.data.downloadRemoteIndexes = 'false'
            self.data.provider = 'maven2'
            self.data.format = 'maven2'
            self.data.providerRole='org.sonatype.nexus.proxy.repository.Repository'
            self.data.checksumPolicy = CHECKSUM_POLICIES.warn
            self.data.repoPolicy = REPO_POLICIES.release

    def __str__(self):
        return "Repository: %s" % self.data.id

    def __repr__(self):
        return self.__str__();
    
    def _set_xml_string(self, xml):
        self.xml = objectify.fromstring(xml)
        self.data = self.xml.data
        self.new = False
        
        self._backup_xml = self.render()
        return self
    
    def _set_xml_obj(self, xml_obj):
        self.xml = xml_obj
        self.data = self.xml.data
        self.new = False
        
        self._backup_xml = self.render()
        return self
        
    def set_hosted(self, storage_location=None):
        self.data.repoType = REPO_TYPES.hosted
        
        if hasattr(self.data, 'remoteStorage'):
            self.data.remove(self.data.remoteStorage)
        
        if storage_location is not None:
            value = storage_location
            if not value.startswith('file:'):
                value = "file:" + value
            
            self.data.overrideLocalStorageUrl = value

        return self
    
    def set_remote(self, url):
        if hasattr(self.data, 'remoteStorage'):
            self.data.remove(self.data.remoteStorage)
            
        self.set('remoteStorage/remoteStorageUrl', url)
        self.data.repoType = REPO_TYPES.remote
        
        if hasattr(self.data, 'overrideLocalStorageUrl'):
            self.data.remove(self.data.overrideLocalStorageUrl)

        return self
    
    def set_exposed(self, exposed):
        self.data.exposed = exposed
        return self
    
    def set_browseable(self, browse):
        self.data.browseable = browse
        return self
    
    def set_indexable(self, index):
        self.data.indexable = index
        return self
    
    def set_download_remote_indexes(self, download):
        self.data.downloadRemoteIndexes = download
        return self
    
    def set_write_policy(self, policy):
        if not policy in WRITE_POLICIES.values():
            raise Exception("Invalid writePolicy: %s" % policy)
        
        self.data.writePolicy = policy
        return self
    
    def set_repo_policy(self, policy):
        if not policy in REPO_POLICIES.values():
            raise Exception("Invalid repoPolicy: %s" % policy)
        
        self.data.repoPolicy = policy
        return self
    
    def set_checksum_policy(self, policy):
        if not policy in CHECKSUM_POLICIES.values():
            raise Exception("Invalid checksumPolicy: %s" % policy)
        
        self.data.checksumPolicy = policy
        return self
    
    def set_nfc_ttl(self, ttl=1440):
        self.data.notFoundCacheTTL = str(ttl)
        return self
    
    def set(self, path, value=None):
        element = self.data
        print(path.split('/'))
        for part in path.split('/'):
            print("Creating: %s" % part)
            if len(part) > 0:
                element = etree.SubElement(element, part)
                print("New element: %s" % element.tag)
        
        if element.tag == self.data.tag:
            raise Exception( "You must specify at least one sub-element!")
    
        if value is not None:
            element._setText(value)
        
        return self
    
    def render(self, pretty_print=True):
        objectify.deannotate(self.xml, xsi_nil=True)
        etree.cleanup_namespaces(self.xml)
        return etree.tostring(self.xml, pretty_print=pretty_print, encoding="unicode")
    
    def content_uri(self):
        if self.xml is not None:
            return self.xml.data.contentResourceURI
        else:
            return None
    
    def name(self):
        if self.xml is not None:
            return self.xml.data.name.text
        else:
            return None
    
    def id(self):
        if self.xml is not None:
            return self.xml.data.id.text
        else:
            return None
    
    def save(self, session):
        """Create the specified Nexus repository, after setting the id (key) and repo name.
           If remote_url is specified, then the resulting repository will be a proxy/remote
           to some upstream.
           If storage_base is used, then the override storage location will be specified
           to direct Nexus to use a custom location for storing artifacts.
        """
        xml = self.render()
        if hasattr(self, '_backup_xml') and xml == self._backup_xml:
            if session.debug:
                print("No changes to repository: %s. Skipping save." % self.data.id)
            return self
        
        if self.new:
            if session.debug:
                print("Saving to: %s\n\n%s\n\n" % (REPOS_PATH, xml))
                
            _response, xml = session.post(REPOS_PATH, self.render())
        else:
            path = NAMED_REPO_PATH.format(key=self.data.id)
            if session.debug:
                print("Saving to: %s\n\n%s\n\n" % (path, xml))
                
            _response, xml = session.put(path, self.render())
        
        self._set_xml_string(xml)
        return self
