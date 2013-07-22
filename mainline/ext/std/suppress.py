#
#    Metrix++, Copyright 2009-2013, Metrix++ Project
#    Link: http://metrixplusplus.sourceforge.net
#    
#    This file is a part of Metrix++ Tool.
#    
#    Metrix++ is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3 of the License.
#    
#    Metrix++ is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#    
#    You should have received a copy of the GNU General Public License
#    along with Metrix++.  If not, see <http://www.gnu.org/licenses/>.
#

import core.api
import core.cout

import re

class Plugin(core.api.Plugin, core.api.Child, core.api.IConfigurable):
    
    def declare_configuration(self, parser):
        parser.add_option("--std.suppress", "--ss", action="store_true", default=False,
                         help="If set (True), suppression markers are collected from comments in code. "
                              "Suppressions are used by post-processing tools, like limit, to remove false-positive warnings. "
                              "Suppressions should be in the first comment block of a region (function/class/interface). "
                              "Format of suppressions: 'metrix++: suppress metric-name'. "
                              "For example: 'metrix++: suppress std.code.complexity:cyclomatic'. "
                              " [default: %default]")
    
    def configure(self, options):
        self.is_active = options.__dict__['std.suppress']
        
    def initialize(self):
        if self.is_active == True:
            # trigger version property set
            core.api.Plugin.initialize(self)
            namespace = self.get_plugin_loader().get_database_loader().create_namespace(self.get_name(), support_regions = True)
            namespace.add_field('count', int, non_zero=True)
            namespace.add_field('list', str)
            core.api.subscribe_by_parents_interface(core.api.ICode, self, 'callback')

    # suppress pattern
    pattern = re.compile(r'''metrix[+][+][:][ \t]+suppress[ \t]+([^ \t\r\n\*]+)''')

    def callback(self, parent, data, is_updated):
        is_updated = is_updated or self.is_updated
        if is_updated == True:
            text = data.get_content()
            for region in data.iterate_regions():
                count = 0
                list_text = ""
                last_comment_end = None
                for marker in data.iterate_markers(
                                filter_group = data.get_marker_types().COMMENT,
                                region_id = region.get_id(),
                                exclude_children = True):
                    
                    if last_comment_end != None and marker.get_offset_begin() > last_comment_end + 2:
                        # check continues comment blocks
                        # stop searching, if this comment block is far from the last
                        break
                    last_comment_end = marker.get_offset_end()
                    
                    matches = self.pattern.findall(text, marker.get_offset_begin(), marker.get_offset_end())
                    for m in matches:
                        namespace_name, field = m.split(':')
                        namespace = self.get_plugin_loader().get_database_loader().get_namespace(namespace_name)
                        if namespace == None or namespace.get_field_packager(field) == None:
                            core.cout.notify(data.get_path(), region.get_cursor(),
                                                  core.cout.SEVERITY_WARNING,
                                                  "Suppressed metric '" + namespace_name + ":" + field +
                                                    "' is not being collected",
                                                  [("Metric name", namespace_name + ":" + field),
                                                   ("Region name", region.get_name())])
                            continue 
                        count += 1
                        list_text += "[" + m +"]"

                    if count > 0:
                        region.set_data(self.get_name(), 'count', count)
                        region.set_data(self.get_name(), 'list', list_text)

