"""
Light Finder +
(c) 2023 - Maya PySide2/Qt Version
Miguel Agenjo, 3D Generalist / Lighting TD
www.miguelagenjo.com

"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Maya imports
try:
    import maya.cmds as cmds
    import maya.OpenMayaUI as omui
    from maya.app.general.mayaMixin import MayaQWidgetBaseMixin
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False
    MayaQWidgetBaseMixin = object

# PySide2 imports
from PySide2.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QListWidget, QListWidgetItem,
    QMessageBox, QTabWidget, QInputDialog
)
from PySide2.QtCore import Qt, Slot
from PySide2.QtGui import QFont

# Resolve MayaQWidgetBaseMixin base: handles both Maya 2022 (mixin without QWidget)
# and newer Maya versions (mixin already inherits QWidget) without MRO conflicts.
if not MAYA_AVAILABLE:
    MayaQWidgetBaseMixin = QWidget

if QWidget in getattr(MayaQWidgetBaseMixin, '__mro__', ()):
    _WindowBase = MayaQWidgetBaseMixin
else:
    class _WindowBase(MayaQWidgetBaseMixin, QWidget):
        pass


# ==================== Stylesheet ====================

DARK_STYLESHEET = """
    QWidget {
        background-color: #333333;
        color: #CCCCCC;
    }
    QLabel {
        color: #CCCCCC;
    }
    QPushButton {
        background-color: #4D4D4D;
        color: #CCCCCC;
        border: 1px solid #1A1A1A;
        border-radius: 3px;
        padding: 3px;
    }
    QPushButton:hover {
        background-color: #5D5D5D;
    }
    QPushButton:pressed {
        background-color: #3D3D3D;
    }
    QListWidget {
        background-color: #2A2A2A;
        color: #CCCCCC;
        border: 1px solid #1A1A1A;
    }
    QListWidget::item:selected {
        background-color: #555555;
    }
    QComboBox {
        background-color: #4D4D4D;
        color: #CCCCCC;
        border: 1px solid #1A1A1A;
        padding: 2px;
    }
    QTextEdit {
        background-color: #2A2A2A;
        color: #CCCCCC;
        border: 1px solid #1A1A1A;
        padding: 5px;
    }
    QLineEdit {
        background-color: #2A2A2A;
        color: #CCCCCC;
        border: 1px solid #1A1A1A;
        padding: 3px;
    }
    QTabWidget::pane {
        border: 1px solid #1A1A1A;
    }
    QTabBar::tab {
        background-color: #282828;
        color: #CCCCCC;
        padding: 5px 15px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background-color: #333333;
    }
    QDoubleSpinBox, QSpinBox {
        background-color: #2A2A2A;
        color: #CCCCCC;
        border: 1px solid #0A0A0A;
        padding: 2px;
    }
    QSlider::groove:horizontal {
        background-color: #2D2D2D;
        height: 6px;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background-color: #AAAAAA;
        width: 14px;
        margin: -4px 0;
        border-radius: 7px;
    }
    QCheckBox {
        color: #CCCCCC;
    }
    QScrollArea {
        border: none;
    }
