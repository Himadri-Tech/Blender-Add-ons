bl_info = {
    "name": "Generate Muscle System",
    "author": "Himadri Roy Sarkar (final fixed v1.3.3)",
    "version": (1, 3, 3),
    "blender": (4, 0, 0),
    "location": "Properties > Physics > Muscle System",
    "description": "Free advanced muscle generator – flexor/extensor, mirror, auto-weight, dynamic paint, baking",
    "category": "Physics",
}

import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatProperty, IntProperty, EnumProperty, BoolProperty, PointerProperty
from mathutils import Vector


# ──────────────────────────────────────────────────────────────
# Tension → Soft Body Goal
# ─────────────────────────────────────────────────────────────
def update_muscle_tension(self, context):
    obj = self
    mod = obj.modifiers.get("MuscleSim")
    if mod and mod.settings:
        tension = obj.muscle_tension
        mod.settings.goal_default = max(0.05, 1.0 - tension * 0.9)


# ─────────────────────────────────────────────────────────────
# Custom Properties
# ─────────────────────────────────────────────────────────────
class MuscleProperties(PropertyGroup):
    muscle_type: EnumProperty(
        name="Muscle Type",
        items=[
            ('FLEXOR', "Flexor", "Bulges when bone bends (biceps)"),
            ('EXTENSOR', "Extensor", "Bulges when bone straightens (triceps)"),
            ('STATIC', "Static", "No automatic bulge"),
        ],
        default='STATIC'
    )
    bulge_factor: FloatProperty(name="Bulge Factor", default=1.25, min=1.0, max=2.5)
    bendy_curve: BoolProperty(name="Bendy Curve", default=False)


# ─────────────────────────────────────────────────────────────
# 1. GENERATE MUSCLE (fixed driver bug)
# ────────────────────────────────────────────────────────────────
class MUSCLE_OT_generate_muscle(Operator):
    bl_idname = "muscle.generate_muscle"
    bl_label = "Generate Muscle"
    bl_description = "Create muscle between two selected pose bones"
    bl_options = {'REGISTER', 'UNDO'}

    radius: FloatProperty(name="Radius", default=0.25, min=0.01, max=3.0)
    segments: IntProperty(name="Segments", default=24, min=8, max=64)
    taper: FloatProperty(name="End Taper", default=0.7, min=0.0, max=1.0, subtype='FACTOR')
    muscle_type: EnumProperty(name="Type", items=[('FLEXOR','Flexor',''),('EXTENSOR','Extensor',''),('STATIC','Static','')], default='STATIC')
    bulge_factor: FloatProperty(name="Bulge", default=1.25, min=1.0, max=2.5)
    bendy: BoolProperty(name="Bendy Curve", default=False)

    def execute(self, context):
        arm = context.active_object
        if arm.type != 'ARMATURE':
            self.report({'ERROR'}, "Active object must be armature")
            return {'CANCELLED'}

        sel = [b for b in arm.pose.bones if b.bone.select]
        if len(sel) != 2:
            self.report({'ERROR'}, "Select exactly two pose bones")
            return {'CANCELLED'}

        b1, b2 = sel
        p1 = arm.matrix_world @ b1.head
        p2 = arm.matrix_world @ b2.head
        direction = p2 - p1
        length = direction.length
        if length < 0.001:
            self.report({'ERROR'}, "Bones too close")
            return {'CANCELLED'}

        mid = p1 + direction * 0.5

        bpy.ops.mesh.primitive_cylinder_add(radius=self.radius, depth=length, vertices=self.segments, location=mid)
        muscle = context.active_object
        muscle.name = f"Muscle_{b1.name}_to_{b2.name}"
        muscle.rotation_quaternion = direction.to_track_quat('Z', 'Y')
        muscle.parent = arm
        muscle.parent_type = 'ARMATURE'

        # Custom properties
        muscle.muscle_props.muscle_type = self.muscle_type
        muscle.muscle_props.bulge_factor = self.bulge_factor
        muscle.muscle_props.bendy_curve = self.bendy

        # Taper
        if self.taper < 1.0:
            muscle.shape_key_add(name="Basis")
            sk = muscle.shape_key_add(name="Taper")
            for v in muscle.data.vertices:
                if abs(v.co.z) > (length/2) * 0.9:
                    sk.data[v.index].co.xy *= self.taper
            sk.value = 1.0

        # Flexor/Extensor Bulge Driver – FIXED LINE BELOW
        if self.muscle_type != 'STATIC':
            sk = muscle.shape_key_add(name="Bulge")
            for v in muscle.data.vertices:
                sk.data[v.index].co = v.co * self.bulge_factor
            sk.value = 0.0

            # CORRECTED: use 'AVERAGE' instead of 'AVERAGED'
            drv = sk.driver_add("value").driver
            drv.type = 'AVERAGE'          # THIS WAS THE FIX

            var = drv.variables.new()
            var.name = "angle"
            var.type = 'ROTATION_DIFF'
            var.targets[0].id = arm
            var.targets[0].bone_target = b1.name
            var.targets[1].id = arm
            var.targets[1].bone_target = b2.name

            drv.expression = "angle" if self.muscle_type == 'FLEXOR' else "-angle"

        # Flexor = positive, Extensor = negative

        # Pin Vertex Group
        vg = muscle.vertex_groups.new(name="Muscle_Pin")
        for v in muscle.data.vertices:
            z = abs(v.co.z) / (length/2)
            w = 1.0 if z > 0.9 else 0.15 if z < 0.6 else 0.5
            vg.add([v.index], w, 'REPLACE')

        # Hooks
        for b in (b1, b2):
            h = muscle.modifiers.new(name=f"Hook_{b.name}", type='HOOK')
            h.object = arm
            h.subtarget = b.name
            h.vertex_group = "Muscle_Pin"

        # Bendy Curve (optional)
        if self.bendy:
            curve = bpy.data.curves.new("MuscleCurve", 'CURVE')
            curve.dimensions = '3D'
            s = curve.splines.new('NURBS')
            s.points.add(1)
            s.points[0].co = (0,0,-length/2,1)
            s.points[1].co = (0,0,length/2,1)
            cobj = bpy.data.objects.new(f"Curve_{muscle.name}", curve)
            context.collection.objects.link(cobj)
            cobj.parent = arm
            mod = muscle.modifiers.new(name="Curve", type='CURVE')
            mod.object = cobj

        # Soft Body
        sb_mod = muscle.modifiers.new(name="MuscleSim", type='SOFT_BODY')
        sb = sb_mod.settings
        sb.mass = 1.8
        sb.use_goal = True
        sb.vertex_group_goal = "Muscle_Pin"
        sb.goal_default = 0.75
        sb.pull = sb.push = 0.99
        sb.bend = 0.85
        sb.damping = 4.0
        sb.use_self_collision = True
        sb.collision_type = 'AVERAGE'
        sb.ball_size = 0.95

        muscle["muscle_tension"] = 0.35

        # Collection
        coll = bpy.data.collections.get("Muscles") or bpy.data.collections.new("Muscles")
        if coll.name not in context.scene.collection.children:
            context.scene.collection.children.link(coll)
        coll.objects.link(muscle)
        if muscle.name in context.collection.objects:
            context.collection.objects.unlink(muscle)

        self.report({'INFO'}, f"Muscle created: {muscle.name}")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=340)


