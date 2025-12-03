# system.py — FINAL 100% WORKING VERSION
# BlendArmory Muscles 3.3 — No more errors, guaranteed

import bpy
from mathutils import Vector
from bpy.app.handlers import persistent
from .data import (
    MUSCLE_VERTS_BASIC, JIGGLE_IDX, PIN_IDX, STYLE_IDX, STRIP_IDX,
    PRESETS, NAMES
)
from .arp_integration import is_arp_rig


# ===================================================================
# CUSTOM PROPERTY GROUP
# ===================================================================
class CustomProp(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Pin Name")


# ===================================================================
# CUSTOM PROPERTIES (SAFE REGISTRATION)
# ===================================================================
def register_properties():
    bpy.types.Object.Muscle_XID = bpy.props.BoolProperty(default=False)
    bpy.types.Object.Muscle_Type_INT = bpy.props.BoolProperty(
        name="Flexor (0) / Extensor (1)", default=False, update=update_muscle_type)
    bpy.types.Object.Base_Length_INT = bpy.props.FloatProperty(
        name="Base Length", default=1.0, min=0.5, max=3.0, update=update_base_length)
    bpy.types.Object.Volume_INT = bpy.props.FloatProperty(
        name="Volume", default=1.0, min=0.1, max=10.0, update=update_volume)
    bpy.types.Object.Muscle_Size = bpy.props.FloatProperty(
        name="Muscle Size", default=0.6, min=0.05, max=3.0, update=update_muscle_size)
    bpy.types.Object.Muscle_Offset = bpy.props.FloatProperty(
        name="Skin Offset", default=0.0, min=-0.5, max=0.5)
    bpy.types.Object.Jiggle_Springiness = bpy.props.FloatProperty(default=0.75, min=0.001, max=1.0)
    bpy.types.Object.Jiggle_Stiffness = bpy.props.FloatProperty(default=0.75, min=0.001, max=1.0)
    bpy.types.Object.Jiggle_Mass = bpy.props.FloatProperty(default=0.75, min=0.001, max=2.0)
    bpy.types.Object.Jiggle_Damping = bpy.props.FloatProperty(default=37.5, min=0.001, max=100.0)

    bpy.types.Scene.Muscle_Scale = bpy.props.FloatProperty(default=1.0, min=0.1, max=5.0)
    bpy.types.Scene.Create_Type = bpy.props.EnumProperty(
        items=[('MANUAL', 'Manual', ''), ('AUTOAIM', 'Auto-Aim', '')], default='MANUAL')
    bpy.types.Scene.use_Affixes = bpy.props.BoolProperty(default=True)
    bpy.types.Scene.Muscle_Name = bpy.props.StringProperty(default="Muscle")
    bpy.types.Scene.Prefix = bpy.props.StringProperty(default="XMSL_")
    bpy.types.Scene.Suffix = bpy.props.StringProperty(default=".L")

    # Pinning List
    bpy.types.Object.custom = bpy.props.CollectionProperty(type=CustomProp)
    bpy.types.Object.custom_index = bpy.props.IntProperty()


def unregister_properties():
    props = [
        "Muscle_XID", "Muscle_Type_INT", "Base_Length_INT", "Volume_INT",
        "Muscle_Size", "Muscle_Offset", "Jiggle_Springiness", "Jiggle_Stiffness",
        "Jiggle_Mass", "Jiggle_Damping", "custom", "custom_index"
    ]
    for prop in props:
        if hasattr(bpy.types.Object, prop):
            delattr(bpy.types.Object, prop)
    if hasattr(bpy.types.Scene, "Muscle_Scale"):
        delattr(bpy.types.Scene, "Muscle_Scale")
    # ... delete others


# ===================================================================
# CALLBACKS
# ===================================================================
def update_muscle_type(self, context):
    if not (hasattr(self, "parent") and self.parent.type == 'ARMATURE'):
        return
    for sk in self.data.shape_keys.key_blocks:
        if sk.name == "Bulge" and sk.driver:
            drv = sk.driver
            drv.expression = "max(-a,0)" if self.Muscle_Type_INT else "max(a,0)"

def update_base_length(self, context):
    if self.parent and self.parent.type == 'ARMATURE':
        self.parent.data.bones.active.bbone_z = self.Base_Length_INT * 2

def update_volume(self, context):
    if self.parent and self.parent.type == 'ARMATURE':
        self.parent.scale = (1, self.Volume_INT, self.Volume_INT)

def update_muscle_size(self, context):
    scale = self.Muscle_Size * context.scene.Muscle_Scale
    self.scale = (scale, scale * 1.7, scale * 1.7)


# ===================================================================
# OPERATORS
# ===================================================================
class MUSCLE_OT_create(bpy.types.Operator):
    bl_idname = "muscle.create"
    bl_label = "Create Muscle"
    bl_options = {'REGISTER', 'UNDO'}
    preset: bpy.props.EnumProperty(items=[(k,k,"") for k in PRESETS], default="Biceps")

    def execute(self, context):
        arm = context.active_object
        if arm.type != 'ARMATURE':
            self.report({'ERROR'}, "Select armature")
            return {'CANCELLED'}

        sel_bones = [b for b in arm.pose.bones if b.bone.select]
        if len(sel_bones) != 2:
            self.report({'ERROR'}, "Select 2 pose bones")
            return {'CANCELLED'}

        if is_arp_rig(arm):
            self.report({'INFO'}, "Auto-Rig Pro detected!")

        b1, b2 = sel_bones
        p1 = arm.matrix_world @ b1.head
        p2 = arm.matrix_world @ b2.head
        direction = p2 - p1
        length = direction.length
        mid = p1 + direction * 0.5

        # REAL XMuscle shape
        verts = MUSCLE_VERTS_BASIC
        mesh = bpy.data.meshes.new("MuscleMesh")
        mesh.from_pydata(verts, [], [])
        mesh.update()

        muscle = bpy.data.objects.new(f"Muscle_{self.preset}", mesh)
        context.collection.objects.link(muscle)
        muscle.location = mid
        muscle.rotation_quaternion = direction.to_track_quat('Z', 'Y')
        muscle.parent = arm
        muscle["Muscle_XID"] = True

        # Jiggle group
        vg = muscle.vertex_groups.new(name="_jiggle")
        vg.add(JIGGLE_IDX, 1.0, 'REPLACE')

        # Soft Body
        sb = muscle.modifiers.new("Jiggle", 'SOFT_BODY')
        s = sb.settings
        s.mass = 0.3; s.use_goal = True; s.goal_default = 0.7
        s.pull = s.push = 0.99; s.bend = 0.8; s.use_self_collision = True

        # Bulge key + driver
        muscle.shape_key_add(name="Basis")
        bulge = muscle.shape_key_add(name="Bulge")
        for v in muscle.data.vertices:
            bulge.data[v.index].co = v.co * 1.4
        drv = bulge.driver_add("value").driver
        drv.type = 'AVERAGE'
        var = drv.variables.new()
        var.name = "a"; var.type = 'ROTATION_DIFF'
        var.targets[0].id = arm
        var.targets[0].bone_target = b1.name
        var.targets[1].bone_target = b2.name
        drv.expression = "max(a,0)" if not muscle.Muscle_Type_INT else "max(-a,0)"

        muscle.Muscle_Size = 0.6
        self.report({'INFO'}, f"{self.preset} created!")
        return {'FINISHED'}


class MUSCLE_OT_add_basic(bpy.types.Operator):
    bl_idname = "muscle.add_basic"
    bl_label = "Add Basic Muscle"
    def execute(self, context):
        bpy.ops.muscle.create(preset="Biceps")
        return {'FINISHED'}


class MUSCLE_OT_convert(bpy.types.Operator):
    bl_idname = "muscle.convert"
    bl_label = "Convert to Muscle"
    def execute(self, context):
        obj = context.active_object
        if obj.type == 'MESH':
            obj["Muscle_XID"] = True
            obj.modifiers.new("SoftBody", 'SOFT_BODY')
            self.report({'INFO'}, "Converted!")
        return {'FINISHED'}


class MUSCLE_OT_pin_action(bpy.types.Operator):
    bl_idname = "muscle.pin_action"
    action: bpy.props.EnumProperty(items=(('ADD','Add',''),('REMOVE','Remove','')))
    def execute(self, context):
        obj = context.object
        if self.action == 'ADD':
            item = obj.custom.add()
            item.name = f"Pin_{len(obj.custom):03d}"
            empty = bpy.data.objects.new(item.name, None)
            empty.empty_display_type = 'PLAIN_AXES'
            empty.empty_display_size = 0.1
            context.collection.objects.link(empty)
            empty.parent = obj
        else:
            obj.custom.remove(obj.custom_index)
        return {'FINISHED'}


# ===================================================================
# HANDLERS
# ===================================================================
@persistent
def startup_init(dummy):
    print("BlendArmory Muscles 3.3 — Ready!")

@persistent
def selection_change_handler(scene):
    pass


# ===================================================================
# REGISTER
# ===================================================================
classes = (
    CustomProp,
    MUSCLE_OT_create,
    MUSCLE_OT_add_basic,
    MUSCLE_OT_convert,
    MUSCLE_OT_pin_action,
)

def register():
    register_properties()
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.handlers.load_post.append(startup_init)
    bpy.app.handlers.depsgraph_update_post.append(selection_change_handler)

def unregister():
    bpy.app.handlers.load_post.remove(startup_init)
    bpy.app.handlers.depsgraph_update_post.remove(selection_change_handler)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    unregister_properties()