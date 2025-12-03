# panel.py — FINAL CLEAN VERSION (NO INDENTED COMMENTS)
# BlendArmory Muscles 3.3

import bpy
from .data import PRESETS

class MUSCLE_PT_create(bpy.types.Panel):
    bl_label = "Create"
    bl_category = "Muscles"
    bl_idname = "MUSCLE_PT_create"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    @classmethod
    def poll(cls, context):
        return context.mode in {'OBJECT', 'POSE'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        col = layout.column(align=True)
        col.label(text="CREATE:", icon='ARMATURE_DATA')

        col.operator("muscle.add_basic", text="Add Basic Muscle", icon='RIGHTARROW_THIN')
        col.operator("muscle.add_stylized", text="Add Stylized Muscle", icon='RIGHTARROW_THIN')
        col.operator("muscle.add_strip", text="Add Strip Muscle", icon='RIGHTARROW_THIN')

        if context.object and context.object.type == 'MESH' and "Muscle_XID" not in context.object:
            col.operator("muscle.convert", text="Convert Mesh to Muscle", icon='RNA_ADD')

        col.separator()
        col.prop(scn, "Muscle_Scale", text="Global Scale", slider=True)
        col.prop(scn, "Create_Type", text="Targeting Method")
        col.prop(scn, "Muscle_Name", text="Name")
        col.prop(scn, "use_Affixes", text="Use Affixes")
        if scn.use_Affixes:
            row = col.row(align=True)
            row.prop(scn, "Prefix", text="")
            row.prop(scn, "Suffix", text="")

        col.separator()
        col.label(text="Presets:")
        row = col.row(align=True)
        for p in PRESETS:
            op = row.operator("muscle.create", text=p)
            op.preset = p

        col.separator()
        col.operator("muscle.arp_auto", text="Auto-Attach to Auto-Rig Pro", icon='PLUGIN')

        col.separator()
        row = col.row(align=True)
        op = row.operator("wm.url_open", text="Check for Updates", icon='QUESTION')
        op.url = "https://github.com/Himadri-Tech/Blender-Add-ons"


class MUSCLE_PT_system(bpy.types.Panel):
    bl_label = "Muscle System"
    bl_category = "Muscles"
    bl_idname = "MUSCLE_PT_system"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    @classmethod
    def poll(cls, context):
        return context.object and "Muscle_XID" in context.object

    def draw(self, context):
        layout = self.layout
        obj = context.object

        col = layout.column(align=True)
        col.label(text="Mesh", icon='MESH_CUBE')
        row = col.row()
        row.prop(obj, "Muscle_Render")
        row.prop(obj, "Muscle_View3D")
        col.prop(obj, "Muscle_Type_INT", text="Flexor / Extensor")
        col.prop(obj, "Base_Length_INT", slider=True)
        col.prop(obj, "Volume_INT", slider=True)
        col.prop(obj, "Muscle_Size", slider=True)
        col.prop(obj, "Muscle_Offset", slider=True)

        col.separator()
        col.label(text="Dynamics", icon='PHYSICS')
        row = col.row()
        row.prop(obj, "Dynamics_Render")
        row.prop(obj, "Dynamics_View3D")
        col.prop(obj, "Jiggle_Springiness", slider=True)
        col.prop(obj, "Jiggle_Stiffness", slider=True)
        col.prop(obj, "Jiggle_Mass", slider=True)
        col.prop(obj, "Jiggle_Damping", slider=True)

        col.separator()
        col.operator("muscle.smart_update", text="Smart Update", icon='FILE_REFRESH')
        col.operator("muscle.delete", text="Delete Muscle", icon='CANCEL')


class OBJECT_UL_pins(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item, "name", text="", emboss=False)


class MUSCLE_PT_pinning(bpy.types.Panel):
    bl_label = "Pinning"
    bl_category = "Muscles"
    bl_idname = "MUSCLE_PT_pinning"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    @classmethod
    def poll(cls, context):
        return context.object and "Muscle_XID" in context.object

    def draw(self, context):
        layout = self.layout
        obj = context.object

        col = layout.column(align=True)
        row = col.row()
        row.prop(obj, "Pinning_Render")
        row.prop(obj, "Pinning_View3D")
        col.prop(obj, "Pin_Size", slider=True)

        col.separator()
        row = col.row()
        row.template_list("OBJECT_UL_pins", "", obj, "custom", obj, "custom_index", rows=4)
        col2 = row.column(align=True)
        col2.operator("muscle.pin_action", icon='ADD', text="").action = 'ADD'
        col2.operator("muscle.pin_action", icon='REMOVE', text="").action = 'REMOVE'


# Register all classes
classes = (
    MUSCLE_PT_create,
    MUSCLE_PT_system,
    OBJECT_UL_pins,
    MUSCLE_PT_pinning,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
