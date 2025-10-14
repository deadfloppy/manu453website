import bpy
import os
from mathutils import Vector
from sys import argv
import platform

def main():
    jobId = argv[argv.index("--") + 1]
    print(f"Joining STL files for jobId: {jobId}")
    # Check if on Linux, then enable STL addon
    if os.path.exists(f"/mnt/volume_nov"):
        bpy.ops.preferences.addon_enable(module='io_mesh_stl')

    def exportMesh(filepath):
        # if mac then blender v<4.2 and new implementation is used 
        if not os.path.exists(f"/mnt/volume_nov"):
            bpy.ops.wm.stl_export(filepath=filepath)
        else:
            bpy.ops.export_mesh.stl(filepath=filepath, check_existing=True)

    def importMesh(filepath):
        if not os.path.exists(f"/mnt/volume_nov"):
            bpy.ops.wm.stl_import(filepath=filepath)
        else:
            bpy.ops.import_mesh.stl(filepath=filepath)

    # figure out base path
    if platform.system() == "Darwin":
        # MacOS
        base_path = f"/Users/deadfloppy/Projects/AdditiveWebsite/with-docker/public/models/"
    else:
        # Linux
        base_path = f"/mnt/volume_nov/with-docker/public/models/"

    # -----------------------------
    # CONFIG
    # -----------------------------
    model1_path = base_path+f"{jobId}-1.stl"
    model2_path = base_path+f"{jobId}-2.stl"
    output_path = base_path+f"{jobId}.stl"
    spacing = 5.0  # distance between models

    # -----------------------------
    # CLEAN SCENE
    # -----------------------------
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # -----------------------------
    # FUNCTION TO IMPORT STL
    # -----------------------------
    def import_stl(filepath):
        importMesh(filepath=filepath)
        obj = bpy.context.selected_objects[0]
        return obj

    # -----------------------------
    # IMPORT MODELS
    # -----------------------------
    obj1 = import_stl(model1_path)
    obj2 = import_stl(model2_path)

    # -----------------------------
    # CENTER GEOMETRY
    # -----------------------------
    def center_obj(obj):
        # Move origin to geometry center
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        # Center at world origin
        obj.location = Vector((0,0,0))

    center_obj(obj1)
    #center_obj(obj2)

    # -----------------------------
    # POSITION MODELS NEXT TO EACH OTHER
    # -----------------------------

    # Flip obj2 upside down first
    obj2.rotation_euler.x = 3.14159
    bpy.context.view_layer.update()

    # Compute bottom Z of obj1
    obj1_bottom_z = min((obj1.matrix_world @ v.co).z for v in obj1.data.vertices)

    # Compute bottom Z of obj2 (after flipping)
    obj2_bottom_z = min((obj2.matrix_world @ v.co).z for v in obj2.data.vertices)

    # Align obj2 bottom to obj1 bottom
    shift_z = obj1_bottom_z - obj2_bottom_z
    obj2.location.z += shift_z

    # Move obj2 slightly on X-axis
    obj2.location.x += 50  # spacing is already defined (5.0) or choose any small value
    bpy.context.view_layer.update()


    # -----------------------------
    # EXPORT COMBINED STL
    # -----------------------------
    # Select both objects
    bpy.ops.object.select_all(action='DESELECT')
    obj1.select_set(True)
    obj2.select_set(True)
    bpy.context.view_layer.objects.active = obj1

    # Export combined STL
    exportMesh(filepath=output_path)
    print(f"Combined STL saved to: {output_path}")
    return 0

if __name__ == "__main__":
    main()