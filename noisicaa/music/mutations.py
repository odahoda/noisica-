#!/usr/bin/python3

import logging

from noisicaa import core

logger = logging.getLogger(__name__)


class Mutation(object):
    def _prop2tuple(self, obj, prop):
        value = getattr(obj, prop.name, None)
        if isinstance(prop, core.ObjectProperty):
            return (
                prop.name,
                'obj',
                value.id if value is not None else None)

        elif isinstance(prop, core.ObjectListProperty):
            return (
                prop.name,
                'objlist',
                [v.id for v in value])

        else:
            return (prop.name, 'scalar', value)


class SetProperties(Mutation):
    def __init__(self, obj, properties):
        self.id = obj.id
        self.properties = []
        for prop_name in properties:
            prop = obj.get_property(prop_name)
            self.properties.append(self._prop2tuple(obj, prop))

    def __str__(self):
        return '<SetProperties id="%s" %s>' % (
            self.id,
            ' '.join(
                '%s=%s:%r' % (p, t, v)
                for p, t, v in self.properties))


class AddObject(Mutation):
    def __init__(self, obj):
        self.id = obj.id
        self.cls = obj.__class__.__name__
        self.properties = []
        for prop in obj.list_properties():
            if prop.name == 'id':
                continue
            self.properties.append(self._prop2tuple(obj, prop))

    def __str__(self):
        return '<AddObject id="%s" cls="%s" %s>' % (
            self.id, self.cls,
            ' '.join(
                '%s=%s:%r' % (p, t, v)
                for p, t, v in self.properties))

