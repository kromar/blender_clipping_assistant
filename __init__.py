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
from bpy.props import FloatProperty, BoolProperty

from bpy.app.handlers import persistent


bl_info = {
    "name": "Clipping Assistant",
    "description": "Assistant to set Viewport and Camera Clipping Distance",
    "author": "Daniel Grauer",
    "version": (1, 1, 4),
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


subscription_owner = object()
# Subscribe to the context object (mesh)
def subscribe_to_obj(subscription_owner):
    """ if subscription_owner.type != 'MESH':
        return """

    subscribe_to = bpy.types.LayerObjects, "active"

    bpy.msgbus.subscribe_rna(
        key=subscribe_to,
        # owner of msgbus subcribe (for clearing later)
        owner=subscription_owner,
        # Args passed to callback function (tuple)
        args=(subscription_owner,),
        # Callback function for property update
        notify=calculate_clipping,        
        options={"PERSISTENT"}
    )
    
    if load_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_handler)


def unsubscribe_to_obj(subscription_owner):
    # Clear all subscribers by this owner
    if subscription_owner is not None:
        bpy.msgbus.clear_by_owner(subscription_owner)

    # Unregister the persistent handler.
    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)


@persistent
def load_handler():
    subscribe_to_obj(subscription_owner)



# Callback function for location changes
def calculate_clipping():
    objPosition = []
    objDimension = []    

    for obj in bpy.context.selected_objects:
        
        view_distance = calc_view_matrix(obj)
        objPosition.append(obj.location)
        objDimension.append(obj.dimensions)  

        
              
    selected_objects_proximity = distance_vec(min(objPosition), max(objPosition))

    minClipping = min_list_value(objDimension) / prefs().clip_start_factor
    maxClipping = selected_objects_proximity + max(max(objDimension)) * view_distance #* pref.clip_end_factor
    
    # fallback if objects without dimensions are selected
    if not minClipping:
        minClipping = view_distance / prefs().clip_start_factor *.1
    if not maxClipping:
        maxClipping = view_distance * prefs().clip_end_factor

    print("min: ", minClipping)
    print("max: ", maxClipping)
    print("prox: ", selected_objects_proximity)
    print("dist: ", view_distance, end=" \n ")

    return minClipping, maxClipping


def apply_clipping():
    minClipping, maxClipping = calculate_clipping()
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
                            space.clip_start = minClipping
                            space.clip_end = maxClipping
                            #set camera clipping                            
                            if space.camera and prefs().camera_clipping:
                                #print("camera: ", space.camera.name)
                                bpy.data.cameras[space.camera.name].clip_start = minClipping
                                bpy.data.cameras[space.camera.name].clip_end = maxClipping


def draw_button(self, context):    
    if prefs().button_toggle:
        if context.region.alignment == 'RIGHT':
            layout = self.layout
            row = layout.row(align=True)           
            if prefs().button_text:
                row.operator(operator="scene.clipping_assistant_start", text="Start", icon='VIEW_CAMERA', emboss=True, depress=False)
                row.operator(operator="scene.clipping_assistant_end", text="End", icon='CANCEL', emboss=True, depress=False)
            else:
                row.operator(operator="scene.clipping_assistant_start", text="", icon='VIEW_CAMERA', emboss=True, depress=False)
                row.operator(operator="scene.clipping_assistant_end", text="", icon='CANCEL', emboss=True, depress=False)


def calc_view_matrix(obj):   
    
    bound_matrix = mathutils.Matrix()  
    bounds = obj.bound_box
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':             
                view_3d = area.spaces.active.region_3d
                #print("window_matrix: ", view_3d.window_matrix)
                #print("view_matrix: ", view_3d.view_matrix)
                print("perspective_matrix: ", view_3d.perspective_matrix)
                print("view_location: ", view_3d.view_location)
                print("view_rotation: ", view_3d.view_rotation.to_euler())
                print("view_distance: ", view_3d.view_distance)
                
            
                for i,v in enumerate(bounds):
                    #print(bounds[i][:])                        
                    bound_matrix[0].x = bounds[i][0]
                    bound_matrix[1].y = bounds[i][1]
                    bound_matrix[2].z = bounds[i][2]                                           
                    
                    print(bound_matrix * obj.matrix_world)
                    print("\n")
                
                return view_3d.view_distance
                

class ClippingAssistant_OT_register(bpy.types.Operator):
    bl_idname = "scene.clipping_assistant_start"
    bl_label = "start"
    bl_description = "Start and End Clipping Distance of Camera(s)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):        
        #calculate_clipping()
        return

    def execute(self, context):
        calculate_clipping()
        #subscribe_to_obj(subscription_owner)
        return {"FINISHED"}


class ClippingAssistant_OT_unregister(bpy.types.Operator):
    bl_idname = "scene.clipping_assistant_end"
    bl_label = "end"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):     
        unsubscribe_to_obj(subscription_owner)
        return {"FINISHED"}

      

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
    ClippingAssistant_OT_register,
    ClippingAssistant_OT_unregister,
    ClippingAssistantPreferences,
    )

def register():   
    [bpy.utils.register_class(c) for c in classes]  
    bpy.types.TOPBAR_HT_upper_bar.prepend(draw_button)


def unregister():
    bpy.types.TOPBAR_HT_upper_bar.remove(draw_button)
    [bpy.utils.unregister_class(c) for c in classes]
    # Unsubscribe and remove handle
    unsubscribe_to_obj(subscription_owner)

if __name__ == "__main__":
    register()
