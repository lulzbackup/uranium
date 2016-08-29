# Copyright (c) 2015 Ultimaker B.V.
# Uranium is released under the terms of the AGPLv3 or higher.

from . import SceneNode

from UM.Application import Application
from UM.Logger import Logger
from UM.Resources import Resources
from UM.Math.Vector import Vector
from UM.Job import Job
from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Scene.ToolHandle import ToolHandle

from UM.View.GL.OpenGL import OpenGL


##  Platform is a special case of Scene node. It renders a specific model as the platform of the machine.
#   A specialised class is used due to the differences in how it needs to rendered and the fact that a platform
#   can have a Texture.
#   It also handles the re-loading of the mesh when the active machine is changed.
class Platform(SceneNode.SceneNode):
    def __init__(self, parent):
        super().__init__(parent)

        self._load_platform_job = None
        self._shader = None
        self._axis_shader = None
        self._has_bed = False
        self._texture = None
        self._global_container_stack = None
        Application.getInstance().globalContainerStackChanged.connect(self._onGlobalContainerStackChanged)
        self._onGlobalContainerStackChanged()
        self.setCalculateBoundingBox(False)

    def render(self, renderer):
        if not self._shader:
            self._shader = OpenGL.getInstance().createShaderProgram(Resources.getPath(Resources.Shaders, "platform.shader"))
            if self._texture:
                self._shader.setTexture(0, self._texture)
            else:
                self._updateTexture()
        if not self._axis_shader:
            self._axis_shader = OpenGL.getInstance().createShaderProgram(Resources.getPath(Resources.Shaders, "platform_axis_block.shader"))

        if self.getMeshData():
            if self._has_bed:
                renderer.queueNode(self, shader=self._shader, transparent = True, backface_cull = True, sort = -10)
            else:
                renderer.queueNode(self, shader=self._axis_shader, transparent=False, backface_cull=True, sort=-10)
            return True

    def _onGlobalContainerStackChanged(self):
        if self._global_container_stack:
            self.setMeshData(None)

        self._global_container_stack = Application.getInstance().getGlobalContainerStack()
        if self._global_container_stack:
            container = self._global_container_stack.findContainer({ "platform": "*" })
            if container:
                mesh_file = container.getMetaDataEntry("platform")
                path = Resources.getPath(Resources.Meshes, mesh_file)

                if self._load_platform_job:
                    # This prevents a previous load job from triggering texture loads.
                    self._load_platform_job.finished.disconnect(self._onPlatformLoaded)

                # Perform platform mesh loading in the background
                self._load_platform_job = _LoadPlatformJob(path)
                self._load_platform_job.finished.connect(self._onPlatformLoaded)
                self._load_platform_job.start()

                self._has_bed = True

                offset = container.getMetaDataEntry("platform_offset")
                if offset:
                    if len(offset) == 3:
                        self.setPosition(Vector(offset[0], offset[1], offset[2]))
                    else:
                        Logger.log("w", "Platform offset is invalid: %s", str(offset))
                        self.setPosition(Vector(0.0, 0.0, 0.0))
                else:
                    self.setPosition(Vector(0.0, 0.0, 0.0))
            else:
                settings = Application.getInstance().getGlobalContainerStack()
                machine_width = settings.getProperty("machine_width", "value")
                machine_depth = settings.getProperty("machine_depth", "value")
                line_len = 25
                line_wid = 1
                handle_size = 3
                mb = MeshBuilder()

                mb.addCube(line_wid, line_len, line_wid, Vector(-machine_width/2, line_len/2, machine_depth/2), ToolHandle.YAxisColor)
                mb.addPyramid(handle_size, handle_size, handle_size, center=Vector(-machine_width/2, line_len, machine_depth/2), color=ToolHandle.YAxisColor)

                mb.addCube(line_len, line_wid, line_wid, Vector(line_len/2-machine_width/2, 0, machine_depth/2), ToolHandle.XAxisColor)
                mb.addPyramid(handle_size, handle_size, handle_size, center=Vector(line_len-machine_width/2, 0, machine_depth/2), color=ToolHandle.XAxisColor, axis = Vector.Unit_Z, angle = 90)

                mb.addCube(line_wid, line_wid, line_len, Vector(-machine_width/2, 0, -line_len/2+machine_depth/2), ToolHandle.ZAxisColor)
                mb.addPyramid(handle_size, handle_size, handle_size, center=Vector(-machine_width/2, 0, -line_len+machine_depth/2), color=ToolHandle.ZAxisColor, axis = Vector.Unit_X, angle = 90)

                self.setMeshData(mb.build())
                self.setPosition(Vector(0.0, 0.0, 0.0))
                self._has_bed = False

    def _updateTexture(self):
        if not self._global_container_stack or not OpenGL.getInstance():
            return

        container = self._global_container_stack.findContainer({"platform_texture":"*"})
        if container:
            texture_file = container.getMetaDataEntry("platform_texture")
            if texture_file:
                self._texture = OpenGL.getInstance().createTexture()
                self._texture.load(Resources.getPath(Resources.Images, texture_file))

                if self._shader:
                    self._shader.setTexture(0, self._texture)
        else:
            self._texture = None
            if self._shader:
                self._shader.setTexture(0, None)

    def _onPlatformLoaded(self, job):
        self._load_platform_job = None

        if not job.getResult():
            self.setMeshData(None)
            return

        node = job.getResult()
        if node.getMeshData():
            self.setMeshData(node.getMeshData())

            # Calling later because for some reason the OpenGL context might be outdated on some computers.
            Application.getInstance().callLater(self._updateTexture)


##  Protected class that ensures that the mesh for the machine platform is loaded.
class _LoadPlatformJob(Job):
    def __init__(self, file_name):
        self._file_name = file_name
        self._mesh_handler = Application.getInstance().getMeshFileHandler()

    def run(self):
        reader = self._mesh_handler.getReaderForFile(self._file_name)
        if not reader:
            self.setResult(None)
            return

        self.setResult(reader.read(self._file_name))