"""


# ==================== Version Management ====================

class VersionManager:
    """Manages version control for light configurations"""

    def __init__(self, base_path: str = None):
        default_path = str(Path.home() / "LgtFindr_maya") if base_path is None else base_path
        env_path = os.path.join(default_path, "env.json")
        custom_path = None
        if os.path.exists(env_path):
            try:
                with open(env_path, "r") as f:
                    data = json.load(f)
                    custom_path = data.get("custom_path")
            except Exception as e:
                print(f"Warning: Could not read env.json: {e}")
        if custom_path:
            published_lights_path = Path(custom_path) / "Published_lights"
            published_lights_path.mkdir(parents=True, exist_ok=True)
            self.base_path = published_lights_path
        else:
            self.base_path = Path(default_path)
            self.base_path.mkdir(parents=True, exist_ok=True)

    def get_all_assets(self) -> List[str]:
        """Get all published light assets"""
        assets = []
        if self.base_path.exists():
            for item in self.base_path.iterdir():
                if item.is_dir():
                    assets.append(item.name)
        return sorted(assets)

    def get_versions(self, asset_name: str) -> List[int]:
        """Get all versions for an asset"""
        asset_path = self.base_path / asset_name
        versions = []
        if asset_path.exists():
            for item in asset_path.iterdir():
                if item.is_dir() and item.name.isdigit():
                    versions.append(int(item.name))
        return sorted(versions, reverse=True)

    def get_latest_version(self, asset_name: str) -> Optional[int]:
        """Get latest version number for an asset"""
        versions = self.get_versions(asset_name)
        return versions[0] if versions else None

    def create_new_version(self, asset_name: str) -> Path:
        """Create a new version folder for an asset"""
        asset_path = self.base_path / asset_name
        asset_path.mkdir(parents=True, exist_ok=True)
        latest = self.get_latest_version(asset_name)
        new_version = (latest or 0) + 1
        version_path = asset_path / str(new_version)
        version_path.mkdir(parents=True, exist_ok=True)
        return version_path

    def get_version_path(self, asset_name: str, version: int) -> Path:
        """Get path to a specific version"""
        return self.base_path / asset_name / str(version)

    def publish_file(self, asset_name: str, file_data: Dict) -> bool:
        """Publish a light configuration file"""
        try:
            version_path = self.create_new_version(asset_name)
            file_path = version_path / f"{asset_name}.json"
            file_data["_published"] = datetime.now().isoformat()
            file_data["_asset_name"] = asset_name
            with open(file_path, 'w') as f:
                json.dump(file_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error publishing file: {e}")
            return False

    def load_file(self, asset_name: str, version: int) -> Optional[Dict]:
        """Load a light configuration file"""
        try:
            version_path = self.get_version_path(asset_name, version)
            file_path = version_path / f"{asset_name}.json"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading file: {e}")
        return None


# ==================== Light Finder Functions ====================

class LightFinderFunctions:
    """Light Finder core functionality for Maya integration"""

    def __init__(self, version_manager: VersionManager):
        self.version_manager = version_manager

    def get_selected_lights(self) -> List[str]:
        """Get currently selected lights from Maya"""
        try:
            selected = cmds.ls(selection=True)
            lights = []
            for obj in selected:
                shapes = cmds.listRelatives(obj, shapes=True) or []
                for shape in shapes:
                    shape_type = cmds.objectType(shape)
                    if "light" in shape_type.lower():
                        lights.append(obj)
                        break
            return lights
        except:
            return []

    def get_arnold_attributes(self, shapes: List[str]) -> List[str]:
        """Get all Arnold attributes (containing 'ai') from shapes"""
        arnold_attrs = []
        try:
            if shapes:
                all_attrs = cmds.listAttr(shapes) or []
                for attr in all_attrs:
                    if "ai" in attr:
                        arnold_attrs.append(attr)
        except:
            pass
        return arnold_attrs

    def collect_light_properties(self, lights: List[str]) -> Dict:
        """Collect all properties from selected lights"""
        properties = {"lights": []}

        for light in lights:
            try:
                shapes = cmds.listRelatives(light, shapes=True)
                if shapes:
                    shape = shapes[0]
                    light_data = {
                        "name": light,
                        "type": cmds.objectType(shape),
                        "attributes": {},
                        "transform": {}
                    }

                    # Collect transform attributes from the light's transform node
                    transform_attrs = cmds.listAttr(light, keyable=True) or []
                    for attr in transform_attrs:
                        if any(keyword in attr.lower() for keyword in ["translate", "rotate", "scale", "shear"]):
                            try:
                                attr_path = light + "." + attr
                                attr_value = cmds.getAttr(attr_path)
                                if isinstance(attr_value, (list, tuple)):
                                    if len(attr_value) == 1:
                                        light_data["transform"][attr] = attr_value[0]
                                    else:
                                        light_data["transform"][attr] = list(attr_value)
                                else:
                                    light_data["transform"][attr] = attr_value
                            except:
                                pass

                    # Get all keyable attributes from the light shape
                    all_attrs = cmds.listAttr(shape, keyable=True) or []
                    for attr in all_attrs:
                        try:
                            attr_path = shape + "." + attr
                            attr_value = cmds.getAttr(attr_path)
                            if isinstance(attr_value, (list, tuple)):
                                if len(attr_value) == 1:
                                    light_data["attributes"][attr] = attr_value[0]
                                else:
                                    light_data["attributes"][attr] = list(attr_value)
                            else:
                                light_data["attributes"][attr] = attr_value
                        except:
                            pass

                    # Get Arnold attributes
                    arnold_attrs = self.get_arnold_attributes(shapes)
                    for attr in arnold_attrs:
                        try:
                            attr_path = shape + "." + attr
                            attr_value = cmds.getAttr(attr_path)
                            if isinstance(attr_value, (list, tuple)):
                                if len(attr_value) == 1:
                                    light_data["attributes"][attr] = attr_value[0]
                                else:
                                    light_data["attributes"][attr] = list(attr_value)
                            else:
                                light_data["attributes"][attr] = attr_value
                        except:
                            pass

                    properties["lights"].append(light_data)
            except:
                pass

        return properties

    def apply_light_properties(self, properties: Dict) -> bool:
        """Apply all light properties to scene and create exact copies of published lights"""
        try:
            created_lights = []

            for light_data in properties.get("lights", []):
                try:
                    name = light_data.get("name")
                    light_type = light_data.get("type")
                    attributes = light_data.get("attributes", {})
                    transform_attrs = light_data.get("transform", {})

                    light_name = name
                    counter = 1
                    while cmds.objExists(light_name):
                        light_name = f"{name}_{counter}"
                        counter += 1

                    try:
                        new_light = None
                        if "aiAreaLight" in light_type:
                            new_light = cmds.shadingNode("aiAreaLight", name=f"{light_name}Shape", asLight=True)
                        elif "aiMesh" in light_type:
                            new_light = cmds.shadingNode("mesh", name=f"{light_name}Shape", asLight=True)
                        elif "directional" in light_type.lower():
                            new_light = cmds.directionalLight(name=light_name)
                        elif "point" in light_type.lower():
                            new_light = cmds.pointLight(name=light_name)
                        elif "spot" in light_type.lower():
                            new_light = cmds.spotLight(name=light_name)
                        elif "skydome" in light_type.lower():
                            new_light = cmds.shadingNode("aiSkyDomeLight", name=f"{light_name}Shape", asLight=True)
                        elif "photometric" in light_type.lower():
                            new_light = cmds.shadingNode("aiPhotometricLight", name=f"{light_name}Shape", asLight=True)
                        else:
                            new_light = cmds.shadingNode("areaLight", name=f"{light_name}Shape", asLight=True)

                        if new_light:
                            shapes = cmds.listRelatives(new_light, shapes=True)
                            if not shapes:
                                shape_node = new_light
                                light_transform = cmds.listRelatives(new_light, parent=True)
                                if light_transform:
                                    light_transform = light_transform[0]
                            else:
                                shape_node = shapes[0]
                                light_transform = new_light

                            # Apply transform attributes
                            transform_applied = 0
                            for attr_name, attr_value in transform_attrs.items():
                                try:
                                    attr_path = light_transform + "." + attr_name
                                    if isinstance(attr_value, list):
                                        cmds.setAttr(attr_path, *attr_value)
                                    else:
                                        cmds.setAttr(attr_path, attr_value)
                                    transform_applied += 1
                                except Exception as e:
                                    print(f"Warning: Could not set transform {attr_name}: {e}")

                            # Apply shape attributes
                            applied_count = 0
                            for attr_name, attr_value in attributes.items():
                                try:
                                    attr_path = shape_node + "." + attr_name
                                    try:
                                        if isinstance(attr_value, list):
                                            cmds.setAttr(attr_path, *attr_value)
                                        else:
                                            cmds.setAttr(attr_path, attr_value)
                                        applied_count += 1
                                    except:
                                        try:
                                            if isinstance(attr_value, str):
                                                cmds.setAttr(attr_path, attr_value, type="string")
                                            else:
                                                print(f"Skipped {attr_name}: unsupported attribute type")
                                        except Exception as e2:
                                            print(f"Warning: Could not set {attr_name}: {e2}")
                                except Exception as e:
                                    print(f"Error processing attribute {attr_name}: {e}")

                            print(f"Created light '{light_transform or shape_node}' with {transform_applied} transform and {applied_count} shape attributes applied")
                            created_lights.append(light_transform if light_transform else shape_node)
                    except Exception as e:
                        print(f"Warning: Failed to create light {light_name}: {e}")

                except Exception as e:
                    print(f"Error processing light data: {e}")

            if created_lights:
                cmds.select(created_lights)
                return True
            else:
                return False

        except Exception as e:
            print(f"Error applying properties: {e}")
            return False

    def export_selection_to_version_folder(self, asset_name: str, version: int) -> bool:
        """Export the current Maya selection to the version folder as a .ma file"""
        try:
            version_path = self.version_manager.get_version_path(asset_name, version)
            file_name = f"{asset_name}.ma"
            export_path = str(version_path / file_name)
            selection = cmds.ls(selection=True)
            if not selection:
                print("No selection to export.")
                return False
            cmds.file(export_path, force=True, options="v=0", type="mayaAscii", exportSelected=True)
            print(f"Exported selection to {export_path}")
            return True
        except Exception as e:
            print(f"Error exporting selection: {e}")
            return False


# ==================== Light Finder Tab (PySide2) ====================

class LightFinderTab(QWidget):
    """Light Finder tab with Publisher and Loader sub-tabs"""

    def __init__(self, base_path=None, parent=None):
        super().__init__(parent)
        self.version_manager = VersionManager(base_path)
        self.light_finder = LightFinderFunctions(self.version_manager)
        self.current_asset = None
        self.current_version = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.sub_tabs = QTabWidget()
        self.sub_tabs.addTab(self._create_publisher_tab(), "Publisher")
        self.sub_tabs.addTab(self._create_loader_tab(), "Loader")
        layout.addWidget(self.sub_tabs)

    def _create_publisher_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Instructions
        instr_label = QLabel("Publication Instructions:")
        instr_label.setStyleSheet("font-weight: bold; color: #AAAAAA;")
        layout.addWidget(instr_label)

        instructions = [
            "1. Select the lights you want to publish",
            "2. Enter a custom name for your publication",
            "3. Click 'Publish' to save the configuration",
            "",
            "Note: Same naming will increment existing version"
        ]

        for instr in instructions:
            instr_text = QLabel(instr)
            if "Note:" in instr:
                instr_text.setStyleSheet("color: #FFFFFF; font-size: 12px;")
            else:
                instr_text.setStyleSheet("color: #888888; font-size: 12px;")
            layout.addWidget(instr_text)

        layout.addWidget(QLabel(""))

        # Publication name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Publication Name"))
        self.pub_name_input = QTextEdit()
        self.pub_name_input.setMaximumHeight(30)
        name_layout.addWidget(self.pub_name_input, 3)

        self.pub_name_combo = QComboBox()
        self.pub_name_combo.currentTextChanged.connect(self._on_pub_name_selected)
        name_layout.addWidget(self.pub_name_combo)

        layout.addLayout(name_layout)

        # Description input
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(QLabel("Description"))
        self.pub_desc_input = QTextEdit()
        self.pub_desc_input.setPlaceholderText("Optional: Add notes about this light configuration...")
        desc_layout.addWidget(self.pub_desc_input, 1)
        layout.addLayout(desc_layout, 1)

        layout.addWidget(QLabel(""))

        # Set Custom Path button
        set_path_btn = QPushButton("Set Custom Path")
        set_path_btn.setStyleSheet("background-color: #555577; font-weight: bold; font-size: 12px;")
        set_path_btn.clicked.connect(self._set_custom_path)
        layout.addWidget(set_path_btn)

        # Publish button
        publish_btn = QPushButton("PUBLISH")
        publish_btn.setMinimumHeight(50)
        publish_btn.setStyleSheet("background-color: #336633; font-weight: bold; font-size: 14px;")
        publish_btn.clicked.connect(self._publish_configuration)
        layout.addWidget(publish_btn)

        return widget

    def _create_loader_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Instructions
        instr_label = QLabel("Loading Instructions:")
        instr_label.setStyleSheet("font-weight: bold; color: #AAAAAA;")
        layout.addWidget(instr_label)

        instr_text = QLabel("Select version and click on the published item to load")
        instr_text.setStyleSheet("color: #888888; font-size: 12px;")
        instr_text2 = QLabel("Published items")

        layout.addWidget(instr_text)
        layout.addWidget(instr_text2)

        # Version selector
        version_layout = QHBoxLayout()
        version_label = QLabel("Version")
        version_label.setStyleSheet("font-weight: bold;")
        version_layout.addWidget(version_label)
        self.version_combo = QComboBox()
        self.version_combo.currentTextChanged.connect(self._on_version_changed)

        version_layout.addWidget(self.version_combo)
        version_layout.addStretch(1)
        layout.addLayout(version_layout)

        # Split view: published list (left) + info panel (right)
        split_layout = QHBoxLayout()

        self.loader_list = QListWidget()
        self.loader_list.setStyleSheet(
            "QListWidget { font-size: 14px; }"
            "QListWidget::item { padding: 4px; }"
        )
        self.loader_list.itemSelectionChanged.connect(self._on_asset_selected)
        split_layout.addWidget(self.loader_list, 1)

        self.info_panel = QTextEdit()
        self.info_panel.setReadOnly(True)
        self.info_panel.setStyleSheet(
            "background-color: #2A2A2A; color: #CCCCCC; border: 1px solid #3A3A3A; padding: 6px;"
        )
        self.info_panel.setPlaceholderText("Select a published item to see details...")
        split_layout.addWidget(self.info_panel, 1)

        layout.addLayout(split_layout)

        # Load button
        load_btn = QPushButton("LOAD SELECTED")
        load_btn.setMinimumHeight(50)
        load_btn.setStyleSheet("background-color: #335533; font-weight: bold; font-size: 14px;")
        load_btn.clicked.connect(self._load_configuration_import_ma)
        layout.addWidget(load_btn)

        # Refresh loader on show
        self._refresh_assets()

        return widget

    # ---- Light Finder Slots ----

    @Slot()
    def _set_custom_path(self):
        default_path = str(self.version_manager.base_path)
        new_path, ok = QInputDialog.getText(
            self, "Set Custom Folder",
            "Enter new base folder for publications:",
            text=default_path
        )
        if ok and new_path:
            env_path = os.path.join(default_path, "env.json")
            try:
                with open(env_path, "w") as f:
                    json.dump({"custom_path": new_path}, f, indent=2)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save custom path: {e}")
            self._refresh_assets()

    @Slot()
    def _refresh_assets(self):
        self.loader_list.clear()
        self.pub_name_combo.clear()
        assets = self.version_manager.get_all_assets()
        for asset in assets:
            item = QListWidgetItem(asset)
            self.loader_list.addItem(item)
            self.pub_name_combo.addItem(asset)

    @Slot()
    def _on_asset_selected(self):
        items = self.loader_list.selectedItems()
        if items:
            self.current_asset = items[0].text()
            self._refresh_versions()
            self._show_asset_info()

    @Slot()
    def _refresh_versions(self):
        self.version_combo.clear()
        if self.current_asset:
            versions = self.version_manager.get_versions(self.current_asset)
            for version in versions:
                self.version_combo.addItem(f"v{version}", version)

    @Slot(str)
    def _on_version_changed(self):
        if self.version_combo.count() > 0:
            self.current_version = self.version_combo.currentData()

    @Slot(str)
    def _on_pub_name_selected(self):
        selected = self.pub_name_combo.currentText()
        if selected:
            self.pub_name_input.setText(selected)

    @Slot()
    def _publish_configuration(self):
        name = self.pub_name_input.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "Error", "Please enter a publication name")
            return

        lights = self.light_finder.get_selected_lights()

        if not lights:
            QMessageBox.warning(self, "Error", "Please select some lights first")
            return

        reply = QMessageBox.question(
            self, "Confirm Publication",
            f"Publish {len(lights)} light(s) as '{name}'?\n\nThis will create a new version.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            config_data = self.light_finder.collect_light_properties(lights)
            description = self.pub_desc_input.toPlainText().strip()
            config_data["description"] = description

            if self.version_manager.publish_file(name, config_data):
                version = self.version_manager.get_latest_version(name)
                self.light_finder.export_selection_to_version_folder(name, version)
                QMessageBox.information(self, "Success", "Version published successfully!")
                self._refresh_assets()
            else:
                QMessageBox.warning(self, "Error", "Failed to publish configuration")

    @Slot()
    def _load_configuration(self):
        if not self.current_asset or self.current_version is None:
            QMessageBox.warning(self, "Error", "Please select an asset and version")
            return

        config = self.version_manager.load_file(self.current_asset, self.current_version)

        if config:
            if self.light_finder.apply_light_properties(config):
                message = f"Version {self.current_version} loaded!\n\n"
                message += f"Loaded {len(config.get('lights', []))} lights"
                QMessageBox.information(self, "Success", message)
            else:
                QMessageBox.warning(self, "Error", "Failed to apply light properties")
        else:
            QMessageBox.warning(self, "Error", "Failed to load configuration")

    @Slot()
    def _load_configuration_import_ma(self):
        if not self.current_asset or self.current_version is None:
            QMessageBox.warning(self, "Error", "Please select an asset and version")
            return
        version_path = self.version_manager.get_version_path(self.current_asset, self.current_version)
        ma_file = version_path / f"{self.current_asset}.ma"
        if not ma_file.exists():
            QMessageBox.warning(self, "Error", f".ma file not found: {ma_file}")
            return
        try:
            cmds.file(str(ma_file), i=True, ignoreVersion=True)
            QMessageBox.information(self, "Success", f"Imported {ma_file.name} successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to import .ma file: {e}")

    @Slot()
    def _show_asset_info(self):
        if not self.current_asset:
            QMessageBox.warning(self, "Error", "Please select an asset")
            return

        version_path = self.version_manager.get_version_path(
            self.current_asset, self.current_version
        )

        json_file = version_path / f"{self.current_asset}.json"
        creation_date = ""
        description = ""

        if json_file.exists():
            creation_date = datetime.fromtimestamp(json_file.stat().st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            try:
                config = self.version_manager.load_file(self.current_asset, self.current_version)
                description = config.get("description", "") if config else ""
            except:
                pass

        info_text = f"<b>Asset:</b><br>{self.current_asset}<br><br>"
        info_text += f"<b>Version:</b><br>{self.current_version}<br><br>"
        info_text += f"<b>Creation Date:</b><br>{creation_date}<br><br>"

        if description:
            info_text += f"<b>Description:</b><br>{description}<br><br>"

        info_text += f"<b>Path:</b><br>{version_path}"

        self.info_panel.setHtml(info_text)


# ==================== Main Window ====================

class LightFinderWindow(_WindowBase):
    """Light Finder + standalone window - Dockable"""

    WINDOW_NAME = "LightFinderWindow"

    def __init__(self, base_path: str = None):
        super().__init__()
        self.setWindowTitle("Light Finder +")
        self.setGeometry(100, 100, 400, 550)
        self.setMinimumHeight(580)

        self.setStyleSheet(DARK_STYLESHEET)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(3)

        # Title
        title = QLabel("< LIGHT FINDER + >")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("background-color: #1A1A1A; padding: 8px;")
        main_layout.addWidget(title)

        # Content
        main_layout.addWidget(LightFinderTab(base_path))

        # Footer
        footer = QLabel("www.miguelagenjo.com")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("background-color: #1A1A1A; padding: 8px; font-size: 12px; color: #777777;")
        main_layout.addWidget(footer)


# ==================== Application Entry Point ====================

_current_window = None


def create_light_finder_window(base_path=None):
    """Create the Light Finder window - ensures only one instance exists at a time"""
    global _current_window

    if not MAYA_AVAILABLE:
        print("This tool requires Maya with PySide2 support")
        return None

    app = QApplication.instance()
    if app:
        for widget in app.topLevelWidgets():
            if widget.objectName() == LightFinderWindow.WINDOW_NAME:
                try:
                    widget.close()
                    widget.deleteLater()
                except:
                    pass

    if _current_window is not None:
        try:
            _current_window.close()
            _current_window.deleteLater()
        except:
            pass
        _current_window = None

    window = LightFinderWindow(base_path)
    window.setObjectName(LightFinderWindow.WINDOW_NAME)
    window.show()

    _current_window = window

    return window


if __name__ == "__main__":
    window = create_light_finder_window()
