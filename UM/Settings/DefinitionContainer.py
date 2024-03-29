# Copyright (c) 2017 Ultimaker B.V.
# Uranium is released under the terms of the LGPLv3 or higher.

import json
import collections
import copy

from PyQt5.QtCore import QObject, pyqtProperty

from UM.Resources import Resources
from UM.PluginObject import PluginObject
from UM.Logger import Logger
from UM.MimeTypeDatabase import MimeTypeDatabase, MimeType
from UM.Signal import Signal

from UM.Settings.Interfaces import DefinitionContainerInterface
from UM.Settings.SettingDefinition import SettingDefinition
from UM.Settings.SettingDefinition import DefinitionPropertyType
from UM.Settings.SettingRelation import SettingRelation
from UM.Settings.SettingRelation import RelationType
from UM.Settings.SettingFunction import SettingFunction

from typing import Dict, Any, List, Optional

class InvalidDefinitionError(Exception):
    pass


class IncorrectDefinitionVersionError(Exception):
    pass


class InvalidOverrideError(Exception):
    pass

MimeTypeDatabase.addMimeType(
    MimeType(
        name = "application/x-uranium-definitioncontainer",
        comment = "Uranium Definition Container",
        suffixes = ["def.json"]
    )
)


##  A container for SettingDefinition objects.
#
#
class DefinitionContainer(QObject, DefinitionContainerInterface, PluginObject):
    Version = 2

    ##  Constructor
    #
    #   \param container_id A unique, machine readable/writable ID for this container.
    def __init__(self, container_id: str, i18n_catalog = None, *args, **kwargs):
        # Note that we explicitly pass None as QObject parent here. This is to be able
        # to support pickling.
        super().__init__(parent = None, *args, **kwargs)

        self._metadata = {"id": container_id,
                          "name": container_id,
                          "container_type": DefinitionContainer,
                          "version": self.Version} # type: Dict[str, Any]
        self._definitions = []                     # type: List[SettingDefinition]
        self._inherited_files = []                 # type: List[str]
        self._i18n_catalog = i18n_catalog

        self._definition_cache = {}                # type: Dict[str, SettingDefinition]
        self._path = ""

    ##  Reimplement __setattr__ so we can make sure the definition remains unchanged after creation.
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        #raise NotImplementedError()

    ##  For pickle support
    def __getnewargs__(self):
        return (self.getId(), self._i18n_catalog)

    ##  For pickle support
    def __getstate__(self):
        return self.__dict__

    ##  For pickle support
    def __setstate__(self, state):
        # We need to call QObject.__init__() in order to initialize the underlying C++ object.
        # pickle doesn't do that so we have to do this here.
        QObject.__init__(self, parent = None)
        self.__dict__.update(state)

    ##  \copydoc ContainerInterface::getId
    #
    #   Reimplemented from ContainerInterface
    def getId(self) -> str:
        return self._metadata["id"]

    id = pyqtProperty(str, fget = getId, constant = True)

    ##  \copydoc ContainerInterface::getName
    #
    #   Reimplemented from ContainerInterface
    def getName(self) -> str:
        return self._metadata["name"]

    name = pyqtProperty(str, fget = getName, constant = True)

    ##  \copydoc ContainerInterface::isReadOnly
    #
    #   Reimplemented from ContainerInterface
    def isReadOnly(self) -> bool:
        return True

    def setReadOnly(self, read_only: bool) -> None:
        pass

    readOnly = pyqtProperty(bool, fget = isReadOnly, constant = True)

    ##  \copydoc ContainerInterface::getPath.
    #
    #   Reimplemented from ContainerInterface
    def getPath(self):
        return self._path

    ##  \copydoc ContainerInterface::setPath
    #
    #   Reimplemented from ContainerInterface
    def setPath(self, path):
        self._path = path

    ##  \copydoc ContainerInterface::getMetaData
    #
    #   Reimplemented from ContainerInterface
    def getMetaData(self):
        return self._metadata

    metaData = pyqtProperty("QVariantMap", fget = getMetaData, constant = True)

    @property
    def definitions(self):
        return self._definitions

    ##  Gets all ancestors of this definition container.
    #
    #   This returns the definition in the "inherits" property of this
    #   container, and the definition in its "inherits" property, and so on. The
    #   ancestors are returned in order from parent to
    #   grand-grand-grand-...-grandparent, normally ending in a "root"
    #   container.
    #
    #   \return A list of ancestors, in order from near ancestor to the root.
    def getInheritedFiles(self):
        return self._inherited_files

    ##  Gets all keys of settings in this container.
    #
    #   \return A set of all keys of settings in this container.
    def getAllKeys(self) -> List[str]:
        keys = set()
        for definition in self.definitions:
            keys |= definition.getAllKeys()
        return keys

    ##  \copydoc ContainerInterface::getMetaDataEntry
    #
    #   Reimplemented from ContainerInterface
    def getMetaDataEntry(self, entry, default = None):
        return self._metadata.get(entry, default)

    ##  \copydoc ContainerInterface::getProperty
    #
    #   Reimplemented from ContainerInterface.
    def getProperty(self, key, property_name, context = None):
        definition = self._getDefinition(key)
        if not definition:
            return None

        try:
            value = getattr(definition, property_name)
            if value is None and property_name == "value":
                value = getattr(definition, "default_value")
                if key in ["machine_start_gcode", "machine_end_gcode", "machine_wipe_gcode","machine_abort_gcode", "machine_level_x_axis_gcode",
                           "machine_extruder_start_code", "machine_extruder_end_code"]:
                    value_from_file = getattr(definition, "default_value_from_file")
                    if value_from_file != None:
                        try:
                            path = Resources.getPath(Resources.GCodes, value_from_file + ".gcode")
                            with open(path, encoding = "utf-8") as f:
                                value = f.read()
                        except FileNotFoundError:
                            return None
            return value
        except AttributeError:
            return None

    ##  \copydoc ContainerInterface::hasProperty
    #
    #   Reimplemented from ContainerInterface
    def hasProperty(self, key, property_name, ignore_inherited: bool = False):
        definition = self._getDefinition(key)
        if not definition:
            return False
        if definition.parent is not None and ignore_inherited:
            return False
        return hasattr(definition, property_name)

    ##  This signal is unused since the definition container is immutable, but is provided for API consistency.
    propertyChanged = Signal()

    metaDataChanged = Signal()

    ##  \copydoc ContainerInterface::serialize
    #
    #   TODO: This implementation flattens the definition container, since the
    #   data about inheritance and overrides was lost when deserialising.
    #
    #   Reimplemented from ContainerInterface
    def serialize(self, ignored_metadata_keys: Optional[set] = None):
        data = { } # The data to write to a JSON file.
        data["name"] = self.getName()
        data["version"] = DefinitionContainer.Version
        data["metadata"] = self.getMetaData().copy()

        # remove the keys that we want to ignore in the metadata
        if not ignored_metadata_keys:
            ignored_metadata_keys = set()
        ignored_metadata_keys |= {"name", "version", "id", "container_type"}
        for key in ignored_metadata_keys:
            if key in data["metadata"]:
                del data["metadata"][key]

        data["settings"] = { }
        for definition in self.definitions:
            data["settings"][definition.key] = definition.serialize_to_dict()

        return json.dumps(data, separators = (", ", ": "), indent = 4) # Pretty print the JSON.

    @classmethod
    def getConfigurationTypeFromSerialized(cls, serialized: str) -> Optional[str]:
        configuration_type = None
        try:
            parsed = json.loads(serialized, object_pairs_hook = collections.OrderedDict)
            configuration_type = parsed["metadata"].get("type", "machine") #TODO: Not all definitions have a type. They get this via inheritance but that requires an instance.
        except Exception as e:
            Logger.log("d", "Could not get configuration type: %s", e)
        return configuration_type

    def _readAndValidateSerialized(self, serialized: str) -> dict:
        parsed = json.loads(serialized, object_pairs_hook = collections.OrderedDict)

        if "inherits" in parsed:
            inherited = self._resolveInheritance(parsed["inherits"])
            parsed = self._mergeDicts(inherited, parsed)

        self._verifyJson(parsed)

        parsed = self._preprocessParsedJson(parsed)
        return parsed

    @classmethod
    def getVersionFromSerialized(cls, serialized: str) -> Optional[int]:
        version = None
        parsed = json.loads(serialized, object_pairs_hook = collections.OrderedDict)
        try:
            version = int(parsed["version"])
        except Exception as e:
            Logger.log("d", "Could not get version from serialized: %s", e)
        return version

    def _preprocessParsedJson(self, parsed):
        # Pre-process the JSON data to include the overrides.
        if "overrides" in parsed:
            for key, value in parsed["overrides"].items():
                setting = self._findInDict(parsed["settings"], key)
                if setting is None:
                    Logger.log("w","Unable to override setting %s", key)
                else:
                    setting.update(value)

        return parsed

    ##  Add a setting definition instance if it doesn't exist yet.
    #
    #   Warning: this might not work when there are relationships higher up in the stack.
    def addDefinition(self, definition: SettingDefinition):
        if definition.key not in [d.key for d in self._definitions]:
            self._definitions.append(definition)
            self._updateRelations(definition)

    ##  \copydoc ContainerInterface::deserialize
    #
    #   Reimplemented from ContainerInterface
    def deserialize(self, serialized, file_name: Optional[str] = None) -> str:
        # update the serialized data first
        serialized = super().deserialize(serialized, file_name)
        parsed = self._readAndValidateSerialized(serialized)

        # Update properties with the data from the JSON
        old_id = self.getId() #The ID must be set via the constructor. Retain it.
        self._metadata = parsed["metadata"]
        self._metadata["id"] = old_id
        self._metadata["name"] = parsed["name"]
        self._metadata["version"] = self.Version #Guaranteed to be equal to what's in the parsed data by the validation.
        self._metadata["container_type"] = DefinitionContainer

        for key, value in parsed["settings"].items():
            definition = SettingDefinition(key, self, None, self._i18n_catalog)
            definition.deserialize(value)
            self._definitions.append(definition)

        for definition in self._definitions:
            self._updateRelations(definition)

        return serialized

    ##  Gets the metadata of a definition container from a serialised format.
    #
    #   This parses the entire JSON document and only extracts the metadata from
    #   it.
    #
    #   \param serialized A JSON document, serialised as a string.
    #   \param container_id The ID of the container (as obtained from the file
    #   name).
    #   \return A dictionary of metadata that was in the JSON document in a
    #   singleton list. If anything went wrong, the list will be empty.
    @classmethod
    def deserializeMetadata(cls, serialized: str, container_id: str) -> List[Dict[str, Any]]:
        serialized = cls._updateSerialized(serialized) #Update to most recent version.
        try:
            parsed = json.loads(serialized, object_pairs_hook = collections.OrderedDict) #TODO: Load only part of this JSON until we find the metadata. We need an external library for this though.
        except json.JSONDecodeError as e:
            Logger.log("d", "Could not parse definition: %s", e)
            return []
        metadata = {}
        if "inherits" in parsed:
            import UM.Settings.ContainerRegistry #To find the definitions we're inheriting from.
            parent_metadata = UM.Settings.ContainerRegistry.ContainerRegistry.getInstance().findDefinitionContainersMetadata(id = parsed["inherits"])
            if not parent_metadata:
                Logger.log("e", "Could not load parent definition container {parent} of child {child}".format(parent = parsed["inherits"], child = container_id))
                #Ignore the parent then.
            else:
                parent_metadata = parent_metadata[0]
                metadata.update(parent_metadata)
                metadata["inherits"] = parsed["inherits"]

        metadata["container_type"] = DefinitionContainer
        metadata["id"] = container_id
        try: #Move required fields to metadata.
            metadata["name"] = parsed["name"]
            metadata["version"] = parsed["version"]
        except KeyError: #Required fields not present!
            return []
        if "metadata" in parsed:
            metadata.update(parsed["metadata"])
        return [metadata]

    ##  Find definitions matching certain criteria.
    #
    #   \param kwargs \type{dict} A dictionary of keyword arguments containing key-value pairs which should match properties of the definition.
    def findDefinitions(self, **kwargs) -> List[SettingDefinition]:
        if len(kwargs) == 1 and "key" in kwargs:
            # If we are searching for a single definition by exact key, we can speed up things by retrieving from the cache.
            key = kwargs.get("key")
            if key in self._definition_cache:
                return [self._definition_cache[key]]

        definitions = []
        for definition in self._definitions:
            definitions.extend(definition.findDefinitions(**kwargs))

        return definitions

    @classmethod
    def getLoadingPriority(cls) -> int:
        return 0

    # protected:

    # Load a file from disk, used to handle inheritance and includes
    def _loadFile(self, file_name: str) -> dict:
        path = Resources.getPath(Resources.DefinitionContainers, file_name + ".def.json")
        with open(path, encoding = "utf-8") as f:
            try:
                contents = json.load(f, object_pairs_hook=collections.OrderedDict)
            except json.JSONDecodeError as e:
                Logger.log("e", "Error while loading file %s %s:%s %s" % (file_name, e.lineno, e.colno, e.msg))

        self._inherited_files.append(path)
        return contents

    # Recursively resolve loading inherited files
    def _resolveInheritance(self, file_name: str) -> dict:
        json_dict = self._loadFile(file_name)

        if "inherits" in json_dict:
            inherited = self._resolveInheritance(json_dict["inherits"])
            json_dict = self._mergeDicts(inherited, json_dict)

        self._verifyJson(json_dict)

        return json_dict

    # Verify that a loaded json matches our basic expectations.
    def _verifyJson(cls, json_dict: Dict[str, Any]):
        required_fields = {"version", "name", "settings", "metadata"}
        missing_fields = required_fields - json_dict.keys()
        if missing_fields:
            raise InvalidDefinitionError("Missing required properties: {properties}".format(properties = ", ".join(missing_fields)))

        if json_dict["version"] != cls.Version:
            raise IncorrectDefinitionVersionError("Definition uses version {0} but expected version {1}".format(json_dict["version"], cls.Version))

    # Recursively find a key in a dictionary
    def _findInDict(self, dictionary: dict, key: str):
        if key in dictionary: return dictionary[key]
        for k, v in dictionary.items():
            if isinstance(v, dict):
                item = self._findInDict(v, key)
                if item is not None:
                    return item

    # Recursively merge two dictionaries, returning a new dictionary
    def _mergeDicts(self, first: dict, second: dict):
        result = copy.deepcopy(first)
        for key, value in second.items():
            if key in result:
                if isinstance(value, dict):
                    result[key] = self._mergeDicts(result[key], value)
                else:
                    result[key] = value
            else:
                result[key] = value

        return result

    # Recursively update relations of settings
    def _updateRelations(self, definition: SettingDefinition):
        for property in SettingDefinition.getPropertyNames(DefinitionPropertyType.Function):
            self._processFunction(definition, property)

        for child in definition.children:
            self._updateRelations(child)

    # Create relation objects for all settings used by a certain function
    def _processFunction(self, definition: SettingDefinition, property: str):
        try:
            function = getattr(definition, property)
        except AttributeError:
            return

        if not isinstance(function, SettingFunction):
            return

        for setting in function.getUsedSettingKeys():
            # Prevent circular relations between the same setting and the same property
            # Note that the only property used by SettingFunction is the "value" property, which
            # is why this is hard coded here.
            if setting == definition.key and property == "value":
                Logger.log("w", "Found circular relation for property 'value' between {0} and {1}", definition.key, setting)
                continue

            other = self._getDefinition(setting)
            if not other:
                continue

            relation = SettingRelation(definition, other, RelationType.RequiresTarget, property)
            definition.relations.append(relation)

            relation = SettingRelation(other, definition, RelationType.RequiredByTarget, property)
            other.relations.append(relation)

    def _getDefinition(self, key: str) -> SettingDefinition:
        definition = None
        if key in self._definition_cache:
            definition = self._definition_cache[key]
        else:
            definitions = self.findDefinitions(key = key)
            if definitions:
                definition = definitions[0]
                self._definition_cache[key] = definition

        return definition

    ##  Simple short string representation for debugging purposes.
    def __str__(self):
        return "<DefinitionContainer '{definition_id}' ('{name}')>".format(definition_id = self.getId(), name = self.getName())