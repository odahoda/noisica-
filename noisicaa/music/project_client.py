#!/usr/bin/python3

import asyncio
import logging

from noisicaa import core
from noisicaa.core import ipc

from . import mutations
from . import model

logger = logging.getLogger(__name__)


# TODO: merge with other one
class ObjectNotAttachedError(Exception):
    pass


class ObjectList(object):
    def __init__(self, prop_name, instance):
        self._prop_name = prop_name
        self._instance = instance
        self._objs = []

    def __len__(self):
        return len(self._objs)

    def __getitem__(self, idx):
        return self._objs[idx]

    def __setitem__(self, idx, obj):
        self.__delitem__(idx)
        self.insert(idx, obj)

    def __delitem__(self, idx):
        self._objs[idx].detach()
        self._objs[idx].clear_parent_container()
        del self._objs[idx]
        for i in range(idx, len(self._objs)):
            self._objs[i].set_index(i)
        self._instance.listeners.call(self._prop_name, 'delete', idx)

    def append(self, obj):
        self.insert(len(self._objs), obj)

    def insert(self, idx, obj):
        obj.attach(self._instance)
        obj.set_parent_container(self)
        self._objs.insert(idx, obj)
        for i in range(idx, len(self._objs)):
            self._objs[i].set_index(i)
        self._instance.listeners.call(self._prop_name, 'insert', idx, obj)

    def clear(self):
        for obj in self._objs:
            obj.detach()
            obj.clear_parent_container()
        self._objs.clear()
        self._instance.listeners.call(self._prop_name, 'clear')


class ObjectProxy(core.ObjectBase):
    def __init__(self, obj_id):
        super().__init__()
        self.state['id'] = obj_id
        self.listeners = core.CallbackRegistry()

    def property_changed(self, change):
        if isinstance(change, core.PropertyValueChange):
            self.listeners.call(
                change.prop_name, change.old_value, change.new_value)

        elif isinstance(change, core.PropertyListInsert):
            self.listeners.call(
                change.prop_name, 'insert',
                change.index, change.new_value)

        elif isinstance(change, core.PropertyListDelete):
            self.listeners.call(
                change.prop_name, 'delete', change.index)

        elif isinstance(change, core.PropertyListClear):
            self.listeners.call(change.prop_name, 'clear')

        else:
            raise TypeError("Unsupported change type %s" % type(change))



class Measure(model.Measure, ObjectProxy): pass
class Track(model.Track, ObjectProxy): pass
class Note(model.Note, ObjectProxy): pass
class ScoreMeasure(model.ScoreMeasure, ObjectProxy): pass
class ScoreTrack(model.ScoreTrack, ObjectProxy): pass
class SheetPropertyMeasure(model.SheetPropertyMeasure, ObjectProxy): pass
class SheetPropertyTrack(model.SheetPropertyTrack, ObjectProxy): pass
class Sheet(model.Sheet, ObjectProxy): pass
class Metadata(model.Metadata, ObjectProxy): pass
class Project(model.Project, ObjectProxy): pass

cls_map = {
    'Measure': Measure,
    'Track': Track,
    'Note': Note,
    'ScoreMeasure': ScoreMeasure,
    'ScoreTrack': ScoreTrack,
    'SheetPropertyMeasure': SheetPropertyMeasure,
    'SheetPropertyTrack': SheetPropertyTrack,
    'Sheet': Sheet,
    'Metadata': Metadata,
    'Project': Project,
    }

class ProjectClientBase(object):
    def __init__(self, event_loop):
        super().__init__()
        self.event_loop = event_loop
        self.server = ipc.Server(self.event_loop, 'client')

    async def setup(self):
        await self.server.setup()

    async def cleanup(self):
        await self.server.cleanup()



