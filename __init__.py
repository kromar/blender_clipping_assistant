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
from bpy.props import BoolProperty, IntProperty


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

clipping_active = False


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




# Callback function for location changes
def calculate_clipping(distance):
    objPosition = []
    objDimension = []    

    for obj in bpy.context.selected_objects:
        objPosition.append(obj.location)
        objDimension.append(obj.dimensions) 
    
    if bpy.context.selected_objects:
        selected_objects_proximity = distance_vec(min(objPosition), max(objPosition))
        minClipping = min_list_value(objDimension) / 100 / prefs().clip_start_factor 
        maxClipping = (max(max(objDimension)) + selected_objects_proximity + distance) * prefs().clip_end_factor
        
        # fallback if objects without dimensions are selected
        if not minClipping:
            minClipping = distance / prefs().clip_start_factor * 0.1
        if not maxClipping:
            maxClipping = distance * prefs().clip_end_factor

        """ print("\nview distance: ", distance)
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
                    view_3d = area.spaces.active.region_3d
                    distance = view_3d.view_distance
                    #print("area: ", area.type , end='\n')
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            #set viewport clipping
                            if bpy.context.selected_objects:
                                #print(bpy.context.selected_objects)
                                minClipping, maxClipping = calculate_clipping(distance)
                                #print("\nset clipping: ", minClipping, maxClipping)
                                space.clip_start = minClipping
                                space.clip_end = maxClipping
                                #set camera clipping                            
                                if space.camera and prefs().camera_clipping:
                                    #print("camera: ", space.camera.name)
                                    bpy.data.cameras[space.camera.name].clip_start = minClipping
                                    bpy.data.cameras[space.camera.name].clip_end = maxClipping



class ClippingAssistant(Operator):
    bl_idname = "scene.clipping_assistant"
    bl_label = "Toggle Automatic Clipping"
    bl_description = "Start and End Clipping Distance of Camera(s)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):   
        return context.selected_objects
    
    def execute(self, context):
        global clipping_active
        wm = context.window_manager   
        if clipping_active:
            print("Disable Auto Update")
            clipping_active = False                     
            return {'CANCELLED'}
        else:
            print("Add Auto Update")
            wm.modal_handler_add(self)
            clipping_active = True
            return {'RUNNING_MODAL'}

    def cancel(self, context):        
        return {'CANCELLED'}

    def modal(self, context, event):   
        if context.selected_objects:
             apply_clipping()

        if clipping_active:
            if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'TRACKPADZOOM'}:
                apply_clipping()        
            return {'PASS_THROUGH'}
        else:
            print("Stop auto update")                   
            return {'CANCELLED'}


def draw_button(self, context): 
    global clipping_active   
    if context.region.alignment == 'RIGHT':
        layout = self.layout
        row = layout.row(align=True)   
        if clipping_active:
            row.operator(operator="scene.clipping_assistant", text="", icon='VIEW_CAMERA', emboss=True, depress=True)
        else:
            row.operator(operator="scene.clipping_assistant", text="", icon='VIEW_CAMERA', emboss=True, depress=False)
          

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
    

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
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
