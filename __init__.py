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
    "version": (2, 2, 0),
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
    ''' Return the minimum non-zero value in a list. 
        Objects can have 0 size in certain dimensions (e.g., planes or edges), 
        so 0 values are ignored to avoid invalid minimum object sizes.
    '''
    filtered_list = [value for value in input_list[0] if value > 0]
    if filtered_list is None:
        return None  # Handle case where all values are zero
    
    min_value = min(filtered_list)
    return min_value


def apply_clipping(context):
    if prefs().debug_profiling:
        total_time = profiler(time.perf_counter(), "Start Total Profiling")
        calc_time = profiler(time.perf_counter(), "Start Profiling")
        print('-' * 40)

    minClipping, maxClipping = None, None

    # Access the active 3D view directly
    #context = bpy.context
    area = next((area for area in context.screen.areas if area.type == 'VIEW_3D'), None)
    if area is None:
        return


    if prefs().debug_profiling:
        calc_time = profiler(calc_time, "Start Clipping Calculation")
        
    space = area.spaces.active

    if prefs().auto_clipping:
        view_3d = space.region_3d
        view_distance = view_3d.view_distance
        if prefs().debug_profiling:
            calc_time = profiler(calc_time, "view_distance")

        minClipping, maxClipping = calculate_clipping(context, view_distance)
        if prefs().debug_profiling:
            calc_time = profiler(calc_time, "auto_clipping")
    else:
        minClipping, maxClipping = prefs().clip_start_distance, prefs().clip_end_distance   
        if prefs().debug_profiling:
            calc_time = profiler(calc_time, "no auto_clipping")

    if prefs().debug_profiling:
        calc_time = profiler(calc_time, "End Clipping Calculation")


    # Apply viewport clipping
    space.clip_start = minClipping
    space.clip_end = maxClipping
    
    if prefs().debug_output:
       print('-' * 40)
       print(f"Set Viewport Clipping: {minClipping:.4f} <-> {maxClipping:.4f}")
       print('=' * 40)

    if prefs().debug_profiling:
        calc_time = profiler(calc_time, "Viewport Clipping Applied")

    # Apply volumetric clipping
    if prefs().volume_clipping:
        scene = context.scene
        scene.eevee.volumetric_start = minClipping
        scene.eevee.volumetric_end = maxClipping

    if prefs().debug_profiling:
        calc_time = profiler(calc_time, "Volumetric Clipping Applied")

    # Apply camera clipping
    if space.camera and prefs().camera_clipping:
        camera = bpy.data.cameras.get(space.camera.name)
        if camera:
            camera.clip_start = minClipping
            camera.clip_end = maxClipping

    if prefs().debug_profiling:
        calc_time = profiler(calc_time, "Camera Clipping Applied")

    if prefs().debug_profiling:
        print('-' * 40)
        total_time = profiler(total_time, "Total clipping time")
        print("=" * 40)
        

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


def get_clipping(context):  
    selected_objects = context.selected_objects
    active_object = context.active_object

    if prefs().debug_output:
        print(f"\nActive object: {active_object.name}, type: {active_object.type}")
        print(f"  Selected objects: {[(obj.name, obj.type) for obj in selected_objects]}")
        
    obj_dimension = [obj.dimensions for obj in selected_objects] if selected_objects else []
    obj_location = [obj.location for obj in selected_objects] if selected_objects else []

    if not selected_objects and active_object:
        obj_dimension = [active_object.dimensions]
        obj_location = [active_object.location]

    return obj_dimension, obj_location
    
    
