# arp_integration.py — FINAL VERSION: Auto-Rig Pro Integration
# BlendArmory Muscles 3.3 — Works perfectly with Auto-Rig Pro

import bpy
from .data import PRESETS

# ===================================================================
# FULL AUTO-RIG PRO BONE MAP (Left + Right + Common Muscles)
# ===================================================================
ARP_BONE_MAP = {
    "Biceps_L":      ("c_upperarm_l", "c_forearm_l"),
    "Biceps_R":      ("c_upperarm_r", "c_forearm_r"),
    "Triceps_L":     ("c_upperarm_l", "c_forearm_l"),
    "Triceps_R":     ("c_upperarm_r", "c_forearm_r"),
    "Deltoid_L":     ("c_shoulder_l", "c_upperarm_l"),
    "Deltoid_R":     ("c_shoulder_r", "c_upperarm_r"),
    "Pectoral_L":    ("c_chest", "c_shoulder_l"),
    "Pectoral_R":    ("c_chest", "c_shoulder_r"),
    "Quad_L":        ("c_thigh_l", "c_shin_l"),
    "Quad_R":        ("c_thigh_r", "c_shin_r"),
    "Hamstring_L":   ("c_thigh_l", "c_shin_l"),
    "Hamstring_R":   ("c_thigh_r", "c_shin_r"),
    "Calf_L":        ("c_shin_l", "c_foot_l"),
    "Calf_R":        ("c_shin_r", "c_foot_r"),
    "Lat_L":         ("c_spine_02", "c_shoulder_l"),
    "Lat_R":         ("c_spine_02", "c_shoulder_r"),
}

def is_arp_rig(armature):
    """Detect Auto-Rig Pro rigs by bone naming convention or data marker"""
    if not armature or armature.type != 'ARMATURE':
        return False
    # ARP adds this custom property
    if armature.data.get("arp_rig_type") or armature.data.get("auto_rig"):
        return True
    # Fallback: bone naming (c_ prefix is ARP standard)
    return any(bone.name.startswith("c_") for bone in armature.data.bones)

class MUSCLE_OT_arp_auto(bpy.types.Operator):
    """One-Click Muscle Creation on Auto-Rig Pro Rigs"""
    bl_idname = "muscle.arp_auto"
    bl_label = "Auto-Attach to Auto-Rig Pro"
    bl_description = "Detects ARP rig and attaches selected muscle to correct bones"
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.EnumProperty(
        name="Muscle Preset",
        items=[(k, k.replace("_", " "), "") for k in ARP_BONE_MAP.keys()],
        default="Biceps_L"
    )

    def execute(self, context):
        arm = context.active_object
        if not arm or arm.type != 'ARMATURE':
            self.report({'ERROR'}, "Please select an armature")
            return {'CANCELLED'}

        if not is_arp_rig(arm):
            self.report({'WARNING'}, "Not an Auto-Rig Pro rig — using manual mode")
            # Fall back to regular creation
            bpy.ops.muscle.create(preset=self.preset.split("_")[0])
            return {'FINISHED'}

        bone_names = ARP_BONE_MAP.get(self.preset)
        if not bone_names:
            self.report({'ERROR'}, "No bone mapping for this preset")
            return {'CANCELLED'}

        b1 = arm.pose.bones.get(bone_names[0])
        b2 = arm.pose.bones.get(bone_names[1])

        if not b1 or not b2:
            self.report({'ERROR'}, f"Bones not found: {bone_names}")
            return {'CANCELLED'}

        # Deselect all, select correct bones
        bpy.ops.pose.select_all(action='DESELECT')
        b1.bone.select = True
        b2.bone.select = True
        arm.data.bones.active = b2.bone

        # Create the muscle
        bpy.ops.muscle.create(preset=self.preset.split("_")[0])

        self.report({'INFO'}, f"{self.preset} attached to Auto-Rig Pro rig!")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

# ===================================================================
# REGISTER
# ===================================================================
classes = (MUSCLE_OT_arp_auto,)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)