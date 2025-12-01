bl_info = {
    "name": "Generate Muscle System",
    "author": "Himadri Roy Sarkar (improved version)",
    "version": (1, 2, 0),
    "blender": (4, 0, 0),
    "location": "Properties > Physics > Muscle System",
    "description": "Quickly generate deformable muscle objects driven by armature bones with soft-body simulation and dynamic stiffness control",
    "category": "Physics",
    "doc_url": "",
    "tracker_url": "",
}

import bpy
from bpy.types import Operator, Panel
from bpy.props import FloatProperty
from mathutils import Vector


# ──────────────────────────────────────────────────────────────
# Global update: Muscle Tension → Soft Body Goal
# ──────────────────────────────────────────────────────────────
def update_muscle_tension(self, context):
    obj = self  # 'self' is the object that owns the property
    mod = obj.modifiers.get("MuscleSim")
    if mod and mod.type == 'SOFT_BODY':
        # 0.0 tension = very stiff, 1.0 = very soft/jiggly
        mod.settings.goal_default = 1.0 - (obj.muscle_tension * 0.85)


# ──────────────────────────────────────────────────────────────
# OPERATORS
# ──────────────────────────────────────────────────────────────
class MUSCLE_OT_generate_muscle(Operator):
    bl_idname = "muscle.generate_muscle"
    bl_label = "Generate Muscle Between Bones"
    bl_description = "Creates a volumetric muscle mesh between two selected pose bones with soft-body simulation"
    bl_options = {'REGISTER', 'UNDO'}

    radius: FloatProperty(name="Base Radius", default=0.25, min=0.01, max=2.0)
    segments: bpy.props.IntProperty(name="Radial Segments", default=20, min=8, max=64)
    taper: FloatProperty(name="End Taper (%)", default=0.7, min=0.0, max=1.0, subtype='FACTOR')

    def execute(self, context):
        arm = context.active_object
        if arm.type != 'ARMATURE':
            self.report({'ERROR'}, "Active object must be an armature")
            return {'CANCELLED'}

        selected_bones = [b for b in arm.pose.bones if b.bone.select]
        if len(selected_bones) != 2:
            self.report({'ERROR'}, "Exactly two pose bones must be selected")
            return {'CANCELLED'}

        bone1, bone2 = selected_bones

        # World positions
        mat = arm.matrix_world
        head1 = mat @ bone1.head
        head2 = mat @ bone2.head
        direction = head2 - head1
        length = direction.length
        if length < 0.001:
            self.report({'ERROR'}, "Bones are too close")
            return {'CANCELLED'}

        mid = head1 + direction * 0.5

        # Create muscle cylinder
        bpy.ops.mesh.primitive_cylinder_add(
            radius=self.radius,
            depth=length,
            vertices=self.segments,
            location=mid,
            align='WORLD'
        )
        muscle = context.active_object
        muscle.name = f"Muscle_{bone1.name}_to_{bone2.name}"

        # Orient along bone direction
        muscle.rotation_quaternion = direction.to_track_quat('Z', 'Y')
        muscle.parent = arm

        # Taper ends
        if self.taper < 1.0:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')

            # Select top and bottom caps
            top_vs = [v for v in muscle.data.vertices if v.co.z > (length/2 - 0.01)]
            bottom_vs = [v for v in muscle.data.vertices if v.co.z < -(length/2 - 0.01)]
            for v in top_vs + bottom_vs:
                v.co.xy *= self.taper

            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.normals_make_consistent()
            bpy.ops.object.mode_set(mode='OBJECT')

        # Hooks
        def create_hook(vertices, bone):
            hook = muscle.modifiers.new(name=f"Hook_{bone.name}", type='HOOK')
            hook.object = arm
            hook.subtarget = bone.name
            indices = [v.index for v in vertices]
            hook.vertex_indices_set(indices)

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')

        # Bottom cap
        bottom_verts = [v for v in muscle.data.vertices if v.co.z < -length * 0.49]
        create_hook(bottom_verts, bone1)

        # Top cap
        top_verts = [v for v in muscle.data.vertices if v.co.z > length * 0.49]
        create_hook(top_verts, bone2)

        # Vertex group for goal strength (stiff at ends, soft in middle)
        vg = muscle.vertex_groups.new(name="Muscle_Pin")
        vg.add([v.index for v in muscle.data.vertices if abs(v.co.z) > length * 0.45], 1.0, 'REPLACE')
        vg.add([v.index for v in muscle.data.vertices if abs(v.co.z) < length * 0.30], 0.2, 'REPLACE')

        # Soft Body
        sb_mod = muscle.modifiers.new(name="MuscleSim", type='SOFT_BODY')
        sb = sb_mod.settings
        sb.mass = 2.0
        sb.use_goal = True
        sb.vertex_group_goal = "Muscle_Pin"
        sb.goal_default = 0.75
        sb.goal_min = 0.0
        sb.goal_max = 1.0
        sb.pull = 0.98
        sb.push = 0.98
        sb.bend = 0.9
        sb.damping = 3.0
        sb.use_self_collision = True
        sb.use_edges = True
        sb.collision_type = 'AVERAGE'

        # Custom property
        muscle.muscle_tension = 0.3  # default medium tension

        # Optional: add to new collection
        coll = bpy.data.collections.get("Muscles")
        if not coll:
            coll = bpy.data.collections.new("Muscles")
            context.scene.collection.children.link(coll)
        coll.objects.link(muscle)
        context.scene.collection.objects.unlink(muscle)

        self.report({'INFO'}, f"Muscle '{muscle.name}' created")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