def calculate_clipping(context, view_distance): 
    if prefs().debug_profiling:
        print('-' *40)
        start_time = profiler(time.perf_counter(), "Start calculate_clipping") 

    obj_dimension, obj_location = get_clipping(context)
    if prefs().debug_profiling:
       start_time =  profiler(start_time, "Retrieved object dimensions and locations")

    # when having multiple selected objects and they are far apart, the distance between them needs to be considered
    # to adjust the max clipping distance
    selected_objects_proximity = (max(obj_location) - min(obj_location)).length  
    if prefs().debug_output:        
        print('Objects proximity: {:.4f}'.format(selected_objects_proximity), 
              '\n  Max: {:.4f}'.format(max(obj_location).length), 
              '\n  Min: {:.4f}'.format(min(obj_location).length))

    if prefs().debug_profiling:
        start_time = profiler(start_time, "Calculated selected objects proximity")

    # TODO: "not min/max - clipping" fallback if objects without dimensions are selected
    # --> check if object has dimensions to improve calculation
    if prefs().use_object_scale:
        maxClipping = ((max(max(obj_dimension)) + (view_distance * prefs().clip_end_factor)) + selected_objects_proximity)     
        minClipping = ((min_list_value(obj_dimension) * view_distance)) * prefs().clip_start_factor  
    else:
        maxClipping = view_distance * prefs().clip_end_factor + selected_objects_proximity
        minClipping = view_distance * prefs().clip_start_factor  

    if prefs().debug_profiling:
        start_time = profiler(start_time, "Calculated min and max clipping distances")

    # Use fallback values for minClipping and maxClipping only if they are None
    if maxClipping is None:
        maxClipping = view_distance * prefs().clip_end_factor
        if prefs().debug_output:
            print(f"maxClipping fallback: {maxClipping:.4f}")

    if minClipping is None:
        minClipping = view_distance * prefs().clip_start_factor
        if prefs().debug_output:
            print(f"minClipping fallback: {minClipping:.4f}")
   
    if prefs().debug_profiling:
        start_time = profiler(start_time, "min and max fallbakcs")

    if prefs().debug_output:
        print("\nmax obj_dimension: {:.4f}".format(max(max(obj_dimension))))     
        print("view_distance: {:.4f}".format(view_distance))   
        print("selected_objects_proximity: {:.4f}".format(selected_objects_proximity)) 
        print("  min clipping: {:.4f}".format(minClipping))
        print("  max clipping: {:.4f}".format(maxClipping))

    if prefs().debug_profiling:
        start_time = profiler(start_time, "Finished calculate_clipping")
        print('-' *40)

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

    ob_type = ['MESH', 'CURVE', 'SURFACE', 'META', 
               'FONT', 'HAIR', 'POINTCLOUD', 'VOLUME', 
               'GPENCIL', 'ARMATURE', 'LATTICE', 'EMPTY']
    
    trigger_event_types = ['BUTTON4MOUSE', 'BUTTON5MOUSE', 'BUTTON6MOUSE', 'BUTTON7MOUSE',
                            'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'MIDDLEMOUSE',
                           'TRACKPADZOOM', 'TRACKPADPAN', 'MOUSEROTATE', 
                           #'INBETWEEN_MOUSEMOVE', 
                           'SELECTMOUSE', 
                           #'MOUSEMOVE',
                           ]    
    key_trigger_event_types = ['LEFTCTRL', 'RIGHTCTRL', 'LEFTSHIFT', 'RIGHTSHIFT', 'LEFTALT', 'RIGHTALT']   
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
            
            print("Clipping Assistant: Enable Auto Update")
            wm.modal_handler_add(self)
            clipping_active = True
            # detect the mouse button used for selection, this causes conflicts in certain scenarios when interacting with gizmos with LMB  
            #   0 == LMB, 1 == RMB          
            active_keymap = bpy.context.preferences.keymap.active_keyconfig            
            preferences = bpy.context.window_manager.keyconfigs[active_keymap].preferences

            if 'select_mouse' in preferences:
                right_click_select = preferences['select_mouse']
            else:
                right_click_select = None

            intersection = set(self.right_click_event_types).intersection(self.trigger_event_types)            
            if intersection: 
                if right_click_select == 0:                 
                    self.trigger_event_types = set(self.trigger_event_types) - set(intersection)
            else:
                if right_click_select == 1:
                    self.trigger_event_types += self.right_click_event_types
            #print("trigger events: ", self.trigger_event_types)
                
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
                selected_objects = [obj for obj in context.selected_objects if obj.type in self.ob_type]
                if selected_objects or (context.active_object and context.active_object.type in self.ob_type):
                    if prefs().debug_output:
                        print("Clipping Assistant: Auto Update applied to selected objects")   
                        print('Event type:', event.type, event.value)
                    
                    apply_clipping(context)  

            return {'PASS_THROUGH'}
        else:
            print("Clipping Assistant: Stop auto update")  
            clipping_active = False           
            return {'FINISHED'}
        


def profiler(start_time=None, message=None): 
    """Measure and print elapsed time with 4 decimal precision."""
    if prefs().debug_profiling is False:
        return start_time  # Skip profiling if debug_profiling is disabled

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
        
        # Display the clip start and end values
        if clipping_active:
            try:
                scene = context.scene
                unit_settings = scene.unit_settings
                scale_length = scene.unit_settings.scale_length

                if unit_settings.system == 'METRIC':
                    scale_length *= 100.0
                elif unit_settings.system == 'IMPERIAL':
                    scale_length *= 3.28084

                clip_start_value = None
                clip_end_value = None
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        space = area.spaces.active
                        clip_start_value = space.clip_start * scale_length
                        clip_end_value = space.clip_end * scale_length
                
                row = layout.row(align=True)
                row.label(text=f"[{clip_start_value:.2f} | {clip_end_value:.2f}]")

            except (KeyError, IndexError, AttributeError):
                layout.row(align=True).label(text="Clip: N/A")
                
        row.operator(
            operator="scene.clipping_assistant", 
            text="", 
            icon='VIEW_CAMERA', 
            emboss=True, 
            depress=clipping_active
        )


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
