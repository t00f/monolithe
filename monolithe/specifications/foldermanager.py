# -*- coding: utf-8 -*-
#
# Copyright (c) 2015, Alcatel-Lucent Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its contributors
#       may be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json
import os
import ConfigParser

from .specification import Specification
from monolithe.lib import merge_dict

class FolderManager (object):
    """ RepositoryManager is an object that allows to manipulate the API specification repository
    """

    def __init__(self, folder, monolithe_config):
        """
        """
        self._monolithe_config = monolithe_config
        self._folder = folder;

    @property
    def folder(self):
        return self._folder

    def get_available_specifications(self):
        """ Returns the list of available specification files

            Args:
                branch: the branch where to find files (default: "master")

            Returns:
                list of all available specification files in the given branch
        """
        ret = []
        for filename in os.listdir(self._folder):
            if os.path.splitext(filename)[1] != ".spec" or filename.startswith("@"):
                continue
            ret.append(filename)
        return ret

    def get_api_info(self):
        """
        """
        with open("%s/api.info" % self._folder, "r") as f:
            try:
                return json.loads(f.read())
            except Exception as e:
                raise Exception("could not parse api.info", e)

    def get_monolithe_config(self, branch="master"):
        """
        """
        with open("%s/monolithe.ini" % self._folder, "r") as f:
            try:
                monolithe_config_parser = ConfigParser.ConfigParser()
                monolithe_config_parser.readfp(f)
                return monolithe_config_parser

            except Exception as e:
                raise Exception("could not parse monolithe.ini", e)

    def get_all_specifications(self):
        """
        """
        specifications = {}
        for name in self.get_available_specifications():
            specifications[name.replace(".spec", "")] = self.get_specification(name)
        return specifications

    def get_specification_data(self, name):
        """
        """
        data = {}
        with open("%s/%s" % (self._folder, name), "r") as f:
            try:
                data = json.loads(f.read())
                if "model" in data and "extends" in data["model"]:
                    for extension in data["model"]["extends"]:
                        data = merge_dict(data, self.get_specification_data(name="%s.spec" % extension))
            except Exception as e:
                raise Exception("Could not parse %s" % name, e)
        return data

    def get_specification(self, name):
        """
        """
        return Specification(filename=name, data=self.get_specification_data(name), monolithe_config=self._monolithe_config)

    def get_specifications(self, names, callback=None):
        """
        """
        specifications = []
        for name in names:
            specification.append(Specification(filename=name, data=self.get_specification_data(name=name)))
        return specifications