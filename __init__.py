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
import mathutils
from mathutils import Vector 
from bpy.types import AddonPreferences, Operator
from bpy.props import FloatProperty, BoolProperty, IntProperty, StringProperty

from bpy.app.handlers import persistent


bl_info = {
    "name": "Clipping Assistant",
    "description": "Assistant to set Viewport and Camera Clipping Distance",
    "author": "Daniel Grauer",
    "version": (2, 0, 0),
    "blender": (2, 83, 0),
    "location": "TopBar",
    "category": "System",
    "wiki_url": "https://github.com/kromar/blender_clipping_assistant",
    "tracker_url": "https://github.com/kromar/blender_clipping_assistant/issues/new",
}

def prefs():
    user_preferences = bpy.context.preferences
    return user_preferences.addons[__package__].preferences 

def max_list_value(list):
        i = numpy.argmax(list)
        v = list[i]
        return (i, v)


def min_list_value(list):
    masked_list = numpy.ma.masked_values(list, 0)  
    i = numpy.argmin(masked_list[0])
    v = masked_list[0][i]
    return v


def distance_vec(point1: Vector, point2: Vector) -> float: 
        """Calculate distance between two points.""" 
        return (point2 - point1).length  


def calc_view_matrix(obj):
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':             
                view_3d = area.spaces.active.region_3d
                #print("window_matrix: ", view_3d.window_matrix)
                #print("view_matrix: ", view_3d.view_matrix)
                #print("perspective_matrix: ", view_3d.perspective_matrix)
                #print("view_location: ", view_3d.view_location)
                #print("view_rotation: ", view_3d.view_rotation.to_euler())
                #print("view_distance: ", view_3d.view_distance)                   
                return view_3d.view_distance


# Callback function for location changes
def calculate_clipping():
    objPosition = []
    objDimension = []    

    for obj in bpy.context.selected_objects:        
        view_distance = calc_view_matrix(obj)
        objPosition.append(obj.location)
        objDimension.append(obj.dimensions) 
    
    if bpy.context.selected_objects:
        selected_objects_proximity = distance_vec(min(objPosition), max(objPosition))
        minClipping = min_list_value(objDimension) / prefs().clip_start_factor / 100
        maxClipping = (selected_objects_proximity + view_distance*2) * prefs().clip_end_factor
        #maxClipping = selected_objects_proximity + max(max(objDimension)) * view_distance * prefs().clip_end_factor
        #maxClipping = (selected_objects_proximity + max(max(objDimension)) + view_distance) * prefs().clip_end_factor * 2
        
        # fallback if objects without dimensions are selected
        if not minClipping:
            minClipping = view_distance / prefs().clip_start_factor * 0.1
        if not maxClipping:
            maxClipping = view_distance * prefs().clip_end_factor

        """ print("\nview distance: ", view_distance)
        print("objects proximity: ", selected_objects_proximity)
        print("min-max: ", minClipping, "<<=====>>", maxClipping) 
        """

        return minClipping, maxClipping


def apply_clipping():
    for workspace in bpy.data.workspaces:
        #print("workspaces:", workspace.name)
        for screen in workspace.screens:
            #print("screen: ", screen.name)
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    #print("area: ", area.type , end='\n')
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            #set viewport clipping
                            if bpy.context.selected_objects:
                                #print(bpy.context.selected_objects)
                                minClipping, maxClipping = calculate_clipping()
                                #print("\nset clipping: ", minClipping, maxClipping)
                                space.clip_start = minClipping
                                space.clip_end = maxClipping
                                #set camera clipping                            
                                if space.camera and prefs().camera_clipping:
                                    #print("camera: ", space.camera.name)
                                    bpy.data.cameras[space.camera.name].clip_start = minClipping
                                    bpy.data.cameras[space.camera.name].clip_end = maxClipping


clipping_active = False

