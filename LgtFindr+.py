"""
Light Finder + (c) 2023 - Maya PySide2/Qt Version
Miguel Agenjo, 3D Generalist / Lighting TD
www.artstation.com/magenjo

Integrated with Maya. Run this in Maya's Python editor or as a shelf button.
Manages publishing and loading of light configurations with version control.
"""

import sys
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


# ==================== Version Management ====================

class VersionManager:
    """Manages version control for light configurations"""
    
    def __init__(self, base_path: str = None):
        # Default path
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
            
            # Add metadata
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
                # Get all attributes from the shapes
                all_attrs = cmds.listAttr(shapes) or []
                
                # Filter for Arnold attributes (containing "ai")
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
                                
                                # Handle different data types
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
                            
                            # Handle different data types
                            if isinstance(attr_value, (list, tuple)):
                                # Convert tuples/lists to lists for JSON serialization
                                if len(attr_value) == 1:
                                    light_data["attributes"][attr] = attr_value[0]
                                else:
                                    light_data["attributes"][attr] = list(attr_value)
                            else:
                                light_data["attributes"][attr] = attr_value
                        except:
                            # Skip attributes that can't be read
                            pass
                    
                    # Get Arnold attributes
                    arnold_attrs = self.get_arnold_attributes(shapes)
                    for attr in arnold_attrs:
                        try:
                            attr_path = shape + "." + attr
                            attr_value = cmds.getAttr(attr_path)
                            
                            # Handle different data types
                            if isinstance(attr_value, (list, tuple)):
                                # Convert tuples/lists to lists for JSON serialization
                                if len(attr_value) == 1:
                                    light_data["attributes"][attr] = attr_value[0]
                                else:
                                    light_data["attributes"][attr] = list(attr_value)
                            else:
                                light_data["attributes"][attr] = attr_value
                        except:
                            # Skip attributes that can't be read
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
                    
                    # Create a new light with a unique name
                    # Get the base name and append a suffix if light already exists
                    light_name = name
                    counter = 1
                    while cmds.objExists(light_name):
                        light_name = f"{name}_{counter}"
                        counter += 1
                    
                    # Create the light based on the type
                    try:
                        # Try to create the light using the stored type
                        new_light = None
                        if "aiAreaLight" in light_type:
                            new_light = cmds.createNode("aiAreaLight", name=f"{light_name}Shape")
                        elif "aiMesh" in light_type:
                            new_light = cmds.createNode("mesh", name=light_name)
                        elif "directional" in light_type.lower():
                            new_light = cmds.directionalLight(name=light_name)
                        elif "point" in light_type.lower():
                            new_light = cmds.pointLight(name=light_name)
                        elif "spot" in light_type.lower():
                            new_light = cmds.spotLight(name=light_name)
                        else:
                            # Fallback: create an area light for unknown types
                            new_light = cmds.createNode("areaLight", name=light_name)
                        
                        # Get the shape node
                        if new_light:
                            # Get shape node if we have a transform
                            shapes = cmds.listRelatives(new_light, shapes=True)
                            if not shapes:
                                # If new_light is already a shape, use it directly
                                shape_node = new_light
                                light_transform = cmds.listRelatives(new_light, parent=True)
                                if light_transform:
                                    light_transform = light_transform[0]
                            else:
                                shape_node = shapes[0]
                                light_transform = new_light
                            
                            # Apply transform attributes first (translate, rotate, scale, shear)
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
                            
                            # Apply all stored attributes to the shape
                            applied_count = 0
                            for attr_name, attr_value in attributes.items():
                                try:
                                    attr_path = shape_node + "." + attr_name
                                    
                                    # Try standard setAttr first
                                    try:
                                        if isinstance(attr_value, list):
                                            # Handle list/vector attributes
                                            cmds.setAttr(attr_path, *attr_value)
                                        else:
                                            cmds.setAttr(attr_path, attr_value)
                                        applied_count += 1
                                    except:
                                        # If standard setAttr fails, try with string type for complex attributes
                                        try:
                                            if isinstance(attr_value, str):
                                                cmds.setAttr(attr_path, attr_value, type="string")
                                            else:
                                                # Skip if we can't determine the type
                                                print(f"Skipped {attr_name}: unsupported attribute type")
                                        except Exception as e2:
                                            print(f"Warning: Could not set {attr_name}: {e2}")
                                
                                except Exception as e:
                                    print(f"Error processing attribute {attr_name}: {e}")
                            
                            print(f"Created light '{light_transform or shape_node}' with {transform_applied} transform and {applied_count} shape attributes applied")
                            created_lights.append(light_transform if light_transform else shape_node)
                    except Exception as e:
                        print(f"Warning: Failed to create light {light_name}: {e}")
                        pass
                
                except Exception as e:
                    print(f"Error processing light data: {e}")
                    pass
            
            if created_lights:
                # Select the newly created lights
                cmds.select(created_lights)
                return True
            else:
                return False
            
        except Exception as e:
            print(f"Error applying properties: {e}")
            return False


