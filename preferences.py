# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

from bpy.types import AddonPreferences
from bpy.props import BoolProperty, IntProperty, FloatProperty, EnumProperty, StringProperty, PointerProperty, CollectionProperty


class ClippingAssistant_Preferences(AddonPreferences):
    bl_idname = __package__

    auto_clipping: BoolProperty(
        name="Auto Clipping",
        description="Adjust clipping distance automaticly on selected context",
        default=True) #dfault: True
    
    clip_start_factor: FloatProperty(
        name="Clip Start Multiplier",
        description="Value to calculate Clip Start, the higher the value the smaller the Clip Start Distance",
        default=0.01,
        min = 0.001,
        soft_min = 1,
        soft_max=10,
        step=1,
        subtype='FACTOR') 

    clip_end_factor: FloatProperty(
        name="Clip End Multiplier",
        description="Value to calculate Clip End, the higher the value the bigger the Clip End Distance",
        default=10,
        min = 0.001,
        soft_min = 1,
        soft_max=100,
        step=1,
        subtype='FACTOR')

    clip_start_distance: FloatProperty(
        name="Clip Start Distance",
        description="Set the Clip Start distance",
        default=0.001,
        min=0.000001, 
        soft_min = 0.0001,
        soft_max=0.01,
        step=1,
        subtype='DISTANCE') 

    clip_end_distance: FloatProperty(
        name="Clip End Distance",
        description="Set the Clip End distance",
        default=100,
        min = 0.01,
        soft_min = 0.01,
        soft_max=200,
        step=1,
        subtype='DISTANCE') 

    camera_clipping: BoolProperty(
        name="Apply Clipping To Active Camera",
        description="When enabled the clipping Distance of the Active Camera is adjusted as well as the Viewport Clip Distance",
        default=False)

    volume_clipping: BoolProperty(
        name="Apply Clipping To Volumetrics",
        description="Adapt Clipping distances of volumetric effects",
        default=True)
    
    debug_output: BoolProperty(
        name="Debug: Output",
        description="Enable some debug output",
        default=False) #default=False
        
    debug_profiling: BoolProperty(
        name="Debug: Profiling",
        description="Enable some performance output",
        default=False) #default=False
    
    show_clipping_distance: BoolProperty(
        name="Show Clipping Distance",
        description="Show the current clipping distance in the header",
        default=True
    )
    

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False

        # General settings
        layout.prop(self, 'camera_clipping')
        layout.prop(self, 'volume_clipping')
        layout.prop(self, 'auto_clipping')

        # Clipping settings
        column = layout.box()
        props = ('clip_start_factor', 'clip_end_factor') if self.auto_clipping else ('clip_start_distance', 'clip_end_distance')
        for prop in props:
            column.prop(self, prop, slider=True)

        # Debug settings
        debug_box = layout.box()
        debug_box.label(text="Debug Settings")
        debug_box.prop(self, 'show_clipping_distance')
        debug_box.prop(self, 'debug_output')
        debug_box.prop(self, 'debug_profiling')

