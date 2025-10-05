import bpy
import csv
import math
import os
from sys import argv

# === SETTINGS ===
csv_file = f"/Users/deadfloppy/Projects/AdditiveWebsite/with-docker/tmp/{argv[5]}/{argv[5]}.csv"  
delimiter = ","
skip_header = False
mesh_name = "SolidSurface"


base_thickness = 5
boombox_base_thickness = 0
record_base_thickness = 2

origin_offset = (0.0, 0.0, 0.0)
#boomboxOffset = (7.0527, 89.9921, 42.616)  
boomboxOffset = (3.16276, 86.8293, 42.616-5)  
recordOffset = (41, 50, 8.2521)  

flip_x = False
flip_y = False
flip_z = False

target_width = 100
target_length = 100
target_height = 20

radius = 3.0  # inner record radius
circle_name = "DonutPath"

# --- Choose which model to import ---
model_choice = "none"   ## <-- Options: "record", "boombox", "none"

# --- File paths ---
record_player_path = r"D:/453 project/Record_player_model_no_spectrogram.stl"
boombox_path       = r"D:/453 project/Boombox_model_no_spectrogramver2.stl"


def detect_num_cols(csv_file, delimiter, skip_header):
    with open(csv_file, newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        if skip_header:
            next(reader, None)  # skip first line

        first_val = None
        count = 0
        for row in reader:
            if not row: 
                continue
            y = int(row[1])  # second column
            if first_val is None:
                first_val = y
            if y == first_val:
                count += 1
            else:
                break
        return count
    
num_cols = detect_num_cols(csv_file, delimiter, skip_header)  
print("Detected num_cols:", num_cols)

def import_grid_surface_solid(csv_file, delimiter, skip_header, num_cols, base_thickness):
    points = []
    with open(csv_file, newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        if skip_header:
            next(reader)
        for row in reader:
            try:
                x, y, z = map(float, row[:3])
                points.append((x, y, z)) # stores every 3 values as a touple, which is then turned into a point, x,y,z
            except:
                print(f"Skipping row: {row}")

    if not points:
        print("No valid points loaded.")
        return

    bottom_z = (min(p[2] for p in points) - base_thickness) #finds the lowest z value to define as the bottom of the volume
    
    #normalize origin
    x0, y0, z0 = points[0] # defines the position of the first point aka the offset from 0,0,0


    points = [(x - x0, y - y0, z - bottom_z) for (x, y, z) in points] #subtracts the offset from each data point to shift it to the origin

    bottom_z = (min(p[2] for p in points) - base_thickness) #finds the lowest z value to define as the bottom of the volume

    num_rows = len(points) // num_cols

    verts = points[:]  #vertices
    faces = []

    for r in range(num_rows - 1):
        for c in range(num_cols - 1):
            v1 = r * num_cols + c
            v2 = v1 + 1
            v3 = v1 + num_cols + 1
            v4 = v1 + num_cols
            faces.append((v1, v2, v3, v4))

    # bottom
    base_start = len(verts) # need to set the start as the end of the list of points so we dont overwrite
    for r in range(num_rows):
        for c in range(num_cols):
            x, y, _ = points[r * num_cols + c]
            verts.append((x, y, bottom_z)) # just sorts through all x and y values with a set z value and creates points

    for r in range(num_rows - 1): # follows the same philosophy as above but reverses the order of points so the normals face down to create a solid object
        for c in range(num_cols - 1):
            v1 = base_start + r * num_cols + c
            v2 = v1 + 1
            v3 = v1 + num_cols + 1
            v4 = v1 + num_cols
            faces.append((v4, v3, v2, v1))  # reversed for outward normals

    for r in range(num_rows - 1):
        # left edge
        top1 = r * num_cols #the start of each row is a multiple of the number of columns so we can just multiply the two
        top2 = top1 + num_cols # the next corner in the square is the start of the next row so we just add it on
        bot1 = base_start + top1 # since the top and bottom were draw in the same order we can just incrememnt the top by the length of the top grid aka the base starting point
        bot2 = base_start + top2 # same as above but for the second point
        faces.append((top1, top2, bot2, bot1))
        # right edge
        top1 = r * num_cols + (num_cols - 1) # same as the left edge but we also add num_cols -1 to shift it over to the other edge
        top2 = top1 + num_cols
        bot1 = base_start + top1
        bot2 = base_start + top2
        faces.append((bot1, bot2, top2, top1))

    for c in range(num_cols - 1):
        # front edge
        top1 = c # much simpler, just inrement across the row for the corners
        top2 = c + 1
        bot1 = base_start + top1 # shift the point by the length of the top grid points aka base start
        bot2 = base_start + top2
        faces.append((bot1, bot2, top2, top1))
        # back edge
        top1 = (num_rows - 1) * num_cols + c # increment across the row but add the total len of all row and columns before it to shift it to the last row
        top2 = top1 + 1 #same idea but one over
        bot1 = base_start + top1 # again since the top and bottom were made in the same order just increment by the length of the top
        bot2 = base_start + top2 #same
        faces.append((top1, top2, bot2, bot1))

    #nesh
    mesh = bpy.data.meshes.new(mesh_name) #creates enmpty mesh
    obj = bpy.data.objects.new(mesh_name, mesh) #creates object for the mesh
    bpy.context.collection.objects.link(obj) # adds to collection, basically just initializes it in the viewport
    mesh.from_pydata(verts, [], faces) # adds the created geometry to the mesh, verts and faces, edges are redundant
    mesh.update() # updates changes
    

def import_stl(filepath, object_name):
    bpy.ops.wm.stl_import(filepath=filepath)
    obj = bpy.context.selected_objects[0]
    obj.name = object_name
    obj.location = (0.0, 0.0, 0.0)  # move to origin
    return obj

######### MAIN ############

if model_choice == "record":
    obj = import_stl(record_player_path, "RecordPlayer")
    origin_offset = recordOffset
    target_width = 10
    target_length = 30
    target_height = 30
    flip_y = False
    flip_x = True
    base_thickness = record_base_thickness
    if circle_name in bpy.data.objects:
        circle = bpy.data.objects[circle_name]
    else:
        bpy.ops.curve.primitive_bezier_circle_add(radius=radius, location=(50, 50, 13.1182))
        circle = bpy.context.active_object
        circle.name = circle_name
        # Ensure circle has correct radius
        circle.scale = (radius, radius, radius)
    print("Imported Record Player model at origin")
elif model_choice == "boombox":
    obj = import_stl(boombox_path, "Boombox")
    origin_offset = boomboxOffset  
    target_width = 24.44628
    target_length = 83.66658
    target_height = 35
    #target_length = 89.9921
    #target_width = 30.***
    base_thickness = boombox_base_thickness
    flip_y = True    
    flip_z = True   
    print("Imported Boombox model at origin")
elif model_choice == "none":
    print("No model imported")
    origin_offset = (0,100,0) 
    target_width = 50.0
    target_length = 100.0
    target_height = 30.0
    flip_y = True
else:
    print(f"Unknown option: {model_choice}")

import_grid_surface_solid(csv_file, delimiter, skip_header, num_cols, base_thickness) # actually runs the fucntion

obj = bpy.data.objects["SolidSurface"]

xoffset, yoffset, zoffset = origin_offset

coords = [obj.matrix_world @ v.co for v in obj.data.vertices]  # world-space vertices

x_min = min(v.x for v in coords)
x_max = max(v.x for v in coords)
y_min = min(v.y for v in coords)
y_max = max(v.y for v in coords)
z_min = min(v.z for v in coords)
z_max = max(v.z for v in coords)

current_width = x_max - x_min
current_length = y_max - y_min
current_height = z_max - z_min

scale_x = target_width / current_width
scale_y = target_length / current_length
scale_z = target_height / current_height

obj.scale = (scale_x, scale_y, scale_z)

coords_scaled = [obj.matrix_world @ v.co for v in obj.data.vertices]
new_x_min = min(v.x for v in coords_scaled)
new_y_min = min(v.y for v in coords_scaled)
new_z_min = min(v.z for v in coords_scaled)

trans_x = xoffset - new_x_min
trans_y = yoffset - new_y_min
trans_z = zoffset - new_z_min

obj.location.x += trans_x
obj.location.y += trans_y
obj.location.z += trans_z


mesh = obj.data

if flip_x:
    for v in mesh.vertices:
        v.co.x *= -1  # flip X
if flip_y:
    for v in mesh.vertices:
        v.co.y *= -1  # flip Y
if flip_z:
    for v in mesh.vertices:
        v.co.z *= -1  # flip Z


if model_choice == "record":
    
    bbox = [obj.matrix_world @ v.co for v in obj.data.vertices]
    xmin = min(v.y for v in bbox)
    xmax = max(v.y for v in bbox)
    obj_length = xmax - xmin
    
    # Scale object to match circle circumference
    circumference = 2 * math.pi * 9   # ~18.85
    scale_factor = circumference / 10   # ~1.885
    obj.scale[0] *= scale_factor


    # Add curve modifier
    mod = obj.modifiers.new(name="DonutWarp", type='CURVE')
    mod.object = circle
    mod.deform_axis = 'POS_X'  # Change if your object is oriented differently
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)

if model_choice == "boombox": #boolean subtract
    
    
    bpy.ops.mesh.primitive_cube_add(size=2, location=(3.16276+24.4463/2, 86.8293-83.6666/2, 42.616-5/2)); bpy.context.active_object.scale=(28/2, 88/2, 5/2)

    bpy.ops.mesh.primitive_cube_add(size=2, location=(15.3885+5, 44.9837, 42.616-1)); bpy.context.active_object.scale=(5/2, 70/2, 5/2)
    bpy.ops.mesh.primitive_cube_add(size=2, location=(15.3885-5, 44.9837, 42.616-1)); bpy.context.active_object.scale=(5/2, 70/2, 5/2)

    bpy.context.view_layer.objects.active = bpy.data.objects["Cube.001"]; [bpy.data.objects[n].select_set(True) for n in ("Cube.001","Cube.002")]; bpy.ops.object.join()

    
    cube = bpy.data.objects["Cube"]
    surface = bpy.data.objects["SolidSurface"]

    # Make SolidSurface the base
    bpy.context.view_layer.objects.active = surface
    cube.select_set(True)
    surface.select_set(True)

    # Add a union boolean on SolidSurface
    bool_mod = surface.modifiers.new("Union", "BOOLEAN")
    bool_mod.operation = 'UNION'
    bool_mod.object = cube

    # Apply the union
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
        
    bpy.data.objects.remove(cube, do_unlink=True)

    main_obj = bpy.data.objects["Boombox"]   # replace with your main object name

    # Select the tool object (the cutter)
    tool_obj = bpy.data.objects["SolidSurface"] # replace with your cutter object name

    # Add a boolean modifier to the main object
    bool_mod = main_obj.modifiers.new(name="Boolean_Cut", type='BOOLEAN')
    bool_mod.object = tool_obj
    bool_mod.operation = 'DIFFERENCE'

    # Apply the modifier so the cut is permanent
    bpy.context.view_layer.objects.active = main_obj
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
    
    main_obj = bpy.data.objects["SolidSurface"]   # base mesh
    tool_obj = bpy.data.objects["Cube.001"]       # cutter

    bool_mod = main_obj.modifiers.new(name="Boolean_Subtract_Cube", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = tool_obj

    bpy.context.view_layer.objects.active = main_obj
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
        
    bpy.data.objects.remove(tool_obj, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')

"""
# Select all mesh objects
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        obj.select_set(True)

# Make the active object the first selected one
bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]

# Join selected objects into one
bpy.ops.object.join()

"""

base_path = f"tmp/{argv[5]}"
ext = ".stl"

counter = 1
while True:
    filepath = f"{base_path}_{counter}{ext}"
    if not os.path.exists(filepath):
        break
    counter += 1

# Export STL with unique name
bpy.ops.wm.stl_export(filepath=filepath, check_existing=True)
bpy.ops.wm.stl_export(filepath=f'tmp/{argv[5]}/{argv[5]}.stl', check_existing=True)
