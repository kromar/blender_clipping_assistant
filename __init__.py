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

from cmath import nan
import bpy
import numpy
import time
from mathutils import Vector 
from bpy.types import AddonPreferences, Operator
from bpy.props import BoolProperty, IntProperty, FloatProperty


bl_info = {
    "name": "Clipping Assistant",
    "description": "Assistant to set Viewport and Camera Clipping Distance",
    "author": "Daniel Grauer",
    "version": (2, 0, 4),
    "blender": (2, 83, 0),
    "location": "TopBar",
    "category": "System",
    "wiki_url": "https://github.com/kromar/blender_clipping_assistant",
    "tracker_url": "https://github.com/kromar/blender_clipping_assistant/issues/new",
}

clipping_active = False
start_time = None

def prefs():
    ''' load addon preferences to reference in code'''
    user_preferences = bpy.context.preferences
    return user_preferences.addons[__package__].preferences 


def max_list_value(input_list):
    ''' find the biggest value in a list and return the index and the value'''
    i = numpy.argmax(input_list)
    v = input_list[i]
    return (i, v)


def min_list_value(input_list):
    ''' numpy.ma.masked_values(): Return a MaskedArray, masked where the data in array x are approximately equal to value.
        Masked_vales is used because objects can have 0 size in certain dimensions like a plane or a edge, 
        therefore its required to filter out 0 to avoid invalid minimum object sizes.
    '''
    filtered_value = 0
    masked_list = numpy.ma.masked_values(input_list, filtered_value)  #this seems to be expensive, how about popping all 0 values?
    min_index = numpy.argmin(masked_list[0])
    min_value = masked_list[0][min_index]
    return min_value


def distance_vec(point1: Vector, point2: Vector) -> float: 
        """Calculate distance between two points.""" 
        return (point2 - point1).length  


def apply_clipping():    
    if prefs().debug_profiling:
        total_time = profiler(time.perf_counter(), "Start Object debug_profiling")
        start_time = profiler(time.perf_counter(), "Start Object debug_profiling")

    ''' this part would be to update in all workspaces, however with the new dynamic method it is redundant.
        its also costs less to only update the active screen'''
    """ for workspace in bpy.data.workspaces:
        #print("workspaces:", workspace.name)
        for screen in workspace.screens:
            #print("screen: ", screen.name) """
    
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:

            if area.type in {'VIEW_3D'}:                    
                view_3d = area.spaces.active.region_3d                    
                distance = view_3d.view_distance
                #print("area: ", area.type , end='\n')
                for space in area.spaces:                    
                    if space.type in {'VIEW_3D'}:
                        if prefs().debug_profiling:
                            start_time = profiler(start_time, "space.type in")                     

                        #set viewport clipping
                        if bpy.context.selected_objects:
                            #print(bpy.context.selected_objects)
                            if prefs().debug_profiling:
                                start_time = profiler(start_time, "apply_clipping") 
                            minClipping, maxClipping = calculate_clipping(distance)
                            
                            if prefs().debug_profiling:
                                start_time = profiler(start_time, "calculate_clipping") 
                            #print("\nset clipping: ", minClipping, maxClipping)
                            space.clip_start = minClipping
                            space.clip_end = maxClipping
                            if prefs().volume_clipping:
                                bpy.context.scene.eevee.volumetric_start = minClipping
                                bpy.context.scene.eevee.volumetric_end = maxClipping
                            
                            if prefs().debug_profiling:
                                start_time = profiler(start_time, "clip") 
                            #set camera clipping                            
                            if space.camera and prefs().camera_clipping:
                                #print("camera: ", space.camera.name)
                                bpy.data.cameras[space.camera.name].clip_start = minClipping
                                bpy.data.cameras[space.camera.name].clip_end = maxClipping

                        
                        if prefs().debug_profiling:
                            print("="*80)
    
    if prefs().debug_profiling:
        total_time = profiler(total_time, "total time") 
        print("="*80)
            

def calculate_clipping(distance):   
    if prefs().debug_profiling:
        start_time = profiler(time.perf_counter(), "Start calculate_clipping") 
     
    objPosition = [obj.location for obj in bpy.context.selected_objects] 
    objDimension = [obj.dimensions for obj in bpy.context.selected_objects] 
    
    if prefs().debug_profiling:
        start_time = profiler(start_time, "transforms")


    if bpy.context.selected_objects:
        selected_objects_proximity = distance_vec(min(objPosition), max(objPosition))
        minClipping = (min_list_value(objDimension) + distance) /100 / prefs().clip_start_factor
        if prefs().debug_profiling:
            start_time = profiler(start_time, "minClipping")

        maxClipping = (max(max(objDimension)) + selected_objects_proximity + distance) * prefs().clip_end_factor
        if prefs().debug_profiling:
            start_time = profiler(start_time, "maxClipping")
        
        # fallback if objects without dimensions are selected
        if not minClipping:
            minClipping = distance / prefs().clip_start_factor * 0.1
        if not maxClipping:
            maxClipping = distance * prefs().clip_end_factor
        
        if prefs().debug_profiling:
            print("\nview distance: ", distance)
            print("objects proximity: ", selected_objects_proximity)
            print("min-max: ", minClipping, "<<=====>>", maxClipping)         
       
        
        return minClipping, maxClipping


class ClippingAssistant(Operator):
    bl_idname = "scene.clipping_assistant"
    bl_label = "Toggle Automatic Clipping"
    bl_description = "Start and End Clipping Distance of Camera(s)"
    bl_options = {"REGISTER", "UNDO"}

    ob_type = ['MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'HAIR', 
                'POINTCLOUD', 'VOLUME', 'GPENCIL', 'ARMATURE', 'LATTICE']  
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
        if clipping_active:
            if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'TRACKPADZOOM', 'LEFTMOUSE', 'MIDDLEMOUSE', 'RIGHTMOUSE'} or event.ctrl or event.shift or event.alt:                
                for obj in context.selected_objects:
                    if obj.type in self.ob_type:  
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

    clip_start_factor: FloatProperty(
        name="Clip Start Divider",
        description="Value to calculate Clip Start, the higher the value the smaller the Clip Start Distance",
        default=0.05,
        min = 0.01,
        soft_max=100,
        step=1,
        subtype='FACTOR') 

    clip_end_factor: FloatProperty(
        name="Clip End Multiplier",
        description="Value to calculate Clip End, the higher the value the bigger the Clip End Distance",
        default=2,
        min = 0.01,
        soft_max=100,
        step=1,
        subtype='FACTOR') 

    camera_clipping: BoolProperty(
        name="Apply Clipping To Active Camera",
        description="When enabled the clipping Distance of the Active Camera is adjusted as well as the Viewport Clip Distance",
        default=False)

    volume_clipping: BoolProperty(
        name="Apply Clipping To Volumetrics",
        description="Adapt Clipping distances of volumetric effects",
        default=True)
        
    debug_profiling: BoolProperty(
        name="Debug: Profiling",
        description="enable some performance output for debuggung",
        default=False)
    

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, 'camera_clipping') 
        layout.prop(self, 'volume_clipping') 
        layout.prop(self, 'clip_start_factor') 
        layout.prop(self, 'clip_end_factor') 
        layout.prop(self, 'debug_profiling') 


def profiler(start_time=False, string=None): 
    elapsed = time.perf_counter()
    measured_time = elapsed-start_time
    if start_time:
        print("{:.10f}".format(measured_time*1000), "ms << ", string)  
    else:
        print("debug_profiling: ", string)  
        
    start_time = time.perf_counter()
    return start_time  

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
