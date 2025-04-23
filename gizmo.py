

from bpy.types import GizmoGroup

class FakeGizmoGroup(GizmoGroup):
    bl_idname = "MESH_GGT_select_side_of_plane"
    bl_label = "Side of Plane Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'EXCLUDE_MODAL'}

    # Helper functions
    @staticmethod
    def my_target_operator(context):
        wm = context.window_manager
        op = wm.operators[-1] if wm.operators else None
        if isinstance(op, SelectSideOfPlane):
            return op
        return None

    @staticmethod
    def my_view_orientation(context):
        rv3d = context.space_data.region_3d
        view_inv = rv3d.view_matrix.to_3x3()
        return view_inv.normalized()

    @classmethod
    def poll(cls, context):
        op = cls.my_target_operator(context)
        if op is None:
            wm = context.window_manager
            wm.gizmo_group_type_unlink_delayed(SelectSideOfPlaneGizmoGroup.bl_idname)
            return False
        return True

    def setup(self, context):
        from mathutils import Matrix, Vector

        # ----
        # Move

        def move_get_cb():
            op = SelectSideOfPlaneGizmoGroup.my_target_operator(context)
            return op.plane_co

        def move_set_cb(value):
            op = SelectSideOfPlaneGizmoGroup.my_target_operator(context)
            op.plane_co = value
            # XXX, this may change!
            op.execute(context)

        gz = self.gizmos.new("GIZMO_GT_move_3d")
        gz.target_set_handler("offset", get=move_get_cb, set=move_set_cb)

        gz.use_draw_value = True

        gz.color = 0.8, 0.8, 0.8
        gz.alpha = 0.5

        gz.color_highlight = 1.0, 1.0, 1.0
        gz.alpha_highlight = 1.0

        gz.scale_basis = 0.2

        self.gizmo_move = gz

        # ----
        # Dial

        def direction_get_cb():
            op = SelectSideOfPlaneGizmoGroup.my_target_operator(context)

            no_a = self.gizmo_dial.matrix_basis.col[1].xyz
            no_b = Vector(op.plane_no)

            no_a = (no_a @ self.view_inv).xy.normalized()
            no_b = (no_b @ self.view_inv).xy.normalized()
            return no_a.angle_signed(no_b)

        def direction_set_cb(value):
            op = SelectSideOfPlaneGizmoGroup.my_target_operator(context)
            matrix_rotate = Matrix.Rotation(-value, 3, self.rotate_axis)
            no = matrix_rotate @ self.gizmo_dial.matrix_basis.col[1].xyz
            op.plane_no = no
            op.execute(context)

        gz = self.gizmos.new("GIZMO_GT_dial_3d")
        gz.target_set_handler("offset", get=direction_get_cb, set=direction_set_cb)
        gz.draw_options = {'ANGLE_START_Y'}

        gz.use_draw_value = True

        gz.color = 0.8, 0.8, 0.8
        gz.alpha = 0.5

        gz.color_highlight = 1.0, 1.0, 1.0
        gz.alpha_highlight = 1.0

        self.gizmo_dial = gz

    def draw_prepare(self, context):
        from mathutils import Vector

        view_inv = self.my_view_orientation(context)

        self.view_inv = view_inv
        self.rotate_axis = view_inv[2].xyz
        self.rotate_up = view_inv[1].xyz

        op = self.my_target_operator(context)

        co = Vector(op.plane_co)
        no = Vector(op.plane_no).normalized()

        # Move
        no_z = no
        no_y = no_z.orthogonal()
        no_x = no_z.cross(no_y)

        matrix = self.gizmo_move.matrix_basis
        matrix.identity()
        matrix.col[0].xyz = no_x
        matrix.col[1].xyz = no_y
        matrix.col[2].xyz = no_z
        # The location callback handles the location.
        # `matrix.col[3].xyz = co`.

        # Dial
        no_z = self.rotate_axis
        no_y = (no - (no.project(no_z))).normalized()
        no_x = self.rotate_axis.cross(no_y)

        matrix = self.gizmo_dial.matrix_basis
        matrix.identity()
        matrix.col[0].xyz = no_x
        matrix.col[1].xyz = no_y
        matrix.col[2].xyz = no_z
        matrix.col[3].xyz = co