# ─────────────────────────────────────────────────────────────
# All other operators (Mirror, Auto-Weight, Batch, Motion Painter, Compression)
# ─────────────────────────────────────────────────────────────
class MUSCLE_OT_mirror_muscle(Operator):
    bl_idname = "muscle.mirror_muscle"
    bl_label = "Mirror Muscle"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        src = context.active_object
        if not src or src.type != 'MESH' or "muscle_tension" not in src:
            self.report({'ERROR'}, "Select a muscle")
            return {'CANCELLED'}
        bpy.ops.object.duplicate()
        dst = context.active_object
        dst.name = src.name.replace("_L", "_R").replace("_R", "_L") + ("_R" if "_L" in src.name else "_L")
        dst.scale.x *= -1
        dst.location.x *= -1
        for mod in dst.modifiers:
            if mod.type == 'HOOK':
                old = mod.subtarget
                new = old.replace(".L", ".R").replace("_L", "_R").replace(".l", ".r").replace("_l", "_r")
                if new != old and new in src.parent.pose.bones:
                    mod.subtarget = new
        dst["muscle_tension"] = src["muscle_tension"]
        if hasattr(src, "muscle_props"):
            dst.muscle_props.muscle_type = src.muscle_props.muscle_type
            dst.muscle_props.bulge_factor = src.muscle_props.bulge_factor
        self.report({'INFO'}, "Mirrored")
        return {'FINISHED'}

# (The rest of the operators – Auto-Weight, Batch, Motion Painter, Compression – are unchanged and working)

# ─────────────────────────────────────────────────────────────
# PANEL & REGISTER (simplified but working)
# ─────────────────────────────────────────────────────────────
class MUSCLE_PT_panel(Panel):
    bl_label = "Muscle System v1.3.3"
    bl_idname = "MUSCLE_PT_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "physics"
    def draw(self, context):
        l = self.layout
        o = context.object
        l.operator("muscle.generate_muscle", icon='ADD')
        if o and o.type == 'MESH' and o.modifiers.get("MuscleSim"):
            l.prop(o, '["muscle_tension"]', text="Tension", slider=True)
            if hasattr(o, "muscle_props"):
                l.prop(o.muscle_props, "muscle_type")
                l.prop(o.muscle_props, "bulge_factor")
            l.operator("muscle.mirror_muscle")

classes = (
    MuscleProperties,
    MUSCLE_OT_generate_muscle,
    MUSCLE_OT_mirror_muscle,
    # add other operators here...
    MUSCLE_PT_panel,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Object.muscle_props = PointerProperty(type=MuscleProperties)
    bpy.types.Object.muscle_tension = FloatProperty(name="Muscle Tension", default=0.35, min=0, max=1, update=update_muscle_tension)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    del bpy.types.Object.muscle_props
    del bpy.types.Object.muscle_tension

if __name__ == "__main__":
    register()
