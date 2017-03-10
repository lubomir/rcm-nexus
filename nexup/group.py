# Copyright (c) 2014 Red Hat, Inc..
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#
# Utility methods for working with Nexus groups. Also includes Group
# class definition, which provides some convenience methods for
# accessing options associated with a group defintion.
#
# Authors:
#    John Casey (jcasey@redhat.com)

from lxml import (objectify,etree)
from session import (nexus_boolean, python_boolean)
import repo as repos
import os
import re

GROUP_CONTENT_URI_RE='(.+)/content/groups/.+'

GROUPS_PATH = '/service/local/repo_groups'
NAMED_GROUP_PATH = GROUPS_PATH + '/{key}'

def group_exists(session, group_key):
    return session.exists( NAMED_GROUP_PATH.format(key=group_key) )

def load(session, group_key, ignore_missing=True):
    """Load the specified group xml definition from nexus (for group_key).
       Return a Group instance.
    """
    path = NAMED_GROUP_PATH.format(key=group_key)
    response, group_xml = session.get(path, ignore_404=ignore_missing)
    
    if ignore_missing and response.status_code == 404:
#        print "Group %s not found. Returning None" % group_key
        return None
    
    doc = objectify.fromstring(group_xml)
    return Group(doc)

class Group(object):
    """Convenience wrapper class around group xml document (via objectify.fromstring(..)).
       Provides methods for accessing data without knowledge of the xml document structure.
    """
    def __init__(self, key_or_doc, name=None, debug=False):
        if type(key_or_doc) is objectify.ObjectifiedElement:
            self.new=False
            self._set_xml_obj(key_or_doc)
        elif name is None:
            raise Exception('Invalid new repository; must supply key AND name (name is missing)')
        else:
            self.new = True
            self.debug = debug
            self.xml = objectify.Element('repo-group')
            self.data = etree.SubElement(self.xml, 'data')
            self.data.id = key_or_doc
            self.data.name = name
            self.data.provider='maven2'
            self.data.format='maven2'
            self.data.repoType = 'group'
            self.data.exposed = nexus_boolean(True)
    
    def exposed(self):
        exposed = self.data.exposed
        pyval = python_boolean(exposed)
        if self.debug is True:
            print "Got group exposed value: %s (type: %s, converted to boolean: %s)" % (exposed, type(exposed), pyval)
        return pyval
    
    def set_exposed(self, exposed):
        # self.data.exposed = nexus_boolean(exposed)
        self.data.exposed = exposed
        return self
    
    def _set_xml_string(self, xml):
        self.xml = objectify.fromstring(xml)
        self.data = self.xml.data
        self.new=False
        
        #re-render to baseline using the objectify formatting engine, not whatever nexus sends back.
        self._backup_xml = self.render()
        return self
    
    def _set_xml_obj(self, xml):
        self.xml = xml
        self.data = self.xml.data
        self.new=False
        
        self._backup_xml = self.render()
        return self
    
    def name(self):
        return self.data.name
    
    def id(self):
        return self.data.id

    def content_uri(self):
        return self.data.contentResourceURI
    
    def set_name(self, name):
        self.data.name = name
        return self
    
    def append_member(self, session, repo_key):
        """Append the specified repository (key) as a member of this group.
           Before appending, validate that the repository isn't already a member, and that the
           repository actually exists.
        """
        if len(self.data.repositories) and self.data.repositories.getchildren() and len(self.data.repositories.getchildren()):
            for member in self.data.repositories['repo-group-member']:
                if member.id == repo_key:
                    return self
        
        repo = repos.load(session, repo_key, ignore_missing=True)
        if repo is not None:
            members = None
            try:
                if self.data.repositories.tag:
                    members = self.data.repositories
            except AttributeError:
                if session.debug:
                    print "No <repositories/> tag found. Will create it to append new member: %s" % repo_key
            
            if members is None:
                members = etree.SubElement(self.data, 'repositories')
            
            member = etree.SubElement(members, 'repo-group-member')
            member.id = repo.data.id
            member.name = repo.data.name
            print "Append: '%s' to group content URI: '%s'" % (repo.data.id, self.data.contentResourceURI)

            match = re.search(GROUP_CONTENT_URI_RE, str(self.content_uri()))
            base_url = match.group(1)

            repo_id = str(repo.data.id)

            resource_uri = "%s%s/%s" % (base_url, NAMED_GROUP_PATH.format(key=self.id()), repo_id)

            member.resourceURI = resource_uri
            
            if session.debug:
                print "Added member: %s" % repo_key
        
        return self
    
    def remove_member(self, session, repo_key):
        """Remove the specified repository (key) from the membership of this group.
        """
        if len(self.data.repositories) and self.data.repositories.getchildren() and len(self.data.repositories.getchildren()):
            for member in self.data.repositories["repo-group-member"]:
                if member.id == repo_key:
                    self.data.repositories.remove(member)
            
                    if session.debug:
                        print "Removed member: %s" % repo_key
        
        return self
    
    def render(self, pretty_print=True):
        objectify.deannotate(self.xml, xsi_nil=True)
        etree.cleanup_namespaces(self.xml)
        return etree.tostring(self.xml, pretty_print=pretty_print)
    
    def members(self):
        if len(self.data.repositories) and self.data.repositories.getchildren() and len(self.data.repositories.getchildren()):
            return self.xml.data.repositories["repo-group-member"]
        else:
            return 0
    
    def save(self, session):
        """Create (POST) or store (PUT) this group, then set self.new = False and update the embedded xml document/object tree.
        """
        xml = self.render()
        if hasattr(self, '_backup_xml') and xml == self._backup_xml:
            if session.debug:
                print "No changes to group: %s. Skipping save." % self.data.id
            return self
        
        if self.new:
            _response, xml = session.post(GROUPS_PATH, self.render())
        else:
            _response, xml = session.put(NAMED_GROUP_PATH.format(key=self.data.id), self.render())
        
        self._set_xml_string(xml)
        return self
