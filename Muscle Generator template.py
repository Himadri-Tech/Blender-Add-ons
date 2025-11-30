bl_info = {
    "name": "Generate Muscle System",
    "author": "Himadri Roy Sarkar",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "Properties > Physics",
    "description": "Provides a convenient way to create realistic muscle systems within Blender. It simplifies the process of generating complex muscle structures for characters, streamlining the workflow for character rigging and animation.",
    "category": "Physics",
}

import bpy
from bpy.types import Operator, Panel
from bpy.props import FloatProperty

# ──────────────────────────────────────────────────────────────
# Slider Update for Global Muscle Tension
# ──────────────────────────────────────────────────────────────
def update_muscle_tension(self, context):
    mod = self.modifiers.get("MuscleSim")
    if mod and mod.type == 'SOFT_BODY':
        mod.settings.goal_default = 1.0 - (self.muscle_tension * 0.8)

# ──────────────────────────────────────────────────────────────
# OPERATORS
# ──────────────────────────────────────────────────────────────
class MUSCLE_OT_generate_muscle(Operator):
    bl_idname = "muscle.generate_muscle"
    bl_label = "Generate Muscle Between Bones"
    bl_description = "Creates a volumetric muscle mesh between two selected bones and sets up simulation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arm = context.active_object
        if arm.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an armature as active object")
            return {'CANCELLED'}

        selected_bones = [b for b in arm.pose.bones if b.bone.select]
        if len(selected_bones) != 2:
            self.report({'ERROR'}, "Select exactly two bones (origin and insertion)")
            return {'CANCELLED'}

        bone1, bone2 = selected_bones

        # Switch to object mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # Create cylinder muscle
        bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=2, vertices=16)
        muscle = context.active_object
        muscle.name = f"Muscle_{bone1.name}_{bone2.name}"

        # Position and orient
        mat = arm.matrix_world
        pos1 = mat @ bone1.head
        pos2 = mat @ bone2.head
        mid = (pos1 + pos2) / 2
        muscle.location = mid
        direction = pos2 - pos1
        muscle.scale.z = direction.length / 2
        muscle.rotation_quaternion = direction.to_track_quat('Z', 'Y')

        # Add hooks for attachment
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')

        # Hook1 for bone1 (bottom end)
        for v in muscle.data.vertices:
            if v.co.z < -0.9:
                v.select = True
        bpy.ops.object.mode_set(mode='OBJECT')
        hook1 = muscle.modifiers.new(name="Hook_Bone1", type='HOOK')
        hook1.object = arm
        hook1.subtarget = bone1.name
        hook1.vertex_indices_set([v.index for v in muscle.data.vertices if v.select])

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')

        # Hook2 for bone2 (top end)
        for v in muscle.data.vertices:
            if v.co.z > 0.9:
                v.select = True
        bpy.ops.object.mode_set(mode='OBJECT')
        hook2 = muscle.modifiers.new(name="Hook_Bone2", type='HOOK')
        hook2.object = arm
        hook2.subtarget = bone2.name
        hook2.vertex_indices_set([v.index for v in muscle.data.vertices if v.select])

        # Add Soft Body for simulation (muscle-optimized)
        mod = muscle.modifiers.new("MuscleSim", 'SOFT_BODY')
        sb = mod.settings
        sb.mass = 1.5  # Heavier for muscle inertia
        sb.use_goal = True
        vg = muscle.vertex_groups.new(name="Muscle_Pin")
        # Pin ends stiff, middle soft
        vg.add([v.index for v in muscle.data.vertices if abs(v.co.z) > 0.9], 1.0, 'REPLACE')
        vg.add([v.index for v in muscle.data.vertices if abs(v.co.z) < 0.5], 0.3, 'REPLACE')
        sb.vertex_group_goal = "Muscle_Pin"
        sb.goal_min = 0.0
        sb.pull = 0.95  # Strong volume preservation
        sb.push = 0.95
        sb.bend = 0.8
        sb.damping = 2.0  # Quick settle
        sb.use_edges = True
        sb.use_self_collision = True

        muscle.muscle_tension = 0.25  # Default tension

        self.report({'INFO'}, "Muscle generated and simulated!")
        return {'FINISHED'}

class MUSCLE_OT_setup_motion_painter(Operator):
    bl_idname = "muscle.setup_motion_painter"
    bl_label = "Setup Muscle Motion Painter"
    bl_description = "Auto-paints soft areas on muscles based on bone motion using Dynamic Paint"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        muscle = context.active_object
        if not muscle or muscle.type != 'MESH':
            self.report({'ERROR'}, "Select a muscle mesh")
            return {'CANCELLED'}

        arm = muscle.parent if muscle.parent and muscle.parent.type == 'ARMATURE' else None
        if not arm:
            for obj in context.selected_objects:
                if obj.type == 'ARMATURE':
                    arm = obj
                    break
        if not arm:
            self.report({'ERROR'}, "No armature found")
            return {'CANCELLED'}

        # Canvas on muscle
        if not any(m.type == 'DYNAMIC_PAINT' for m in muscle.modifiers):
            bpy.ops.object.modifier_add(type='DYNAMIC_PAINT')
        dp_mod = next(m for m in muscle.modifiers if m.type == 'DYNAMIC_PAINT')
        dp_mod.ui_type = 'CANVAS'
        if not dp_mod.canvas_settings.canvas_surfaces:
            bpy.ops.dpaint.surface_slot_add({'object': muscle})
        surface = dp_mod.canvas_settings.canvas_surfaces[0]
        surface.surface_type = 'WEIGHT'
        surface.brush_group = muscle.vertex_groups.get("Muscle_Pin")

        # Brushes on bones
        selected_bones = [b for b in arm.pose.bones if b.bone.select] or arm.pose.bones
        for bone in selected_bones:
            empty_name = f"DP_Brush_{bone.name}"
            if empty_name in bpy.data.objects:
                continue
            bpy.ops.object.empty_add(type='PLAIN_AXES')
            brush = context.active_object
            brush.name = empty_name
            brush.parent = arm
            brush.parent_type = 'BONE'
            brush.parent_bone = bone.name
            brush.empty_display_size = 0.05
            brush.hide_viewport = True

            bpy.ops.object.modifier_add(type='DYNAMIC_PAINT')
            brush.modifiers[-1].ui_type = 'BRUSH'
            bset = brush.modifiers[-1].brush_settings
            bset.paint_source = 'PROXIMITY'
            bset.strength = 0.15
            bset.distance = 0.3
            bset.invert_proximity = True

        self.report({'INFO'}, "Motion painter setup complete!")
        return {'FINISHED'}

