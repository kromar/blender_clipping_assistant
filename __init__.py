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


def get_min_dimension(dimension_list):
    '''
    Find the minimum non-zero dimension value across all dimension vectors in the list.
    Uses a small epsilon for float comparison against zero.
    Returns a default small positive value (0.001) if no positive dimensions are found.
    '''
    # Check if the list is actually populated before iterating
    if not dimension_list:
        return 0.001 # Default if no dimensions provided

    # Create a generator yielding only dimensions significantly greater than zero
    # Assumes dimension_list contains iterable vectors (like Blender's obj.dimensions)
    positive_dims = (dim for vec in dimension_list for dim in vec if dim > 1e-6)

    try:
        # Find the minimum value from the generator
        return min(positive_dims)
    except ValueError:
        # min() raises ValueError if the generator yields no items
        return 0.001


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
        print("=" * 40, end='\n\n')
        

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


def get_object_dimensions_and_locations(context):  
    """Gets the dimensions and locations of selected objects, or the active object if none are selected."""
    selected_objects = context.selected_objects
    active_object = context.active_object

    # Determine the target objects
    target_objects = selected_objects
    if not target_objects and active_object:
        target_objects = [active_object] # Use a list containing the active object

    if prefs().debug_output:
        print(f"\nActive object: {active_object.name if active_object else 'None'}, type: {active_object.type if active_object else 'None'}")
        print(f"  Selected objects: {[(obj.name, obj.type) for obj in selected_objects]}")
        print(f"  Target objects for data: {[(obj.name, obj.type) for obj in target_objects]}")
        
    obj_dimensions = [obj.dimensions for obj in target_objects]
    obj_locations = [obj.location for obj in target_objects]
    
    return obj_dimensions, obj_locations

    
def calculate_clipping(context, view_distance): 
    prefs_ = prefs() # Get prefs once
    if prefs_.debug_profiling:
        print('-' *40)
        start_time = profiler(time.perf_counter(), "Start calculate_clipping") 

    obj_dimensions, obj_locations = get_object_dimensions_and_locations(context)
    if prefs_.debug_profiling:
       start_time =  profiler(start_time, "Retrieved object dimensions and locations")

    # --- Early exit or default calculation if no objects ---
    if not obj_dimensions: # If no dimensions, locations will also be empty
        if prefs_.debug_output:
            print("No target objects found. Using default clipping based on view distance.")
        # Calculate clipping based only on view distance and factors
        minClipping = view_distance * prefs_.clip_start_factor
        maxClipping = view_distance * prefs_.clip_end_factor
        # Ensure minimum clipping values to prevent issues
        minClipping = max(minClipping, prefs_.clip_start_factor) # Avoid zero or negative clip start
        maxClipping = max(maxClipping, minClipping + prefs_.clip_end_factor) # Ensure clip end is after clip start

        if prefs_.debug_profiling:
            profiler(start_time, "Finished calculate_clipping (no objects)")
            print('-' * 40)
        return minClipping, maxClipping
    # --- End Early Exit ---


    # --- Calculate Proximity ---
    selected_objects_proximity = 0.0
    min_loc_vec = None
    max_loc_vec = None
    if len(obj_locations) > 1:
        # Store min/max vectors to avoid recalculating
        min_loc_vec = min(obj_locations)
        max_loc_vec = max(obj_locations)
        selected_objects_proximity = (max_loc_vec - min_loc_vec).length
    elif len(obj_locations) == 1:
         # Assign for consistent debug output later
         min_loc_vec = max_loc_vec = obj_locations[0]

    if prefs_.debug_output:
        print(f'Objects proximity: {selected_objects_proximity:.4f}')
        # Check if vectors were assigned before accessing .length
        if min_loc_vec is not None:
             print(f'  Min Loc Vec: {min_loc_vec} (dist: {min_loc_vec.length:.4f})')
        if max_loc_vec is not None:
             print(f'  Max Loc Vec: {max_loc_vec} (dist: {max_loc_vec.length:.4f})')

    if prefs_.debug_profiling:
        start_time = profiler(start_time, "Calculated selected objects proximity")
    # --- End Proximity ---

    # --- Calculate Clipping ---
    max_dim_value = 1.0 # Initialize here for broader scope
    min_dim_value = 0.0 

    # Flatten the list of dimensions and find the max
    # Use a generator expression for efficiency, remove redundant isinstance check
    try:
        all_dims_gen = (d for dim_vec in obj_dimensions for d in dim_vec)
        max_dim_value = max(all_dims_gen)
    except ValueError:
        pass # Keep max_dim_value = 0.0 if no dimensions found

    # Find min non-zero dimension value across all objects using the corrected helper
    min_dim_value = get_min_dimension(obj_dimensions)

    maxClipping = (max_dim_value + (view_distance * prefs_.clip_end_factor)) + selected_objects_proximity
    # Using the structure from the original logic for minClipping: (min_dim * view_distance) * factor
    minClipping = (min_dim_value * view_distance) * prefs_.clip_start_factor

    if prefs_.debug_output:
            print(f"\nUsing object scale:")
            print(f"Max Clipping: {maxClipping}")
            print(f"  Max Dimension Value: {max_dim_value}")
            print("   View_distance:", view_distance)
            print("   prefs_.clip_end_factor:", prefs_.clip_end_factor)
            print("   selected_objects_proximity:", selected_objects_proximity)

            print(f"Min Clipping: {minClipping}")
            print(f"  Min Dimension Value (non-zero): {min_dim_value}")
            print("   View_distance:", view_distance)
            print("   prefs_.clip_start_factor:", prefs_.clip_start_factor)

    if prefs_.debug_profiling:
        start_time = profiler(start_time, "Calculated initial min/max clipping")
    # --- End Clipping Calculation ---

    if prefs_.debug_output:
        print(f"\nMax Object Dimension Overall: {max_dim_value}")
        print(f"View Distance: {view_distance}")
        print(f"Selected Objects Proximity: {selected_objects_proximity}")
        print(f"  Final Min Clipping: {minClipping}")
        print(f"  Final Max Clipping: {maxClipping}")

    if prefs_.debug_profiling:
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