class ProjectClientMixin(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stub = None
        self._session_id = None
        self._object_map = {}
        self.project = None

    def __set_project(self, root_id):
        assert self.project is None
        self.project = self._object_map[root_id]
        self.project.is_root = True

    async def setup(self):
        await super().setup()
        self.server.add_command_handler(
            'PROJECT_MUTATION', self.handle_project_mutation)
        self.server.add_command_handler(
            'PROJECT_CLOSED', self.handle_project_closed)

    async def connect(self, address):
        assert self._stub is None
        self._stub = ipc.Stub(self.event_loop, address)
        await self._stub.connect()
        self._session_id, root_id = await self._stub.call(
            'START_SESSION', self.server.address)
        if root_id is not None:
            # Connected to a loaded project.
            self.__set_project(root_id)

    async def disconnect(self):
        if self._session_id is not None:
            await self._stub.call('END_SESSION', self._session_id)
            self._session_id = None

        if self._stub is not None:
            await self._stub.close()
            self._stub = None

    def apply_properties(self, obj, properties):
        for prop_name, prop_type, value in properties:
            if prop_type == 'scalar':
                setattr(obj, prop_name, value)

            elif prop_type == 'list':
                lst = getattr(obj, prop_name)
                lst.clear()
                lst.extend(value)

            elif prop_type == 'obj':
                child = None
                if value is not None:
                    child = self._object_map[value]
                setattr(obj, prop_name, child)

            elif prop_type == 'objlist':
                lst = getattr(obj, prop_name)
                lst.clear()
                for child_id in value:
                    child = self._object_map[child_id]
                    lst.append(child)

            else:
                raise ValueError(
                    "Property type %s not supported." % prop_type)

    def handle_project_mutation(self, mutation):
        logger.info("Mutation received: %s" % mutation)
        try:
            if isinstance(mutation, mutations.SetProperties):
                obj = self._object_map[mutation.id]
                self.apply_properties(obj, mutation.properties)

            elif isinstance(mutation, mutations.AddObject):
                cls = cls_map[mutation.cls]
                obj = cls(mutation.id)
                self.apply_properties(obj, mutation.properties)
                self._object_map[mutation.id] = obj

            elif isinstance(mutation, mutations.UpdateObjectList):
                obj = self._object_map[mutation.id]
                lst = getattr(obj, mutation.prop_name)
                if mutation.args[0] == 'insert':
                    idx, child_id = mutation.args[1:]
                    child = self._object_map[child_id]
                    lst.insert(idx, child)
                elif mutation.args[0] == 'delete':
                    idx, = mutation.args[1:]
                    child = lst[idx]
                    del lst[idx]
                    # TODO: delete tree under child
                elif mutation.args[0] == 'clear':
                    lst.clear()
                else:
                    raise ValueError(mutation.args[0])

            elif isinstance(mutation, mutations.UpdateList):
                obj = self._object_map[mutation.id]
                lst = getattr(obj, mutation.prop_name)
                if mutation.args[0] == 'insert':
                    idx, value = mutation.args[1:]
                    lst.insert(idx, value)
                elif mutation.args[0] == 'delete':
                    idx, = mutation.args[1:]
                    del lst[idx]
                elif mutation.args[0] == 'clear':
                    lst.clear()
                else:
                    raise ValueError(mutation.args[0])

            else:
                raise ValueError("Unknown mutation %s received." % mutation)
        except Exception as exc:
            logger.exception("Handling of mutation %s failed:", mutation)

    def handle_project_closed(self):
        logger.info("Project closed received.")

    async def shutdown(self):
        await self._stub.call('SHUTDOWN')

    async def test(self):
        await self._stub.call('TEST')

    async def create(self, path):
        assert self.project is None
        root_id = await self._stub.call('CREATE', path)
        self.__set_project(root_id)

    async def create_inmemory(self):
        assert self.project is None
        root_id = await self._stub.call('CREATE_INMEMORY')
        self.__set_project(root_id)

    async def open(self, path):
        assert self.project is None
        root_id = await self._stub.call('OPEN', path)
        self.__set_project(root_id)

    async def close(self):
        assert self.project is not None
        await self._stub.call('CLOSE')
        self.project = None
        self._object_map.clear()

    async def send_command(self, target, command, **kwargs):
        assert self.project is not None
        result = await self._stub.call('COMMAND', target, command, kwargs)
        logger.info("Command %s completed with result=%r", command, result)
        return result

class ProjectClient(ProjectClientMixin, ProjectClientBase):
    pass