def draw_button(self, context): 
    global clipping_active   
    if prefs().button_toggle:
        if context.region.alignment == 'RIGHT':
            layout = self.layout
            row = layout.row(align=True)   
            if prefs().button_text:
                row.operator(operator="scene.clipping_assistant", text="Start", icon='VIEW_CAMERA', emboss=True, depress=False).button_input = 'MANUAL'
                if clipping_active:
                    row.operator(operator="scene.clipping_assistant", text="Start", icon='CHECKBOX_HLT', emboss=True, depress=True).button_input = 'AUTOMATIC'
                else:
                    row.operator(operator="scene.clipping_assistant", text="Start", icon='CHECKBOX_DEHLT', emboss=True, depress=False).button_input = 'AUTOMATIC'

            else:
                row.operator(operator="scene.clipping_assistant", text="", icon='VIEW_CAMERA', emboss=True, depress=False).button_input = 'MANUAL'
                if clipping_active:
                    row.operator(operator="scene.clipping_assistant", text="", icon='CHECKBOX_HLT', emboss=True, depress=True).button_input = 'AUTOMATIC'
                else:
                    row.operator(operator="scene.clipping_assistant", text="", icon='CHECKBOX_DEHLT', emboss=True, depress=False).button_input = 'AUTOMATIC'

               

class ClippingAssistant(Operator):
    bl_idname = "scene.clipping_assistant"
    bl_label = "Toggle Automatic Clipping"
    bl_description = "Start and End Clipping Distance of Camera(s)"
    bl_options = {"REGISTER", "UNDO"}

    button_input: StringProperty()

    @classmethod
    def poll(cls, context):    
        return context.selected_objects
    
    def execute(self, context):
        wm = context.window_manager        

        global clipping_active
        if self.button_input == 'AUTOMATIC':
            if clipping_active:
                clipping_active = False     
                return {'FINISHED'}
            else:
                wm.modal_handler_add(self)
                clipping_active = True
                return {'RUNNING_MODAL'}

        elif self.button_input == 'MANUAL':
            apply_clipping()
            return {'FINISHED'}

    def cancel(self, context):        
        return {'CANCELED'}

    def modal(self, context, event):        
        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'TRACKPADZOOM'}:
            apply_clipping()        
        return {'PASS_THROUGH'}

      

class ClippingAssistant_Preferences(AddonPreferences):
    bl_idname = __package__

    clip_start_factor: IntProperty(
        name="Clip Start Divider",
        description="Value to calculate Clip Start, the higher the value the smaller the Clip Start Distance",
        default=1,
        min = 1,
        soft_max=100,
        step=1,
        subtype='FACTOR') 

    clip_end_factor: IntProperty(
        name="Clip End Multiplier",
        description="Value to calculate Clip End, the higher the value the bigger the Clip End Distance",
        default=1,
        min = 1,
        soft_max=100,
        step=1,
        subtype='FACTOR') 

    camera_clipping: BoolProperty(
        name="Apply Clipping To Active Camera",
        description="When enabled the clipping Distance of the Active Camera is adjusted as well as the Viewport Clip Distance",
        default=False)
    
    button_text: BoolProperty(
        name="Show Button Text",
        description="When enabled the Header Button will Show A Text",
        default=False)

    button_toggle: BoolProperty(
        name="Show Button",
        description="When enabled the Header Button will Show",
        default=True)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, 'button_toggle') 
        layout.prop(self, 'button_text')
        layout.prop(self, 'camera_clipping') 
        layout.prop(self, 'clip_start_factor') 
        layout.prop(self, 'clip_end_factor') 


classes = (
    ClippingAssistant,
    ClippingAssistant_Preferences,
    )

def register():   
    [bpy.utils.register_class(c) for c in classes]  
    bpy.types.TOPBAR_HT_upper_bar.prepend(draw_button)


def unregister():
    bpy.types.TOPBAR_HT_upper_bar.remove(draw_button)
    [bpy.utils.unregister_class(c) for c in classes]
    # Unsubscribe and remove handle
    #unsubscribe_to_obj(subscription_owner)

if __name__ == "__main__":
    register()
