# ═══════════════════════════════════════════════════════════════════
#   BLENDARMORY MUSCLES 2.1 – With Bendy Bones for Soft Middle Deformation
#   Now uses bendy bones with head/tail controllers and Stretch To constraints
#   Removed soft body – now pure rig-based for speed and control
# ═══════════════════════════════════════════════════════════════════

bl_info = {
    "name": "BlendArmory Muscles 2.1",
    "author": "Grok + Himadri",
    "version": (2, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Muscles",
    "description": "Professional muscle system: bendy bones for soft middle, tendons, presets, auto-skin",
    "category": "Rigging",
}

import bpy
from mathutils import Vector
from math import sin, cos, pi


# ─────────────────────── CORE SHAPE (unchanged) ───────────────────────
def create_fusiform(name, length, radius, power=1.9, radial=40, longi=26):
    bm = bmesh.new()
    for i in range(longi + 1):
        t = i / longi
        z = length * (t - 0.5)
        r = radius * pow(1.0 - abs(2*t - 1), power)
        for j in range(radial):
            a = j / radial * pi * 2
            bm.verts.new((r*cos(a), r*sin(a), z))
    bm.verts.ensure_lookup_table()
    for i in range(longi):
        for j in range(radial):
            a = i*radial + j
            b = i*radial + (j+1)%radial
            c = (i+1)*radial + (j+1)%radial
            d = (i+1)*radial + j
            bm.faces.new((bm.verts[a], bm.verts[b], bm.verts[c], bm.verts[d]))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh

# ─────────────────────── PRESETS (unchanged) ───────────────────────
PRESETS = {
    "Biceps":     {"bulge": 0.42, "length": 1.05, "tendon": 18, "type": "FLEXOR"},
    "Triceps":    {"bulge": 0.35, "length": 1.10, "tendon": 15, "type": "EXTENSOR"},
    "Deltoid":    {"bulge": 0.45, "length": 0.95, "tendon": 12, "type": "FLEXOR"},
    "Pectoral":   {"bulge": 0.50, "length": 1.00, "tendon": 8,  "type": "FLEXOR"},
    "Quadriceps": {"bulge": 0.55, "length": 1.15, "tendon": 20, "type": "FLEXOR"},
    "Dual Biceps":{"bulge": 0.40, "length": 1.05, "tendon": 18, "type": "DUAL"},
}

# ─────────────────────── CREATE MUSCLE ───────────────────────
class MUSCLE_OT_create(bpy.types.Operator):
    bl_idname = "muscle.create"
    bl_label = "Create Muscle"
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.EnumProperty(name="Preset", items=[(k,k,"") for k in PRESETS], default="Biceps")
    custom_bulge: bpy.props.FloatProperty(name="Bulge", default=0.4, min=0.1, max=1.2)
    custom_length: bpy.props.FloatProperty(name="Length", default=1.0, min=0.7, max=1.5)
    custom_tendon: bpy.props.FloatProperty(name="Tendon %", default=15, min=0, max=40)
    bbone_segments: bpy.props.IntProperty(name="Bendy Segments", default=16, min=4, max=32)

    def execute(self, context):
        arm = context.active_object
        if arm.type != 'ARMATURE':
            self.report({'ERROR'}, "Select armature")
            return {'CANCELLED'}
        bones = [b for b in arm.pose.bones if b.bone.select]
        if len(bones) != 2:
            self.report({'ERROR'}, "Select 2 bones")
            return {'CANCELLED'}

        p = PRESETS[self.preset]
        bulge = self.custom_bulge if self.preset == "Custom" else p["bulge"]
        length_mult = self.custom_length if self.preset == "Custom" else p["length"]
        tendon_pct = self.custom_tendon if self.preset == "Custom" else p["tendon"]
        mtype = p["type"]

        b1, b2 = bones
        p1 = arm.matrix_world @ b1.head
        p2 = arm.matrix_world @ b2.head
        direction = p2 - p1
        length = direction.length * length_mult
        mid = p1 + direction * 0.5

        # Create mesh
        mesh = create_fusiform("Muscle", length, bulge)
        muscle = bpy.data.objects.new(f"MUSCLE_{b1.name}_{b2.name}", mesh)
        context.collection.objects.link(muscle)
        muscle.location = mid
        muscle.rotation_quaternion = direction.to_track_quat('Z','Y')
        muscle.parent = arm

        # Create bendy bone armature for soft deformation
        muscle_arm_data = bpy.data.armatures.new(f"Arm_{muscle.name}")
        muscle_arm = bpy.data.objects.new(f"Arm_{muscle.name}", muscle_arm_data)
        context.collection.objects.link(muscle_arm)
        muscle_arm.location = p1
        muscle_arm.rotation_quaternion = direction.to_track_quat('Z','Y')
        muscle_arm.parent = arm

        # Switch to edit mode to add bones
        context.view_layer.objects.active = muscle_arm
        bpy.ops.object.mode_set(mode='EDIT')

        # Start handle
        start_handle = muscle_arm_data.edit_bones.new("Start_Handle")
        start_handle.head = Vector(0, 0, 0)
        start_handle.tail = Vector(0, 0.05, 0)  # Small size

        # Main bendy bone
        main_bone = muscle_arm_data.edit_bones.new("Main")
        main_bone.head = start_handle.tail
        main_bone.tail = Vector(0, 0, length)

        # End handle
        end_handle = muscle_arm_data.edit_bones.new("End_Handle")
        end_handle.head = main_bone.tail
        end_handle.tail = Vector(0, 0, length + 0.05)

        bpy.ops.object.mode_set(mode='OBJECT')

        # Configure B-Bone
        data_bone = muscle_arm_data.bones["Main"]
        data_bone.bbone_segments = self.bbone_segments
        data_bone.bbone_x = 0.05
        data_bone.bbone_z = 0.05
        data_bone.bbone_handle_type_start = 'ABSOLUTE'
        data_bone.bbone_handle_type_end = 'ABSOLUTE'
        data_bone.bbone_custom_handle_start = muscle_arm_data.bones["Start_Handle"]
        data_bone.bbone_custom_handle_end = muscle_arm_data.bones["End_Handle"]

        # Switch to pose mode for constraints
        bpy.ops.object.mode_set(mode='POSE')

        # Constraints for start handle (attach to b1)
        start_pb = muscle_arm.pose.bones["Start_Handle"]
        cl = start_pb.constraints.new('COPY_LOCATION')
        cl.target = arm
        cl.subtarget = b1.name
        cr = start_pb.constraints.new('COPY_ROTATION')
        cr.target = arm
        cr.subtarget = b1.name

        # Constraints for end handle (attach to b2)
        end_pb = muscle_arm.pose.bones["End_Handle"]
        cl = end_pb.constraints.new('COPY_LOCATION')
        cl.target = arm
        cl.subtarget = b2.name
        cr = end_pb.constraints.new('COPY_ROTATION')
        cr.target = arm
        cr.subtarget = b2.name

        # Stretch To for main bone (stretch to end, head fixed by copy loc)
        main_pb = muscle_arm.pose.bones["Main"]
        cl = main_pb.constraints.new('COPY_LOCATION')
        cl.target = arm
        cl.subtarget = b1.name
        st = main_pb.constraints.new('STRETCH_TO')
        st.target = arm
        st.subtarget = b2.name
        st.keep_axis = 'NONE'  # Free stretch
        st.volume = 'NO_VOLUME'  # Optional: preserve volume or not

        bpy.ops.object.mode_set(mode='OBJECT')

        # Attach mesh to armature
        muscle.parent = muscle_arm
        arm_mod = muscle.modifiers.new("Armature", 'ARMATURE')
        arm_mod.object = muscle_arm

        # Vertex group for main bone
        vg = muscle.vertex_groups.new(name="Main")
        vg.add(range(len(mesh.vertices)), 1.0, 'REPLACE')

        # Bulge shape key + driver (unchanged)
        muscle.shape_key_add(name="Basis")
        sk = muscle.shape_key_add(name="Bulge")
        half = length / 2
        for v in muscle.data.vertices:
            sk.data[v.index].co = v.co * (1.0 + 0.85 * (1.0 - abs(v.co.z/half)**1.3))
        drv = sk.driver_add("value").driver
        drv.type = 'AVERAGE'
        v = drv.variables.new()
        v.name = "a"
        v.type = 'ROTATION_DIFF'
        v.targets[0].id = arm
        v.targets[0].bone_target = b1.name
        v.targets[1].id = arm
        v.targets[1].bone_target = b2.name
        if mtype == "FLEXOR":   drv.expression = "max(a,0)"
        elif mtype == "EXTENSOR": drv.expression = "max(-a,0)"
        else: drv.expression = "abs(a)"   # DUAL

        # Tendon material (unchanged)
        mat = bpy.data.materials.get("Tendon") or bpy.data.materials.new("Tendon")
        mat.diffuse_color = (0.9, 0.85, 0.8, 1)
        muscle.data.materials.append(mat)
        for poly in muscle.data.polygons:
            if abs(poly.center.z) > half * (1 - tendon_pct/100 * 1.2):
                poly.material_index = 0

        # Collection
        coll = bpy.data.collections.get("Muscles") or bpy.data.collections.new("Muscles")
        context.scene.collection.children.link(coll)
        coll.objects.link(muscle)
        coll.objects.link(muscle_arm)

        muscle.select_set(True)
        context.view_layer.objects.active = muscle
        self.report({'INFO'}, f"{self.preset} created with bendy bone soft middle!")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)


