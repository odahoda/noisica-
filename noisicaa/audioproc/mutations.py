#!/usr/bin/python3

# @begin:license
#
# Copyright (c) 2015-2018, Benjamin Niemann <pink@odahoda.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# @end:license

# mypy: loose

from noisicaa import node_db


class Mutation(object):
    pass


class AddNode(Mutation):
    def __init__(self, *, description, **args):
        super().__init__()
        assert isinstance(description, node_db.NodeDescription)

        self.description = description
        self.args = args

    def __str__(self):
        return '<AddNode name="%s" type=%s%s>' % (
            self.description.display_name,
            type(self.description).__name__,
            ''.join(' %s=%r' % (k, v) for k, v in sorted(self.args.items())))


class RemoveNode(Mutation):
    def __init__(self, node_id):
        super().__init__()
        self.node_id = node_id

    def __str__(self):
        return '<RemoveNode id=%s>' % self.node_id


class ConnectPorts(Mutation):
    def __init__(self, src_node, src_port, dest_node, dest_port):
        super().__init__()
        self.src_node = src_node
        self.src_port = src_port
        self.dest_node = dest_node
        self.dest_port = dest_port

    def __str__(self):
        return '<ConnectPorts src=%s:%s dest=%s:%s>' % (
            self.src_node, self.src_port, self.dest_node, self.dest_port)


class DisconnectPorts(Mutation):
    def __init__(self, src_node, src_port, dest_node, dest_port):
        super().__init__()
        self.src_node = src_node
        self.src_port = src_port
        self.dest_node = dest_node
        self.dest_port = dest_port

    def __str__(self):
        return '<DisconnectPorts src=%s:%s dest=%s:%s>' % (
            self.src_node, self.src_port, self.dest_node, self.dest_port)


class SetPortProperty(Mutation):
    def __init__(self, node, port, **kwargs):
        super().__init__()
        self.node = node
        self.port = port
        self.kwargs = kwargs

    def __str__(self):
        return '<SetPortProperty port=%s:%s%s>' % (
            self.node, self.port,
            ''.join(' %s=%r' % (k, v)
                    for k, v in sorted(self.kwargs.items())))


class SetControlValue(Mutation):
    def __init__(self, name, value, generation):
        super().__init__()
        self.name = name
        self.value = value
        self.generation = generation

    def __str__(self):
        return '<SetControlValue name="%s" value=%s generation=%d>' % (
            self.name, self.value, self.generation)


class SetPluginState(Mutation):
    def __init__(self, node, state):
        super().__init__()
        self.node = node
        self.state = state

    def __str__(self):
        return '<SetPluginState node="%s" state=%s>' % (self.node, self.state)
