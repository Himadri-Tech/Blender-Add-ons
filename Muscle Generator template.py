bl_info = {
    "name": "Muscle Generator",
    "blender": (2, 80, 0),
    "category": "Object",
    "author": "Himadri Roy Sarkar",
    "version": (1, 0, 0),
    "location": "View3D > Add > Mesh",
    "description": "Generate a simple muscle system for rigging.",
    "warning": "experimental",
    "doc_url": "https://github.com/Himadri-Tech/Blender-Add-ons.git",
    "tracker_url": "https://yourbugtrackerlink.com",
    "support": "COMMUNITY",
    "category": "Object"
}


import bpy

def create_muscle(muscle_name, parent_bone, length, thickness):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    muscle_obj = bpy.context.active_object
    muscle_obj.name = muscle_name
    
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value":(0, 0, length)})
    bpy.ops.object.mode_set(mode='OBJECT')
    
    bpy.ops.object.modifier_add(type='SUBSURF')
    bpy.context.object.modifiers["Subdivision Surface"].levels = 2
    bpy.ops.object.modifier_apply({"object": muscle_obj}, modifier="Subdivision Surface")
    
    bpy.ops.object.modifier_add(type='SMOOTH')
    bpy.context.object.modifiers["Smooth"].factor = 0.5
    bpy.ops.object.modifier_apply({"object": muscle_obj}, modifier="Smooth")
    
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')
    
    # Create bone for the muscle
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.armature.bone_primitive_add(name=muscle_name)
    bpy.ops.object.mode_set(mode='OBJECT')
    muscle_bone = bpy.context.object.data.edit_bones[muscle_name]
    muscle_bone.head = parent_bone.head
    muscle_bone.tail = muscle_bone.head + (0, 0, length)
    
    # Parent the muscle object to the armature
    bpy.context.view_layer.objects.active = bpy.data.objects[parent_bone.id_data.name]
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.bone_select_all(action='DESELECT')
    bpy.context.object.data.bones.active = bpy.context.object.data.bones[parent_bone.name]
    bpy.ops.pose.bone_select()
    bpy.context.view_layer.objects.active = bpy.data.objects[muscle_obj.name]
    bpy.ops.object.parent_set(type='BONE')
    
    return muscle_obj

class OBJECT_OT_generate_muscle_system(bpy.types.Operator):
    bl_idname = "object.generate_muscle_system"
    bl_label = "Generate Muscle System"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Replace 'Armature' and 'Spine' with your armature and spine bone names
        armature_name = 'YourArmatureName'  # Change 'YourArmatureName' to the actual name of your armature
        spine_bone_name = 'Spine'

        # Select the armature object
        bpy.data.objects[armature_name].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[armature_name]

        # Switch to Pose Mode
        bpy.ops.object.mode_set(mode='POSE')

        # Create muscles along the spine
        for i in range(1, 6):
            muscle_name = f'Muscle_{i}'
            length = 1.0
            thickness = 0.1
            parent_bone = bpy.context.object.pose.bones[spine_bone_name]

            create_muscle(muscle_name, parent_bone, length, thickness)

            # Move to the next spine bone
            bpy.ops.pose.bone_select_all(action='DESELECT')
            bpy.context.object.data.bones.active = bpy.context.object.data.bones[spine_bone_name + f'.00{i}']
            bpy.ops.pose.bone_select()

        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_generate_muscle_system.bl_idname)

def register():
    bpy.utils.register_class(OBJECT_OT_generate_muscle_system)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_generate_muscle_system)
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)

if __name__ == "__main__":
    register()