# ==================== Main UI Window ====================

class LightFinderWindow(MayaQWidgetBaseMixin, QWidget):
    """Main Light Finder/Publisher window for Maya - Dockable"""
    
    WINDOW_NAME = "LightFinderWindow"
    
    def __init__(self, base_path: str = None):
        super().__init__()
        self.setWindowTitle("Light Finder +")
        self.setGeometry(100, 100, 500, 60)
        
        # Initialize managers
        self.version_manager = VersionManager(base_path)
        self.light_finder = LightFinderFunctions(self.version_manager)
        
        # Current state
        self.current_asset = None
        self.current_version = None
        
        # Apply dark theme colors matching Maya
        self.setStyleSheet("""
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
                background-color: #2D2D2D;
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
                background-color: #2D2D2D;
                color: #CCCCCC;
                border: 1px solid #1A1A1A;
                padding: 5px;
            }
            QTabWidget::pane {
                border: 1px solid #1A1A1A;
            }
            QTabBar::tab {
                background-color: #4D4D4D;
                color: #CCCCCC;
                padding: 5px 15px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #555555;
            }
        """)
        
        self.resize(5, 40)
        self.create_ui()
    
    def create_ui(self):
        """Create the main UI layout"""
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
        
        # Create tabbed interface
        self.tabs = QTabWidget()
        
        # Tab 1: Publisher
        publisher_widget = self.create_publisher_tab()
        self.tabs.addTab(publisher_widget, "Publisher")
        
        # Tab 2: Loader
        loader_widget = self.create_loader_tab()
        self.tabs.addTab(loader_widget, "Loader")
        
        main_layout.addWidget(self.tabs)
        
        # Footer
        footer = QLabel("Miguel Agenjo - www.artstation.com/magenjo")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("background-color: #1A1A1A; padding: 8px; font-size: 9px; color: #777777;")
        main_layout.addWidget(footer)
    
    def create_publisher_tab(self) -> QWidget:
        """Create the publisher tab"""
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
            # Use white color for the note, gray for other instructions
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
        self.pub_name_combo.currentTextChanged.connect(self.on_pub_name_selected)
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
        set_path_btn.clicked.connect(self.set_custom_path)
        layout.addWidget(set_path_btn)

        # Publish button
        publish_btn = QPushButton("PUBLISH")
        publish_btn.setMinimumHeight(50)
        publish_btn.setStyleSheet("background-color: #336633; font-weight: bold; font-size: 14px;")
        publish_btn.clicked.connect(self.publish_configuration)
        layout.addWidget(publish_btn)
        
        return widget
    
    def create_loader_tab(self) -> QWidget:
        """Create the loader tab"""
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
        
        # Assets list with version/import controls
        assets_and_controls_layout = QHBoxLayout()
        
        self.loader_list = QListWidget()
        self.loader_list.itemSelectionChanged.connect(self.on_asset_selected)
        assets_and_controls_layout.addWidget(self.loader_list, 3)
        
        # Version and info controls on the right
        right_controls_layout = QVBoxLayout()
        
        version_layout = QHBoxLayout()
        version_label = QLabel("Version")
        version_label.setStyleSheet("font-weight: bold;")
        version_layout.addWidget(version_label)
        self.version_combo = QComboBox()
        self.version_combo.currentTextChanged.connect(self.on_version_changed)
        version_layout.addWidget(self.version_combo)
        right_controls_layout.addLayout(version_layout)
        
        info_btn = QPushButton("Info")
        info_btn.setStyleSheet("background-color: #333355;")
        info_btn.clicked.connect(self.show_asset_info)
        right_controls_layout.addWidget(info_btn)
        
        right_controls_layout.addStretch()
        
        assets_and_controls_layout.addLayout(right_controls_layout, 1)
        layout.addLayout(assets_and_controls_layout)
        
        # Load button
        load_btn = QPushButton("LOAD SELECTED")
        load_btn.setMinimumHeight(50)
        load_btn.setStyleSheet("background-color: #335533; font-weight: bold; font-size: 14px;")
        load_btn.clicked.connect(self.load_configuration)
        layout.addWidget(load_btn)
        
        # Refresh loader on show
        self.refresh_assets()
        
        return widget
    
    @Slot()
    def set_custom_path(self):
        """Set a custom base path for version management and save it to env.json"""
        default_path = str(self.version_manager.base_path)
        new_path, ok = QInputDialog.getText(self, "Set Custom Folder", "Enter new base folder for publications:", text=default_path)

        if ok and new_path:
            # Save the new path to env.json in the base path directory
            env_path = os.path.join(default_path, "env.json")
            try:
                with open(env_path, "w") as f:
                    json.dump({"custom_path": new_path}, f, indent=2)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save custom path: {e}")
            self.refresh_assets()

    @Slot()
    def refresh_assets(self):
        """Refresh the assets list in loader"""
        self.loader_list.clear()
        self.pub_name_combo.clear()
        
        assets = self.version_manager.get_all_assets()
        
        for asset in assets:
            item = QListWidgetItem(asset)
            self.loader_list.addItem(item)
            self.pub_name_combo.addItem(asset)
    
    @Slot()
    def on_asset_selected(self):
        """Handle asset selection"""
        items = self.loader_list.selectedItems()
        if items:
            self.current_asset = items[0].text()
            self.refresh_versions()
    
    @Slot()
    def refresh_versions(self):
        """Refresh versions for selected asset"""
        self.version_combo.clear()
        
        if self.current_asset:
            versions = self.version_manager.get_versions(self.current_asset)
            for version in versions:
                self.version_combo.addItem(f"v{version}", version)
    
    @Slot(str)
    def on_version_changed(self):
        """Handle version change"""
        if self.version_combo.count() > 0:
            self.current_version = self.version_combo.currentData()
    
    @Slot(str)
    def on_pub_name_selected(self):
        """Handle publication name selection from combo"""
        selected = self.pub_name_combo.currentText()
        if selected:
            self.pub_name_input.setText(selected)
    
    @Slot()
    def publish_configuration(self):
        """Publish a light configuration"""
        name = self.pub_name_input.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a publication name")
            return
        
        # Get selected lights
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
            # Collect light properties
            config_data = self.light_finder.collect_light_properties(lights)
            
            # Add description to config data
            description = self.pub_desc_input.toPlainText().strip()
            config_data["description"] = description
            
            if self.version_manager.publish_file(name, config_data):
                QMessageBox.information(self, "Success", "Version published successfully!")
                self.refresh_assets()
            else:
                QMessageBox.warning(self, "Error", "Failed to publish configuration")
    
    @Slot()
    def load_configuration(self):
        """Load a light configuration"""
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
    def show_asset_info(self):
        """Show information about selected asset"""
        if not self.current_asset:
            QMessageBox.warning(self, "Error", "Please select an asset")
            return
        
        version_path = self.version_manager.get_version_path(
            self.current_asset, self.current_version
        )
        
        # Get file creation date
        json_file = version_path / f"{self.current_asset}.json"
        creation_date = ""
        description = ""
        
        if json_file.exists():
            creation_date = datetime.fromtimestamp(json_file.stat().st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            
            # Load and get description from JSON
            try:
                config = self.version_manager.load_file(self.current_asset, self.current_version)
                description = config.get("description", "") if config else ""
            except:
                pass
        
        info_text = f"Asset:\n{self.current_asset}\n\n"
        info_text += f"Version:\n{self.current_version}\n\n"
        info_text += f"Creation Date:\n{creation_date}\n\n"
        
        if description:
            info_text += f"Description:\n{description}\n\n"
        
        info_text += f"Path:\n{version_path}\n"
        
        QMessageBox.information(self, "Asset Information", info_text)


# ==================== Application Entry Point ====================

# Keep track of the current window at module level
_current_window = None

def create_light_finder_window():
    """Create the Light Finder window - ensures only one instance exists at a time"""
    global _current_window

    if not MAYA_AVAILABLE:
        cmds.confirmDialog(title="Error", message="This tool requires Maya with PySide2 support")
        return None

    # Search ALL top-level widgets for any existing instance by object name
    # This catches windows that slipped past our global reference (e.g. via MayaQWidgetBaseMixin)
    app = QApplication.instance()
    if app:
        for widget in app.topLevelWidgets():
            if widget.objectName() == LightFinderWindow.WINDOW_NAME:
                try:
                    widget.close()
                    widget.deleteLater()
                except:
                    pass

    # Also clean up via global reference as a safety net
    if _current_window is not None:
        try:
            _current_window.close()
            _current_window.deleteLater()
        except:
            pass
        _current_window = None

    # Create a fresh window
    window = LightFinderWindow()
    window.setObjectName(LightFinderWindow.WINDOW_NAME)
    window.show()

    # Store reference
    _current_window = window

    return window


if __name__ == "__main__":
    # When run from Maya's Python editor
    window = create_light_finder_window()