# Motion Painter & Compression operators kept but slightly cleaned
class MUSCLE_OT_setup_motion_painter(Operator):
    bl_idname = "muscle.setup_motion_painter"
    bl_label = "Setup Motion Painter"
    bl_description = "Creates proximity brushes on selected bones to paint soft areas during movement"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        muscle = context.active_object
        if muscle.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a muscle mesh")
            return {'CANCELLED'}

        arm = muscle.find_armature()
        if not arm:
            self.report({'ERROR'}, "Muscle has no armature")
            return {'CANCELLED'}

        # Canvas
        dp = muscle.modifiers.get("DynamicPaint") or muscle.modifiers.new("DynamicPaint", 'DYNAMIC_PAINT')
        dp.ui_type = 'CANVAS'
        if not dp.canvas_settings.canvas_surfaces:
            bpy.ops.dpaint.surface_slot_add({'object': muscle})
        surf = dp.canvas_settings.canvas_surfaces[0]
        surf.surface_type = 'WEIGHT'
        surf.name = "MotionSoftness"

        # Brushes on selected bones (or all if none selected)
        bones = [b for b in arm.pose.bones if b.bone.select] or arm.pose.bones
        for bone in bones:
            name = f"DP_Brush_{bone.name}"
            if name in bpy.data.objects:
                continue
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
            brush = context.active_object
            brush.name = name
            brush.parent = arm
            brush.parent_type = 'BONE'
            brush.parent_bone = bone.name
            brush.empty_display_size = 0.05
            brush.show_in_front = True

            dp_mod = brush.modifiers.new(type='DYNAMIC_PAINT', name="DP_Brush")
            dp_mod.ui_type = 'BRUSH'
            bs = dp_mod.brush_settings
            bs.paint_source = 'PROXIMITY'
            bs.proximity_falloff = 'SMOOTH'
            bs.strength = 0.2
            bs.distance = 0.35
            bs.invert_proximity = True

        self.report({'INFO'}, "Motion Painter brushes created")
        return {'FINISHED'}


class MUSCLE_OT_setup_compression(Operator):
    bl_idname = "muscle.setup_compression"
    bl_label = "Setup Compression Stiffener"
    bl_description = "Stiffens muscle where clothing/other objects press against it"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        muscle = context.active_object
        if muscle.type != 'MESH':
            self.report({'ERROR'}, "Select muscle mesh")
            return {'CANCELLED'}

        vg = muscle.vertex_groups.get("Muscle_Pin") or muscle.vertex_groups.new(name="Muscle_Pin")

        dp = muscle.modifiers.get("DynamicPaint") or muscle.modifiers.new("DynamicPaint", 'DYNAMIC_PAINT')
        dp.ui_type = 'CANVAS'
        surf = None
        for s in dp.canvas_settings.canvas_surfaces:
            if s.name == "Compression":
                surf = s
                break
        if not surf:
            bpy.ops.dpaint.surface_slot_add({'object': muscle})
            surf = dp.canvas_settings.canvas_surfaces[-1]
            surf.name = "Compression"
        surf.surface_type = 'WEIGHT'
        surf.use_invert_output = True  # contact = high weight = stiff

        # Turn selected meshes into brushes
        for obj in context.selected_objects:
            if obj == muscle or obj.type != 'MESH':
                continue
            mod = obj.modifiers.new(type='DYNAMIC_PAINT', name="CompressionBrush")
            mod.ui_type = 'BRUSH'
            bs = mod.brush_settings
            bs.paint_source = 'PROXIMITY'
            bs.strength = 1.0
            bs.distance = 0.06

        self.report({'INFO'}, "Compression stiffener ready")
        return {'FINISHED'}


# ──────────────────────────────────────────────────────────────
# PANEL
# ──────────────────────────────────────────────────────────────
class MUSCLE_PT_panel(Panel):
    bl_label = "Muscle System"
    bl_idname = "MUSCLE_PT_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "physics"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        obj = context.object

        col = layout.column(align=True)
        col.operator("muscle.generate_muscle", icon='OUTLINER_OB_MESH')

        if obj and obj.type == 'MESH' and obj.modifiers.get("MuscleSim"):
            box = layout.box()
            box.label(text="Muscle Controls", icon='ARMATURE_DATA')
            box.prop(obj, "muscle_tension", text="Tension (0=stiff, 1=soft)", slider=True)

            col = layout.column(align=True)
            col.operator("muscle.setup_motion_painter", icon='BONE_DATA')
            col.operator("muscle.setup_compression", icon='MOD_CLOTH')

            row = layout.row(align=True)
            row.operator("ptcache.bake_all", text="Bake All Physics", icon='PHYSICS')
            row.operator("ptcache.free_bake_all", text="Free", icon='CANCELLED')


# ──────────────────────────────────────────────────────────────
# REGISTER
# ──────────────────────────────────────────────────────────────
classes = (
    MUSCLE_OT_generate_muscle,
    MUSCLE_OT_setup_motion_painter,
    MUSCLE_OT_setup_compression,
    MUSCLE_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.muscle_tension = FloatProperty(
        name="Muscle Tension",
        description="0 = stiff muscle, 1 = very soft/jiggly",
        default=0.3, min=0.0, max=1.0,
        update=update_muscle_tension
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Object.muscle_tension

if __name__ == "__main__":
    register()
