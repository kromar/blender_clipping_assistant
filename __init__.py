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
import time
from bpy.types import Operator
from . import preferences


bl_info = {
    "name": "Clipping Assistant",
    "description": "Assistant to set Viewport and Camera Clipping Distance",
    "author": "Daniel Grauer",
    "version": (2, 1, 1),
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
    ''' Find the maximum value in a list and return the index and the value '''
    input_array = numpy.array(input_list)
    max_index = input_array.argmax()
    max_value = input_array[max_index]
    return max_index, max_value


def min_list_value(input_list):
    ''' Return the minimum non-zero value in a list and its index. 
        Objects can have 0 size in certain dimensions (e.g., planes or edges), 
        so 0 values are ignored to avoid invalid minimum object sizes.
    '''
    filtered_list = [value for value in input_list[0] if value > 0]
    if not filtered_list:
        return None, None  # Handle case where all values are zero
    min_value = min(filtered_list)
    min_index = input_list[0].index(min_value)
    return min_index, min_value


def apply_clipping():    
    if prefs().debug_profiling:
        total_time = profiler(time.perf_counter(), "Start Total debug_profiling")
        start_time = profiler(time.perf_counter(), "Start Object debug_profiling")
    
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type in {'VIEW_3D'}:                    
                view_3d = area.spaces.active.region_3d                    
                view_distance = view_3d.view_distance
                #print("area: ", area.type , end='\n')
                for space in area.spaces:                    
                    if space.type in {'VIEW_3D'}:
                        if prefs().debug_profiling:
                            start_time = profiler(start_time, "space.type in")                     
                        

                        # Viewport clipping
                        if prefs().auto_clipping: 
                            if prefs().debug_profiling:
                                start_time = profiler(start_time, "apply_clipping") 
                                print("\n\nDISTANCE: {:.4f}".format(view_distance))
                            minClipping, maxClipping = calculate_clipping(view_distance)                               
                        else:
                            minClipping, maxClipping = prefs().clip_start_distance, prefs().clip_end_distance                           
                        if prefs().debug_profiling:
                            start_time = profiler(start_time, "calculate_clipping") 
                            print("\nset clipping: ", minClipping, maxClipping)
                        
                        space.clip_start = minClipping #TODO: why do we lose the gizmo when running this line?
                        space.clip_end = maxClipping
                        # Volumetric clipping
                        if prefs().volume_clipping:
                            bpy.context.scene.eevee.volumetric_start = minClipping
                            bpy.context.scene.eevee.volumetric_end = maxClipping
                        
                        if prefs().debug_profiling:
                            start_time = profiler(start_time, "clip") 
                        
                        # Camera clipping                            
                        if space.camera and prefs().camera_clipping:
                            #print("camera: ", space.camera.name)
                            bpy.data.cameras[space.camera.name].clip_start = minClipping
                            bpy.data.cameras[space.camera.name].clip_end = maxClipping
                        
                        if prefs().debug_profiling:
                            print("-"*40) 
    
    if prefs().debug_profiling:
        total_time = profiler(total_time, "Fotal clipping time") 
        print("="*40)
        

def get_outliner_objects():
    '''Retrieve the active object from the Outliner area.'''
    for area in bpy.context.screen.areas:
        if area.type == 'OUTLINER':
            for region in area.regions:
                if region.type == 'WINDOW':
                    context_overridden = bpy.context.copy()
                    context_overridden['area'] = area
                    context_overridden['region'] = region
                    return context_overridden.get('active_object')
    return None


def get_clipping(view_distance):  
    selected_obj = bpy.context.selected_objects
    active_obj = bpy.context.active_object

    if prefs().debug_profiling:
        print(f"Active object: {active_obj.name if active_obj else 'None'}")
        print(f"Selected objects: {[obj.name for obj in selected_obj]}")

    if selected_obj and active_obj in selected_obj:
        obj_dimension = [obj.dimensions for obj in selected_obj]
        obj_location = [obj.location for obj in selected_obj]
    else:
        obj_dimension = [active_obj.dimensions] if active_obj else []
        obj_location = [active_obj.location] if active_obj else []

    return obj_dimension, obj_location
    
    
def calculate_clipping(view_distance): 
    obj_dimension, obj_location = get_clipping(view_distance)
    if prefs().debug_profiling:
        start_time = profiler(time.perf_counter(), "Start calculate_clipping") 
    # when having multiple selected obejcts and they are far appart the distance between them needs to be considered
    # to adjust the max clipping distance
    
    selected_objects_proximity = (max(obj_location) - min(obj_location)).length  
    if prefs().debug_profiling:
        print('Objects proximity: ', selected_objects_proximity,'\n__ Max: ',  max(obj_location), ' Min: ', min(obj_location))

    # TODO: "not min/max - clipping" fallback if objects without dimensions are selected  # -->  check if object has dimentions to improve calculation
    if prefs().use_object_scale:
        maxClipping = ((max(max(obj_dimension)) + (view_distance * prefs().clip_end_factor)) + selected_objects_proximity)     
        minClipping = ((min_list_value(obj_dimension) * view_distance)) * prefs().clip_start_factor  
    else:
        maxClipping = view_distance * prefs().clip_end_factor + selected_objects_proximity
        minClipping = view_distance * prefs().clip_start_factor  


    if not maxClipping:
        maxClipping = view_distance * prefs().clip_end_factor   
        print("maxClipping fallback: ", maxClipping)
      
    if not minClipping:
        minClipping = view_distance * prefs().clip_start_factor
        print("minClipping fallback: ", minClipping)
           
        
    if  prefs().debug_profiling:
        #print("\n\nobj_location: ", obj_location)     
           
        #print("\n\nmin_list_value(obj_dimension): ", min_list_value(obj_dimension)) 
        #print("view distance: ", view_distance)   
        #print("min-max: ", minClipping, "<<=====>>", maxClipping)

        print("\n(max(max(obj_dimension): {:.4f}".format(max(max(obj_dimension))))     
        print("view_distance: {:.4f}".format(view_distance))   
        print("selected_objects_proximity: {:.4f}".format(selected_objects_proximity)) 
        print("min-max: {:.4f} <<=====>> {:.4f}".format(minClipping, maxClipping))  
    
    if prefs().debug_profiling:
        start_time = profiler(start_time, "calculate_clipping") 

    return minClipping, maxClipping


class ClippingAssistant(Operator):
    """
    Operator for managing automatic clipping distances in Blender.

    This class toggles automatic updates for viewport and camera clipping distances
    based on the dimensions and locations of selected or active objects. It also
    object_types = ['MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'HAIR', 'POINTCLOUD', 'VOLUME', 'GPENCIL', 'ARMATURE', 'LATTICE']    
    during navigation or object manipulation.

    Attributes:
        ob_type (list): List of object types supported for clipping adjustments.
        trigger_event_types (list): List of mouse and keyboard events that trigger updates.
        right_click_event_types (list): Events for right-click selection mode.
    """
    bl_idname = "scene.clipping_assistant"
    bl_label = "Toggle Automatic Clipping"
    bl_description = "Start and End Clipping Distance of Camera(s)"
    bl_options = {"REGISTER", "UNDO"}   

    ob_type = ['MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'HAIR', 'POINTCLOUD', 'VOLUME', 'GPENCIL', 'ARMATURE', 'LATTICE']    
    trigger_event_types = ['BUTTON4MOUSE', 'BUTTON5MOUSE', 'BUTTON6MOUSE', 'BUTTON7MOUSE',
                            'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'MIDDLEMOUSE', 'WHEELINMOUSE' , 'WHEELOUTMOUSE','SELECTMOUSE',
                           'TRACKPADZOOM', 'TRACKPADPAN',  
                           'MOUSEROTATE', 'WHEELINMOUSE', 'WHEELOUTMOUSE',
                           ]    
    right_click_event_types = ['LEFTMOUSE', 'RIGHTMOUSE']    

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
            # detect the mouse button used for selection, this causes conflicts in certain scenarios when interacting with gizmos with LMB  
            #   0 == LMB, 1 == RMB          
            active_keymap = bpy.context.preferences.keymap.active_keyconfig
            
            #try: # some keymaps do not contain the select_mouse property. This avoids errors with those keymaps
            preferences = bpy.context.window_manager.keyconfigs[active_keymap].preferences
            if 'select_mouse' in preferences:
                right_click_select = preferences['select_mouse']
            else:
                right_click_select = None
            intersection = set(self.right_click_event_types).intersection(self.trigger_event_types)            
            if intersection: 
                if right_click_select == 0:                    
                    #print("intersection: ", intersection) 
                    self.trigger_event_types = set(self.trigger_event_types) - set(intersection)
            else:
                if right_click_select == 1:
                    self.trigger_event_types += self.right_click_event_types
            #print("trigger events: ", self.trigger_event_types)
            """ except (KeyError, AttributeError):
                pass """
                
            return {'RUNNING_MODAL'}
        
    def cancel(self, context) -> None:
        global clipping_active   
        clipping_active = False     
        return None

    def modal(self, context, event): 
        global clipping_active
        if clipping_active:
            if (event.type in self.trigger_event_types
            or event.ctrl or event.shift or event.alt):  
                """ selected_objects = [obj for obj in context.selected_objects if obj.type in self.ob_type]
                if selected_objects or (bpy.context.active_object and bpy.context.active_object.type in self.ob_type):
                    print('Event type:', event.type)   
                    print("Clipping Assistant: Auto Update applied to batch")    """
                apply_clipping()  

            return {'PASS_THROUGH'}
        else:
            print("Clipping Assistant: Stop auto update")  
            clipping_active = False                
            return {'FINISHED'}
        


def profiler(start_time=None, message=None): 
    """Measure and print elapsed time with 4 decimal precision."""
    current_time = time.perf_counter()
    if start_time is not None:
        elapsed_time = current_time - start_time
        print(f"{elapsed_time * 1000:.4f} ms << {message}")
    else:
        print(f"debug_profiling: {message}")
    return current_time


def draw_button(self, context): 
    global clipping_active   
    if context.region.alignment == 'RIGHT':
        layout = self.layout
        row = layout.row(align=True)   
        if clipping_active:
            row.operator(operator="scene.clipping_assistant", text="", icon='VIEW_CAMERA', emboss=True, depress=True)
        else:
            row.operator(operator="scene.clipping_assistant", text="", icon='VIEW_CAMERA', emboss=True, depress=False)
          


classes = (
    ClippingAssistant,
    preferences.ClippingAssistant_Preferences,
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