class MUSCLE_OT_setup_compression(Operator):
    bl_idname = "muscle.setup_compression"
    bl_label = "Setup Muscle Compression"
    bl_description = "Auto-stiffens muscles under clothing using Dynamic Paint"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        muscle = context.active_object
        if not muscle or muscle.type != 'MESH':
            self.report({'ERROR'}, "Select a muscle mesh")
            return {'CANCELLED'}

        vg = muscle.vertex_groups.get("Muscle_Pin") or muscle.vertex_groups.new(name="Muscle_Pin")

        dp_mod = next((m for m in muscle.modifiers if m.type == 'DYNAMIC_PAINT'), None)
        if not dp_mod:
            bpy.ops.object.modifier_add(type='DYNAMIC_PAINT')
            dp_mod = muscle.modifiers[-1]
        dp_mod.ui_type = 'CANVAS'

        surf = None
        for s in dp_mod.canvas_settings.canvas_surfaces:
            if s.name == "Compression":
                surf = s
                break
        if not surf:
            bpy.ops.dpaint.surface_slot_add({'object': muscle})
            surf = dp_mod.canvas_settings.canvas_surfaces[-1]
            surf.name = "Compression"
        surf.surface_type = 'WEIGHT'
        surf.brush_group = vg
        surf.paint_color = 'INVERT'  # Contact stiffens

        # Turn selected objects into brushes
        for obj in context.selected_objects:
            if obj == muscle or obj.type != 'MESH':
                continue
            bpy.ops.object.modifier_add({'object': obj}, type='DYNAMIC_PAINT')
            mod = obj.modifiers[-1]
            mod.ui_type = 'BRUSH'
            bset = mod.brush_settings
            bset.paint_source = 'PROXIMITY'
            bset.strength = 1.0
            bset.distance = 0.06

        self.report({'INFO'}, "Compression setup complete!")
        return {'FINISHED'}

# ──────────────────────────────────────────────────────────────
# PANEL
# ──────────────────────────────────────────────────────────────
class MUSCLE_PT_panel(Panel):
    bl_label = "Generate Muscle System"
    bl_idname = "MUSCLE_PT_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "physics"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if not obj:
            layout.label(text="Select an object")
            return

        row = layout.row()
        row.operator("muscle.generate_muscle", text="Generate Muscle", icon='OUTLINER_OB_MESH')

        if obj.modifiers.get("MuscleSim"):
            box = layout.box()
            box.label(text="Muscle Tension", icon='PREFERENCES')
            box.prop(obj, "muscle_tension", text="Tension", slider=True)

            layout.operator("object.mode_set", text="Paint Muscle Areas", icon='BRUSH_DATA').mode = 'WEIGHT_PAINT'
            layout.label(text="Blue = Flexible | Red = Stiff", icon='INFO')

            layout.separator()
            box2 = layout.box()
            box2.label(text="Dynamic Simulation", icon='MOD_DYNAMICPAINT')
            box2.operator("muscle.setup_motion_painter", text="Motion Painter", icon='BONE_DATA')
            box2.operator("muscle.setup_compression", text="Compression Stiffener", icon='MOD_CLOTH')

            layout.separator()
            row = layout.row(align=True)
            row.operator("ptcache.bake_all", text="Bake", icon='PHYSICS')
            row.operator("ptcache.free_bake_all", text="Free Bake", icon='TRASH')

# ──────────────────────────────────────────────────────────────
# REGISTER
# ──────────────────────────────────────────────────────────────
def register():
    bpy.utils.register_class(MUSCLE_OT_generate_muscle)
    bpy.utils.register_class(MUSCLE_OT_setup_motion_painter)
    bpy.utils.register_class(MUSCLE_OT_setup_compression)
    bpy.utils.register_class(MUSCLE_PT_panel)

    bpy.types.Object.muscle_tension = FloatProperty(
        name="Muscle Tension",
        default=0.0, min=0.0, max=1.0,
        update=update_muscle_tension
    )

def unregister():
    bpy.utils.unregister_class(MUSCLE_PT_panel)
    bpy.utils.unregister_class(MUSCLE_OT_setup_compression)
    bpy.utils.unregister_class(MUSCLE_OT_setup_motion_painter)
    bpy.utils.unregister_class(MUSCLE_OT_generate_muscle)
    del bpy.types.Object.muscle_tension

if __name__ == "__main__":
    register()
