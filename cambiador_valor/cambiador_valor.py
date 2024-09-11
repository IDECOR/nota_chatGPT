from qgis.PyQt import QtWidgets, QtGui, QtCore
from qgis.core import QgsProject, QgsFeature, QgsFeatureRequest, QgsPointXY, QgsSingleSymbolRenderer, QgsSymbol
from qgis.gui import QgsMapTool
from .cambiador_form import Ui_Dialog  # Asegúrate de que este archivo esté importado correctamente


class CambiadorValor(QgsMapTool):

    def __init__(self, iface):
        super().__init__(iface.mapCanvas())
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.layer = None
        self.value = None
        self.attribute = None
        self.tool_active = False
        self.dialog = None

        # Inicializar un temporizador para el efecto de flash
        self.flash_timer = QtCore.QTimer()
        self.flash_timer.timeout.connect(self.restore_feature)
        self.flashing_feature_id = None
        self.original_symbol = None

    def initGui(self):
        self.action = QtWidgets.QAction("Cambiador de Valor", self.iface.mainWindow())
        self.action.triggered.connect(self.start)
        self.iface.addPluginToMenu("CambiadorValor", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("CambiadorValor", self.action)
        self.iface.removeToolBarIcon(self.action)

    def start(self):
        if not self.dialog:
            self.dialog = QtWidgets.QDialog()
            self.ui = Ui_Dialog()
            self.ui.setupUi(self.dialog)

            # Conectar los botones del buttonBox
            self.ui.buttonBox.accepted.connect(self.on_dialog_accepted)
            self.ui.buttonBox.rejected.connect(self.deactivate)

        self.layer = self.iface.activeLayer()
        if not self.layer:
            QtWidgets.QMessageBox.warning(None, "Alerta", "Por favor, selecciona una capa.")
            return

        self.ui.comboBox.clear()
        self.ui.comboBox.addItems([field.name() for field in self.layer.fields()])

        self.dialog.exec_()

        self.iface.mapCanvas().setMapTool(self)  # Activa la herramienta
        self.set_cursor()  # Cambia el cursor al activarla

    def keyPressEvent(self, event):
        """ Captura eventos de teclado y permite desactivar la herramienta con Escape. """
        if event.key() == QtCore.Qt.Key_Escape:
            self.deactivate()  # Desactiva la herramienta

    def on_dialog_accepted(self):
        self.value = self.ui.lineEdit.text()
        self.attribute = self.ui.comboBox.currentText()

        # Inicia el modo de edición
        if self.layer:
            self.layer.startEditing()  # Activa la edición en la capa
        
        self.tool_active = True
        self.dialog.close()

    def canvasPressEvent(self, event):
        if self.tool_active:
            point = self.toMapCoordinates(event.pos())
            feature = self.get_feature_at(point)
            if feature:
                self.update_feature(feature)
                self.start_flash(feature.id())  # Usamos el ID de la característica

    def get_feature_at(self, point):
        """Buscar la característica en el punto especificado."""
        request = QgsFeatureRequest().setFilterRect(self.layer.extent())
        for feature in self.layer.getFeatures(request):
            if feature.geometry().contains(point):
                return feature
        return None

    def update_feature(self, feature):
        feature[self.attribute] = self.value
        self.layer.updateFeature(feature)

    def start_flash(self, feature_id):
        """Inicia el efecto de flash en la característica seleccionada."""

        self.flashing_feature_id = feature_id  # Almacena el ID de la característica
        feature = self.layer.getFeature(self.flashing_feature_id)

        # Guarda el símbolo original
        self.original_symbol = self.layer.renderer().symbol().clone()  

        # Cambia el color del símbolo a rojo
        flash_symbol = self.original_symbol.clone()
        flash_symbol.setColor(QtGui.QColor(255, 0, 0))  # Cambia a rojo

        # Obtener la capa de símbolos
        symbol_renderer = QgsSingleSymbolRenderer(flash_symbol)  

        # Asignar el nuevo símbolo al renderer temporal
        self.layer.setRenderer(symbol_renderer)  
        self.layer.triggerRepaint()  # Fuerza a repintar la capa

        # Inicia el temporizador para restaurar el símbolo después de un tiempo
        self.flash_timer.start(300)  # Cambiar durante 300 ms

    def restore_feature(self):
        """Restaura la simbología original de la característica seleccionada."""
        if self.layer and self.original_symbol:
            # Restaura el símbolo original
            self.layer.setRenderer(QgsSingleSymbolRenderer(self.original_symbol))  
            self.layer.triggerRepaint()  # Fuerza a repintar la capa

        # Detener el temporizador
        self.flash_timer.stop()
        self.flashing_feature_id = None
        self.original_symbol = None

    def deactivate(self):
        self.tool_active = False
        self.dialog.close()  # Cierra el formulario
        self.reset_cursor()  # Restaura el cursor al desactivar

    def set_cursor(self):
        """ Cambiar el cursor cuando la herramienta está activa. """
        self.canvas.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))  # Cursor de mano

    def reset_cursor(self):
        """ Restaurar el cursor predeterminado. """
        self.canvas.unsetCursor()  # Vuelve a establecer el cursor en el predeterminado
