"""

To be implemented
- size mapping, is dependant on how we choose to do the data processing, should map the overall x y and z size to present sizes by multiplying the data in each axis by a factor
- generating musical themed accessory and placing the spectrogram on to it
    - warping the spectrogram as required
        - ex. into a circle for a record 
- decimation / subdivision based on printing specs
- QOL / Polishing features
    - a textured base
    - a base with the audio file name engraved
    - bevel the base
- any other data parsed by the group
- display the key of the song
- show the beat
- 

"""

import bpy
import csv
import math

# === SETTINGS ===
csv_file = "D:\downloads\mel_spectrogram_points_clean.csv"  
delimiter = ","
skip_header = False
mesh_name = "SolidSurface"

num_cols = 70
base_thickness = 5
boombox_base_thickness = 0
record_base_thickness = 2

origin_offset = (0.0, 0.0, 0.0)
boomboxOffset = (0.0, 89.9921, 42.616)  
recordOffset = (0.0, 0.0, 42.616)  



# --- Choose which model to import ---
# Options: "record", "boombox", "none"
model_choice = "none"   # <-- change this to "boombox" or "none"

# --- File paths ---
record_player_path = r"D:/453 project/Record_player_model_no_spectrogram.stl"
boombox_path       = r"D:/453 project/Boombox_model_no_spectrogram.stl"


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
    target_width = 30.7717
    target_length = 89.9921
    target_height = 20
    base_thickness = record_base_thickness
    print("Imported Record Player model at origin")
elif model_choice == "boombox":
    obj = import_stl(boombox_path, "Boombox")
    origin_offset = boomboxOffset  
    target_width = 30.7717
    target_length = 89.9921
    target_height = 20
    base_thickness = boombox_base_thickness
    print("Imported Boombox model at origin")
elif model_choice == "none":
    print("No model imported")
    origin_offset = (0,100,0) 
    target_width = 30.0
    target_length = 100.0
    target_height = 30.0
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
for v in mesh.vertices:
    v.co.y *= -1  # flip Y