# ─────────────────────── BIND TO SKIN (unchanged) ───────────────────────
class MUSCLE_OT_bind_skin(bpy.types.Operator):
    bl_idname = "muscle.bind_skin"
    bl_label = "Bind Muscles to Skin"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        skin = context.active_object
        if skin.type != 'MESH':
            self.report({'ERROR'}, "Select skin mesh")
            return {'CANCELLED'}
        muscles = [o for o in bpy.data.objects if o.name.startswith("MUSCLE_")]
        for m in muscles:
            dt = skin.modifiers.new(f"DT_{m.name}", 'DATA_TRANSFER')
            dt.object = m
            dt.use_loop_data = True
            dt.data_types_loops = {'VGROUP_WEIGHTS'}
            dt.loop_mapping = 'NEAREST_POLY'
            dt.mix_mode = 'ADD'
        self.report({'INFO'}, f"{len(muscles)} muscles bound!")
        return {'FINISHED'}


# ─────────────────────── PANEL ───────────────────────
class MUSCLE_PT_panel(bpy.types.Panel):
    bl_label = "BlendArmory Muscles 2.1"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Muscles"

    def draw(self, context):
        l = self.layout
        l.operator("muscle.create", text=" Create Muscle", icon='ARMATURE_DATA')
        l.separator()
        row = l.row(align=True)
        for p in ["Biceps","Triceps","Deltoid","Pectoral","Quadriceps","Dual Biceps"]:
            op = row.operator("muscle.create", text=p)
            op.preset = p
        l.separator()
        if context.object and context.object.type == 'MESH':
            l.operator("muscle.bind_skin", icon='OUTLINER_OB_MESH')


# ─────────────────────── REGISTER ───────────────────────
classes = (MUSCLE_OT_create, MUSCLE_OT_bind_skin, MUSCLE_PT_panel)

def register():
    for c in classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes): bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
