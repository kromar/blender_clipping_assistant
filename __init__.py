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
    "version": (2, 0, 7),
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
    return masked_list[0][min_index]


def apply_clipping():    
    if prefs().debug_profiling:
        total_time = profiler(time.perf_counter(), "Start Total debug_profiling")
        start_time = profiler(time.perf_counter(), "Start Object debug_profiling")
    
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
                        
                        if prefs().auto_clipping: 
                            #set viewport clipping
                            if prefs().debug_profiling:
                                start_time = profiler(start_time, "apply_clipping") 
                            print("\n\nDISTANCE: ", distance)
                            minClipping, maxClipping = calculate_clipping(distance)                                
                        else:
                            minClipping, maxClipping = prefs().clip_start_distance, prefs().clip_end_distance                        
                        

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
        

def get_outliner_objects():
    def get_outliner_area(context):
        for area in context.screen.areas:
            if area is None:
                continue
            if area.type != 'OUTLINER':
                continue
            return area

    def get_outliner_window(area):
        for region in area.regions:
            if region.type != 'WINDOW':
                continue
            return region

    # we will override context to be able to access selected_ids

    # assuming that context is defined
    outliner_area = get_outliner_area(bpy.context)
    outliner_window = get_outliner_window(outliner_area)

    # deprecated since 3.2 but easy to use
    context_overridden = bpy.context.copy()
    context_overridden['area'] = outliner_area
    context_overridden['region'] = outliner_window

    # @brockmann's solution can then be used to output a nice dictionary
    print("OVERRIDE: ", context_overridden['active_object'])       
    return context_overridden['active_object']   



def calculate_clipping(distance=0):  
    if prefs().debug_profiling:
        start_time = profiler(time.perf_counter(), "Start calculate_clipping") 
    
    outliner_object = get_outliner_objects()
    print("ALTERNATE method: ", outliner_object.name, bpy.context.active_object.name, bpy.context.selected_objects)

    if bpy.context.selected_objects:
        objLocation = [obj.location for obj in bpy.context.selected_objects] 
        objDimension = [obj.dimensions for obj in bpy.context.selected_objects]        
        if prefs().debug_profiling:
            start_time = profiler(start_time, "transforms")

        minClipping = (min_list_value(objDimension) + distance) /100 / prefs().clip_start_factor
        if prefs().debug_profiling:
            start_time = profiler(start_time, "minClipping")

        # when having multiple selected obejcts and they are far appart the distance between them needs to be considered
        # to adjust the max clipping distance
        #selected_objects_proximity = object_distance(min(objLocation), max(objLocation))
        selected_objects_proximity = (max(objLocation) - min(objLocation)).length
        
        maxClipping = (max(max(objDimension)) + selected_objects_proximity + distance) * prefs().clip_end_factor        
        if prefs().debug_profiling:
            start_time = profiler(start_time, "maxClipping")
        
        # fallback if objects without dimensions are selected
        if not minClipping:
            minClipping = distance / prefs().clip_start_factor * 0.1
        if not maxClipping:
            maxClipping = distance * prefs().clip_end_factor
        
        if prefs().debug_profiling:
            print("\nmin-max: ", minClipping, "<<=====>>", maxClipping)
            print("view distance: ", distance)
            print("selected_objects_proximity: ", selected_objects_proximity, end='\n')   

        return minClipping, maxClipping   
    else:
        return 0.1*distance, 100*distance
    
    """ elif not bpy.context.selected_objects and bpy.context.active_object:
        print("ALTERNATE method 22: ", bpy.context.active_object, bpy.context.selected_objects)
        return  """



class ClippingAssistant(Operator):
    bl_idname = "scene.clipping_assistant"
    bl_label = "Toggle Automatic Clipping"
    bl_description = "Start and End Clipping Distance of Camera(s)"
    bl_options = {"REGISTER", "UNDO"}
    

    ob_type = ['MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'HAIR', 
                'POINTCLOUD', 'VOLUME', 'GPENCIL', 'ARMATURE', 'LATTICE']  
    @classmethod
    def poll(cls, context):      
        return context.selected_objects or context.active_object
    
    def execute(self, context):
        global clipping_active
        wm = context.window_manager   
        if clipping_active:
            print("Clipping Assistant: Disable Auto Update")
            clipping_active = False                     
            return {'FINISHED'}
        else:
            print("Clipping Assistant: Add Auto Update")
            wm.modal_handler_add(self)
            clipping_active = True
            return {'RUNNING_MODAL'}

    def cancel(self, context) -> None:
        global clipping_active   
        clipping_active = False     
        return None

    def modal(self, context, event): 
        global clipping_active
        if clipping_active:
            if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'TRACKPADZOOM', 'LEFTMOUSE', 'MIDDLEMOUSE', 'RIGHTMOUSE'} or event.ctrl or event.shift or event.alt:                
                for obj in context.selected_objects:
                    if obj.type in self.ob_type:  
                        apply_clipping()   
                if bpy.context.active_object:
                    apply_clipping()  
            return {'PASS_THROUGH'}
        else:
            print("Clipping Assistant: Stop auto update")  
            clipping_active = False                
            return {'FINISHED'}


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

    auto_clipping: BoolProperty(
        name="Auto Clipping",
        description="Adjust clipping distance automaticly on selected context",
        default=True)

    clip_start_factor: FloatProperty(
        name="Clip Start Divider",
        description="Value to calculate Clip Start, the higher the value the smaller the Clip Start Distance",
        default=0.05,
        min = 0.001,
        soft_min = 0.01,
        soft_max=0.1,
        step=1,
        subtype='FACTOR') 

    clip_end_factor: FloatProperty(
        name="Clip End Multiplier",
        description="Value to calculate Clip End, the higher the value the bigger the Clip End Distance",
        default=2,
        min = 0.01,
        soft_max=4,
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
        
    debug_profiling: BoolProperty(
        name="Debug: Profiling",
        description="enable some performance output for debuggung",
        default=False)
    

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.prop(self, 'camera_clipping') 
        layout.prop(self, 'volume_clipping') 
        
        layout.prop(self, 'auto_clipping') 
        column = layout.box()
        if self.auto_clipping:
            column.prop(self, 'clip_start_factor', slider=True)
            column.prop(self, 'clip_end_factor', slider=True)
        else:
            column.prop(self, 'clip_start_distance', slider=True)
            column.prop(self, 'clip_end_distance', slider=True)

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
