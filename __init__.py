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

import bpy
import numpy
from bpy.types import AddonPreferences
from bpy.types import Operator 
from bpy.props import (FloatProperty, BoolProperty)

bl_info = {
    "name": "Clipping Assistant",
    "description": "Assistant to set Viewport and Camera Clipping Distance",
    "author": "Daniel Grauer",
    "version": (1, 0, 1),
    "blender": (2, 83, 0),
    "location": "TopBar",
    "category": "System",
    "wiki_url": "https://github.com/kromar/blender_clipping_assistant",
    "tracker_url": "https://github.com/kromar/blender_clipping_assistant/issues/new",
}

  

def draw_button(self, context):
    pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences    
    if context.region.alignment == 'RIGHT':
        layout = self.layout
        row = layout.row(align=True)
        if pref.button_text:
            row.operator(operator="scene.clipping_assistant", text="Set Clipping", icon='VIEW_CAMERA', emboss=True, depress=False)
        else:
            row.operator(operator="scene.clipping_assistant", text="", icon='VIEW_CAMERA', emboss=True, depress=False)




class ClippingAssistant_OT_run(Operator):
    bl_idname = "scene.clipping_assistant"
    bl_label = "clipping_assistant"
    bl_description = "Set Start and End Clipping Distance of Camera(s)"
    
    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def max_list_value(self, list):
        i = numpy.argmax(list)
        v = list[i]
        return (i, v)

    def min_list_value(self, list):
        i = numpy.argmin(list)
        v = list[i]
        return (i, v)

    def execute(self, context):        
        pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences        
        obj = bpy.context.active_object
        # calculate selected context
        #size = sum(obj.dimensions)        
        i, max = self.max_list_value(obj.dimensions)
        i, min = self.min_list_value(obj.dimensions)
        print(obj.name , ": ", max, min)
        # adjust clipping selected context
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.clip_start = min / pref.clip_start_factor
                        space.clip_end = max * pref.clip_end_factor
                        print("start: ", space.clip_start, "\nend: ", space.clip_end)
                        if space.camera and pref.camera_clipping:
                            print("camera: ", space.camera.name)
                            bpy.data.cameras[space.camera.name].clip_start = min / pref.clip_start_factor
                            bpy.data.cameras[space.camera.name].clip_end = max * pref.clip_end_factor
        
        return{'FINISHED'}

class ClippingAssistantPreferences(AddonPreferences):
    bl_idname = __package__

    clip_start_factor: FloatProperty(
        name="Clip Start Divider",
        description="Value to calculate Clip Start, the higher the value the smaller the Clip Start Distance",
        default=100,
        min = 1,
        soft_max=1000,
        step=10,
        precision=0,
        subtype='FACTOR') 

    clip_end_factor: FloatProperty(
        name="Clip End Multiplier",
        description="Value to calculate Clip End, the higher the value the bigger the Clip End Distance",
        default=100,
        min = 1,
        soft_max=1000,
        step=10,
        precision=0,
        subtype='FACTOR') 

    camera_clipping: BoolProperty(
        name="Apply Clipping To Active Camera",
        description="When enabled the clipping Distance of the Active Camera is adjusted as well as the Viewport Clip Distance",
        default=False)
    
    button_text: BoolProperty(
        name="Show Button Text",
        description="When enabled the Header Button will Show A Text",
        default=True)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, 'clip_start_factor') 
        layout.prop(self, 'clip_end_factor') 
        layout.prop(self, 'camera_clipping') 
        layout.prop(self, 'button_text') 


classes = (
    ClippingAssistant_OT_run,
    ClippingAssistantPreferences,
    )

def register():
    
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_HT_upper_bar.prepend(draw_button)


def unregister():
    bpy.types.TOPBAR_HT_upper_bar.remove(draw_button)
    [bpy.utils.unregister_class(c) for c in classes]

if __name__ == "__main__":
    register()
