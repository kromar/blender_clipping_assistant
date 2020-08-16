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

bl_info = {
    "name": "camera_clipping_assistant",
    "description": "Assistant to set camera clipping distance",
    "author": "Daniel Grauer",
    "version": (1, 0, 0),
    "blender": (2, 83, 0),
    "location": "TopBar",
    "category": "System",
    "wiki_url": "https://github.com/kromar/blender_camera_clipping_assistant"
}

  

def draw_button(self, context):
    
    AC_active = True 
    if context.region.alignment == 'RIGHT':
        layout = self.layout
        row = layout.row(align=True)
        
        if AC_active:
            row.operator(operator="scene.auto_clipping", text="", icon='VIEW_CAMERA', emboss=True, depress=False)
            AC_active = False
        else:
            row.operator(operator="scene.auto_clipping", text="", icon='OUTLINER_DATA_CAMERA', emboss=True, depress=False)
            AC_active = True
        

        #bpy.ops.script.reload()

def max_list_value(list):
    i = numpy.argmax(list)
    v = list[i]
    return (i, v)

def min_list_value(list):
    i = numpy.argmin(list)
    v = list[i]
    return (i, v)

class AutoClipping_OT_run(bpy.types.Operator):
    bl_idname = "scene.auto_clipping"
    bl_label = "auto_clipping"
    bl_description = "auto_clipping"
    
    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def execute(self, context):
        scale_factor = 100
        obj = bpy.context.active_object
        # calculate selected context
        #size = sum(obj.dimensions)        
        i, max = max_list_value(obj.dimensions)
        i, min = min_list_value(obj.dimensions)
        print(obj.name , ": ", max, min)
        # adjust clipping selected context
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.clip_start = min / scale_factor
                        space.clip_end = max * scale_factor
                        print("start: ", space.clip_start, "\nend: ", space.clip_end)
                        if space.camera:
                            print("camera: ", space.camera.name)
                            bpy.data.cameras[space.camera.name].clip_start = min / scale_factor
                            bpy.data.cameras[space.camera.name].clip_end = max * scale_factor
        
        return{'FINISHED'}

def register():
    bpy.utils.register_class(AutoClipping_OT_run)
    bpy.types.TOPBAR_HT_upper_bar.prepend(draw_button)


def unregister():
    bpy.types.TOPBAR_HT_upper_bar.remove(draw_button)
    bpy.utils.unregister_class(AutoClipping_OT_run)


if __name__ == "__main__":
    register()
