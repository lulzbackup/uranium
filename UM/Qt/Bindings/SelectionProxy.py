# Copyright (c) 2015 Ultimaker B.V.
# Uranium is released under the terms of the AGPLv3 or higher.

from PyQt5.QtCore import QObject, pyqtSignal, pyqtProperty, pyqtSlot

from UM.Application import Application
from UM.Scene.Selection import Selection

class SelectionProxy(QObject):
    def __init__(self, parent = None):
        super().__init__(parent)
        Selection.selectionChanged.connect(self._onSelectionChanged)

    selectionChanged = pyqtSignal()
    
    @pyqtProperty(bool, notify = selectionChanged)
    def hasSelection(self):
        return Selection.hasSelection()

    def _onSelectionChanged(self):
        self.selectionChanged.emit()

    @pyqtProperty(int, notify = selectionChanged)
    def count(self):
        return Selection.getCount()

    @pyqtProperty(str, notify = selectionChanged)
    def selectionName(self):
        return Selection.getSelectedObject(0).getName()

def createSelectionProxy(engine, script_engine):
    return SelectionProxy()
