import bpy
import csv
import math
import os
from collections import defaultdict
import sys
# clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# bpy.ops.preferences.addon_enable(module='io_mesh_stl')  # ensure add-on enabled

jobId = sys.argv[5]
mode = sys.argv[6] if len(sys.argv) > 6 else "none"

# Check if on Linux, then enable STL addon
bpy.ops.preferences.addon_enable(module='io_mesh_stl')

# === SETTINGS ===
if not os.path.exists(f"/mnt/volume_nov"):
    csv_file = os.path.join("/Users/deadfloppy/Projects/AdditiveWebsite/main-docker/tmp", jobId, f"{jobId}.csv")
else:
    csv_file = f"/mnt/volume_nov/with-docker/tmp/{jobId}/{jobId}.csv"  
print(csv_file)
delimiter = ","
skip_header = True
SHOW_BANDS = False  # True = generate band meshes (flat freq per time). False = single mesh
mesh_name = "SolidSurface"

# Base thicknesses
base_thickness = 2
boombox_base_thickness = 0
record_base_thickness = 2

# Placement/offsets (used for single surface mode)
origin_offset = (0.0, 0.0, 0.0)
boomboxOffset = (3.16276, 86.8293, 42.616 - 5)
recordOffset = (41, 50, 8.2521)

flip_x = False
flip_y = False
flip_z = False

# --- SIZE SETTINGS ---
# Band sizes
target_band_width = 100
target_band_length = 20
target_band_height = 70

# Single mesh sizes (defaults; overridden by model_choice branch)
target_single_width = 100
target_single_length = 100
target_single_height = 30

# spacing between band objects
band_spacing_extra = 0  # extra gap between band blocks

radius = 3.0
circle_name = "DonutPath"

# Get paths
if not os.path.exists(f"/mnt/volume_nov"):
    modelpath = "/Users/deadfloppy/Projects/AdditiveWebsite/main-docker/public"
else:
    modelpath = "/mnt/volume_nov/with-docker/public"

# --- Model choice ---
model_choice = mode  # "record", "boombox", "none"
record_player_path = f"{modelpath}/Record_player_model_no_spectrogram.stl"
boombox_path       = f"{modelpath}/Boombox_model_no_spectrogramver2.stl"

# --- FUNCTIONS ---
def detect_num_cols(csv_file, delimiter, skip_header):
    with open(csv_file, newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        if skip_header:
            next(reader, None)
        first_val = None
        count = 0
        for row in reader:
            if not row:
                continue
            try:
                y = int(float(row[1]))
            except Exception:
                # if parsing fails, skip row
                continue
            if first_val is None:
                first_val = y
            if y == first_val:
                count += 1
            else:
                break
        return count

num_cols = detect_num_cols(csv_file, delimiter, skip_header)
print("Detected num_cols:", num_cols)


def import_stl(filepath, object_name):
    bpy.ops.export_mesh.stl(filepath=filepath)
    obj = bpy.context.selected_objects[0]
    obj.name = object_name
    obj.location = (0.0, 0.0, 0.0)
    return obj


def import_grid_surface(points, mesh_name, num_cols, base_thickness,
                        target_width, target_length, show_bands=False,
                        global_bottom_z=None):
    """
    Create a mesh for a set of points (single band), using a shared global_bottom_z if provided.
    """
    if not points:
        print(f"No valid points for {mesh_name}.")
        return None

    # Group points by time
    time_dict = defaultdict(list)
    for x, y, z in points:
        time_dict[x].append((x, y, z))

    time_values_sorted = sorted(time_dict.keys())
    num_rows = len(time_values_sorted)
    num_cols_local = max(len(vs) for vs in time_dict.values())

    verts = []
    faces = []

    # === Determine bottom Z ===
    if show_bands and global_bottom_z is None:
        # fallback: calculate per-band bottom if global not provided
        avg_dict = {t: sum(p[2] for p in row) / len(row)
                    for t, row in time_dict.items()}
        global_bottom_z = min(avg_dict.values()) - base_thickness
    elif not show_bands and global_bottom_z is None:
        global_bottom_z = min(p[2] for p in points) - base_thickness

    # === Build vertices ===
    time_min = min(time_values_sorted)
    time_max = max(time_values_sorted)

    for t in time_values_sorted:
        row_points = time_dict[t]
        row_points.sort(key=lambda p: p[1])

        if show_bands:
            avg_z = sum(p[2] for p in row_points) / len(row_points)

        for p_idx, (x, y, z) in enumerate(row_points):
            x_scaled = (t - time_min) / (time_max - time_min) * target_width
            y_scaled = p_idx / (len(row_points) - 1) * target_length if len(row_points) > 1 else 0

            if show_bands:
                z_scaled = avg_z - global_bottom_z
            else:
                z_scaled = z - global_bottom_z

            verts.append((x_scaled, y_scaled, z_scaled))

    # === Build faces ===
    for r in range(num_rows - 1):
        for c in range(num_cols_local - 1):
            v1 = r * num_cols_local + c
            v2 = v1 + 1
            v3 = v1 + num_cols_local + 1
            v4 = v1 + num_cols_local
            faces.append((v1, v2, v3, v4))

    # === Bottom vertices ===
    base_start = len(verts)
    for v in verts[:]:
        x, y, _ = v
        verts.append((x, y, -base_thickness))

    # Bottom faces
    for r in range(num_rows - 1):
        for c in range(num_cols_local - 1):
            v1 = base_start + r * num_cols_local + c
            v2 = v1 + 1
            v3 = v1 + num_cols_local + 1
            v4 = v1 + num_cols_local
            faces.append((v4, v3, v2, v1))

    # Side walls
    for r in range(num_rows - 1):
        top1 = r * num_cols_local
        top2 = top1 + num_cols_local
        bot1 = base_start + top1
        bot2 = base_start + top2
        faces.append((top1, top2, bot2, bot1))

        top1 = r * num_cols_local + (num_cols_local - 1)
        top2 = top1 + num_cols_local
        bot1 = base_start + top1
        bot2 = base_start + top2
        faces.append((bot1, bot2, top2, top1))

    for c in range(num_cols_local - 1):
        top1 = c
        top2 = c + 1
        bot1 = base_start + top1
        bot2 = base_start + top2
        faces.append((bot1, bot2, top2, top1))

        top1 = (num_rows - 1) * num_cols_local + c
        top2 = top1 + 1
        bot1 = base_start + top1
        bot2 = base_start + top2
        faces.append((top1, top2, bot2, bot1))

    # === Create mesh ===
    mesh = bpy.data.meshes.new(mesh_name)
    obj = bpy.data.objects.new(mesh_name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    print(f"Created {mesh_name}, rows={num_rows}, cols={num_cols_local}, bands={show_bands}")
    return obj


def import_grid_surface_solid(csv_file, delimiter, skip_header, num_cols, base_thickness):
    """
    Create a single solid surface mesh from the whole CSV.
    Mesh origin/bottom will be at (0,0,-base_thickness).
    """
    points = []
    with open(csv_file, newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        if skip_header:
            next(reader)
        for row in reader:
            try:
                x, y, z = map(float, row[:3])
                points.append((x, y, z))
            except:
                print(f"Skipping row: {row}")

    if not points:
        print("No valid points loaded.")
        return None

    # Normalize so mesh starts at origin (min corner -> 0,0,0)
    x_min = min(p[0] for p in points)
    y_min = min(p[1] for p in points)
    z_min = min(p[2] for p in points)
    points = [(x - x_min, y - y_min, z - z_min) for (x, y, z) in points]

    num_rows = len(points) // num_cols
    verts = points[:]
    faces = []

    # Top faces
    for r in range(num_rows - 1):
        for c in range(num_cols - 1):
            v1 = r * num_cols + c
            v2 = v1 + 1
            v3 = v1 + num_cols + 1
            v4 = v1 + num_cols
            faces.append((v1, v2, v3, v4))

    # Bottom
    base_start = len(verts)
    for r in range(num_rows):
        for c in range(num_cols):
            x, y, _ = points[r * num_cols + c]
            verts.append((x, y, -base_thickness))

    # Bottom faces
    for r in range(num_rows - 1):
        for c in range(num_cols - 1):
            v1 = base_start + r * num_cols + c
            v2 = v1 + 1
            v3 = v1 + num_cols + 1
            v4 = v1 + num_cols
            faces.append((v4, v3, v2, v1))

    # Side walls
    for r in range(num_rows - 1):
        top1 = r * num_cols
        top2 = top1 + num_cols
        bot1 = base_start + top1
        bot2 = base_start + top2
        faces.append((top1, top2, bot2, bot1))
        top1 = r * num_cols + (num_cols - 1)
        top2 = top1 + num_cols
        bot1 = base_start + top1
        bot2 = base_start + top2
        faces.append((bot1, bot2, top2, top1))

    for c in range(num_cols - 1):
        top1 = c
        top2 = c + 1
        bot1 = base_start + top1
        bot2 = base_start + top2
        faces.append((bot1, bot2, top2, top1))
        top1 = (num_rows - 1) * num_cols + c
        top2 = top1 + 1
        bot1 = base_start + top1
        bot2 = base_start + top2
        faces.append((top1, top2, bot2, bot1))

    mesh = bpy.data.meshes.new(mesh_name)
    obj = bpy.data.objects.new(mesh_name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    print(f"Created solid surface mesh {mesh_name} with {num_rows} rows × {num_cols} cols")
    return obj


# --- CSV DATA read ---
groups = {"1": [], "2": [], "3": [], "4": [], "5": []}
all_points = []
with open(csv_file, newline="") as f:
    reader = csv.reader(f, delimiter=delimiter)
    if skip_header:
        next(reader)
    for row in reader:
        try:
            x, y, z = map(float, row[:3])
            all_points.append((x, y, z))
            if SHOW_BANDS and len(row) > 3:
                label = row[3].strip()
                if label in groups:
                    groups[label].append((x, y, z))
        except:
            pass

if not all_points:
    print("No points found in CSV.")
    raise SystemExit

global_bottom_z = min(p[2] for p in all_points) - base_thickness

# --- CREATE MESHES ---
band_objects = []
if SHOW_BANDS:
    # Compute the lowest averaged height across all bands
    all_avg_zs = []
    for points in groups.values():
        time_dict = defaultdict(list)
        for x, y, z in points:
            time_dict[x].append(z)
        for z_list in time_dict.values():
            avg_z = sum(z_list) / len(z_list)
            all_avg_zs.append(avg_z)

    global_bottom_z = min(all_avg_zs) - base_thickness

    # Then create each band using this global bottom
    spacing = target_band_length + band_spacing_extra
    for i, (label, points) in enumerate(groups.items()):
        obj = import_grid_surface(
            points, f"Mesh_{label}", num_cols, base_thickness,
            target_band_width, target_band_length,
            show_bands=SHOW_BANDS,
            global_bottom_z=global_bottom_z  # <-- pass it here
        )
        if obj:
            obj.location.y += i * spacing
            band_objects.append(obj)

# If SHOW_BANDS is False, make single surface
single_surface_obj = None
if not SHOW_BANDS:
    
    if model_choice == "record":
        single_surface_obj = import_grid_surface_solid(csv_file, delimiter, skip_header, num_cols, base_thickness)
    elif model_choice == "boombox":
        single_surface_obj = import_grid_surface_solid(csv_file, delimiter, skip_header, num_cols, boombox_base_thickness)
    else:
        single_surface_obj = import_grid_surface_solid(csv_file, delimiter, skip_header, num_cols, base_thickness)
        
        
    if single_surface_obj is None:
        raise RuntimeError("Failed to create single surface.")

# --- MODEL / MODIFIER LOGIC ---
# We want to apply model handling in two modes:
# 1) If SHOW_BANDS=True and model_choice != 'none', apply modifiers to each band object individually.
# 2) If SHOW_BANDS=False, apply modifiers to the single surface object (as before).

def ensure_circle():
    if circle_name in bpy.data.objects:
        return bpy.data.objects[circle_name]
    bpy.ops.curve.primitive_bezier_circle_add(radius=radius, location=(50, 50, 13.1182))
    circle = bpy.context.active_object
    circle.name = circle_name
    circle.scale = (radius, radius, radius)
    return circle

def apply_record_modifiers_to_object(obj):
    # Set model-specific parameters
    # For bands we use band sizes; for single surface target_single_* should already be set
    # Warp object to circle
    circle = ensure_circle()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new(name="DonutWarp", type='CURVE')
    mod.object = circle
    mod.deform_axis = 'POS_X'
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.select_set(False)

def apply_boombox_modifiers_to_object(obj, tw, tl, th):
        
        # === Build up cutters ===
    bpy.ops.mesh.primitive_cube_add(size=2, location=(3.16276+24.4463/2, 86.8293-83.6666/2, 42.616-5/2))
    bpy.context.active_object.scale = (28/2, 88/2, 5/2)

    bpy.ops.mesh.primitive_cube_add(size=2, location=(15.3885+5, 44.9837, 42.616-1))
    bpy.context.active_object.scale = (5/2, 70/2, 5/2)

    bpy.ops.mesh.primitive_cube_add(size=2, location=(15.3885-5, 44.9837, 42.616-1))
    bpy.context.active_object.scale = (5/2, 70/2, 5/2)

    # Join Cube.001 and Cube.002
    bpy.context.view_layer.objects.active = bpy.data.objects["Cube.001"]
    for n in ("Cube.001", "Cube.002"):
        bpy.data.objects[n].select_set(True)
    bpy.ops.object.join()

    # === Union cube into SolidSurface ===
    cube = bpy.data.objects["Cube"]
    surface = bpy.data.objects["SolidSurface"]

    bpy.context.view_layer.objects.active = surface
    cube.select_set(True)
    surface.select_set(True)

    bool_mod = surface.modifiers.new("Union", "BOOLEAN")
    bool_mod.operation = 'UNION'
    bool_mod.object = cube
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)

    bpy.data.objects.remove(cube, do_unlink=True)

    # === Cut SolidSurface from Boombox ===
    main_obj = bpy.data.objects["Boombox"]          # main object
    tool_obj = bpy.data.objects["SolidSurface"]     # cutter (unioned surface)
    
    dup_surface = tool_obj.copy()
    dup_surface.data = tool_obj.data.copy()
    dup_surface.name = "SolidSurface2"
    bpy.context.collection.objects.link(dup_surface)
    
    cutter_obj = bpy.data.objects["SolidSurface2"]
    
    bpy.context.view_layer.objects.active = cutter_obj
    cutter_obj.select_set(True)

    # Apply all transforms (location, rotation, scale)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    disp_mod = cutter_obj.modifiers.new("Inflate_Displace", type='DISPLACE')

    # Push along normals
    disp_mod.direction = 'NORMAL'
    disp_mod.strength = 0.3

    # Apply the modifier so the geometry updates
    bpy.context.view_layer.objects.active = cutter_obj
    bpy.ops.object.modifier_apply(modifier=disp_mod.name)

    bool_mod = main_obj.modifiers.new("Boolean_Cut", "BOOLEAN")
    bool_mod.object = cutter_obj
    bool_mod.operation = 'DIFFERENCE'
    bpy.context.view_layer.objects.active = main_obj
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)

    # === Subtract Cube.001 directly from SolidSurface ===
    main_obj = bpy.data.objects["SolidSurface"]   # base mesh
    tool_obj2 = bpy.data.objects["Cube.001"]       # joined cutter

    bool_mod = main_obj.modifiers.new("Boolean_Subtract_Cube", "BOOLEAN")
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = tool_obj2

    bpy.context.view_layer.objects.active = main_obj
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)

    bpy.data.objects.remove(tool_obj2, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')

    bpy.data.objects.remove(cutter_obj, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    
    tool_obj.location.z += 50

    # Make it active and apply transforms
    bpy.context.view_layer.objects.active = tool_obj
    tool_obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


# Apply modifiers to bands individually (if bands present and model chosen)
if SHOW_BANDS and band_objects:
    if model_choice == "record":
        #do nothing
        print(f"do nothing")
    elif model_choice == "boombox":
        #do nothing
        print(f"do nothing")
    elif model_choice == "none":
        # leave bands alone
        pass

# Apply modifiers to single surface (if single mode)
# --- APPLY MODEL / MODIFIERS TO SINGLE SURFACE ---
if not SHOW_BANDS and single_surface_obj:
    obj = single_surface_obj

    # --- MODEL-SPECIFIC PARAMS ---
    if model_choice == "record":

        origin_offset = recordOffset
        base_thickness = record_base_thickness
        target_single_width = 10
        target_single_length = 30
        target_single_height = 25
        flip_x = True
        flip_y = False
        flip_z = False

    elif model_choice == "boombox":

        origin_offset = boomboxOffset
        target_single_width = 24.44628
        target_single_length = 83.66658
        target_single_height = 35
        flip_x = False
        flip_y = True
        flip_z = True
        base_thickness = boombox_base_thickness

    else:  # "none"
        origin_offset = (0.0, 0.0, 0.0)
        flip_x = flip_y = flip_z = False

    # --- SCALE & POSITION BASED ON TARGETS ---
    coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
    x_min = min(v.x for v in coords)
    x_max = max(v.x for v in coords)
    y_min = min(v.y for v in coords)
    y_max = max(v.y for v in coords)
    z_min = min(v.z for v in coords)
    z_max = max(v.z for v in coords)

    current_width = x_max - x_min
    current_length = y_max - y_min
    current_height = z_max - z_min

    scale_x = target_single_width / current_width if current_width > 0 else 1.0
    scale_y = target_single_length / current_length if current_length > 0 else 1.0
    scale_z = target_single_height / current_height if current_height > 0 else 1.0

    obj.scale = (scale_x, scale_y, scale_z)
    bpy.context.view_layer.update()

    # --- RECORD-SPECIFIC CIRCUMFERENCE SCALING ---
    if model_choice == "record":
        coords_scaled = [obj.matrix_world @ v.co for v in obj.data.vertices]
        x_min_s = min(v.x for v in coords_scaled)
        x_max_s = max(v.x for v in coords_scaled)
        obj_length = x_max_s - x_min_s

        if obj_length > 1e-6:
            desired_radius = 9.0
            circumference = 2 * math.pi * desired_radius
            scale_factor = circumference / obj_length
            obj.scale.x *= scale_factor
            bpy.context.view_layer.update()
            print(f"Applied record circumference scaling: X multiplied by {scale_factor:.4f}")
        else:
            print("Warning: object X length is zero — cannot scale to circumference.")

    # --- TRANSLATE TO ORIGIN OFFSET ---
    coords_final = [obj.matrix_world @ v.co for v in obj.data.vertices]
    new_x_min = min(v.x for v in coords_final)
    new_y_min = min(v.y for v in coords_final)
    new_z_min = min(v.z for v in coords_final)

    obj.location.x += origin_offset[0] - new_x_min
    obj.location.y += origin_offset[1] - new_y_min
    obj.location.z += origin_offset[2] - new_z_min
    bpy.context.view_layer.update()

    # --- FLIP AXES IF NEEDED ---
    mesh = obj.data
    if flip_x:
        for v in mesh.vertices:
            v.co.x *= -1
    if flip_y:
        for v in mesh.vertices:
            v.co.y *= -1
    if flip_z:
        for v in mesh.vertices:
            v.co.z *= -1
    obj.data.update()

    # --- APPLY MODEL MODIFIERS ---
    if model_choice == "record":
        print("Record player model chosen.")
        record_player_obj = import_stl(record_player_path, "RecordPlayer")
        apply_record_modifiers_to_object(obj)
    elif model_choice == "boombox":
        print("Boombox model chosen.")
        boombox_obj = import_stl(boombox_path, "Boombox")
        apply_boombox_modifiers_to_object(obj, target_single_width, target_single_length, target_single_height)
    elif model_choice == "none":
        pass

"""
# --- EXPORT STL ---
    base_path = "D:/453 project/"
    ext = ".stl"

   
    
    
    if SHOW_BANDS:
        
        #code to export 5 files, Mesh_1-Mesh_5 with batch number
        #ex. Bin_1_Batch_1.stl
        #the batch should increment based on the files already present
    
    elif not SHOW_BANDS:
        
        if model_choice == "record":
        
        #joins all meshes together and exports as one mesh
        #ex. Record_Batch_1.stl
        
        elif model_choice == "boombox":
        
        #exports the 2 meshes present
        #ex. Boombox_part_1_batch_1.stl and Boombox_part_2_batch_1.stl
        
        elif model_choice == "none":      
            #exports the mesh as Spectrogram_batch_1.stl
            
            
             counter = 1
    while True:
        filepath = f"{base_path}_{counter}{ext}"
        if not os.path.exists(filepath):
            break
        counter += 1

    # Export STL with unique name
    bpy.ops.wm.stl_export(filepath=filepath, check_existing=True)
    """
    
    # --- SETTINGS ---
if not os.path.exists(f"/mnt/volume_nov"):
    base_path = os.path.join("/Users/deadfloppy/Projects/AdditiveWebsite/main-docker", "tmp", jobId)
else:
    base_path = "/mnt/volume_nov/with-docker/tmp/" + jobId
ext = ".stl"

def get_next_batch_number(pattern):
    """
    Returns the next batch number based on existing files matching the pattern.
    pattern: e.g., "Bin_1_Batch_{}.stl" or "Record_Batch_{}.stl"
    """
    batch = 1
    while True:
        filepath = pattern.format(batch)
        if not os.path.exists(filepath):
            return batch
        batch += 1

# --- EXPORT STL ---
if SHOW_BANDS:
    # Names of the meshes in Blender
    mesh_names = [f"Mesh_{i}" for i in range(1, 6)]

    for i, name in enumerate(mesh_names, start=1):
        obj = bpy.data.objects.get(name)
        if obj is None:
            print(f"[WARNING] Object '{name}' not found — skipping.")
            continue

        # Hide all other objects except this one
        for o in bpy.data.objects:
            o.hide_set(True)
        obj.hide_set(False)

        # Build custom export filename (EQ_Band_i_Batch_j.stl)
        pattern = os.path.join(base_path, f"EQ_Band_{i}_Batch_{{}}{ext}")
        batch = get_next_batch_number(pattern)
        filepath = pattern.format(batch)

        # Export currently visible mesh
        bpy.ops.export_mesh.stl(filepath=filepath, check_existing=True)
        print(f"[EXPORT] Exported {name} as {os.path.basename(filepath)}")

    # Restore visibility after exporting all meshes
    for o in bpy.data.objects:
        o.hide_set(False)

elif not SHOW_BANDS:
    if model_choice == "record":
        pattern = os.path.join(base_path, f"{jobId}{ext}")
        batch = get_next_batch_number(pattern)
        filepath = pattern.format(batch)
        # Join all meshes first if not already joined
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.join()
        bpy.ops.export_mesh.stl(filepath=filepath, check_existing=True)

    elif model_choice == "boombox":
        # === Export Boombox ===
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.data.objects:
            obj.hide_set(True)
        bpy.data.objects['Boombox'].hide_set(False)

        pattern = os.path.join(base_path, f"{jobId}{ext}")
        batch = get_next_batch_number(pattern)
        filepath = pattern.format(batch)

        bpy.ops.export_mesh.stl(filepath=filepath, check_existing=True)
        print(f"[EXPORT] Exported Boombox -> {filepath}")

        # === Export Solid surface ===
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.data.objects:
            obj.hide_set(True)
        bpy.data.objects['SolidSurface'].hide_set(False)

        pattern = os.path.join(base_path, f"{jobId}{ext}")
        batch = get_next_batch_number(pattern)
        filepath = pattern.format(batch)

        bpy.ops.export_mesh.stl(filepath=filepath, check_existing=True)
        print(f"[EXPORT] Exported Solid surface -> {filepath}")

        # === Restore visibility ===
        for obj in bpy.data.objects:
            obj.hide_set(False)
        
    elif model_choice == "none":
        pattern = os.path.join(base_path, f"{jobId}{ext}")
        batch = get_next_batch_number(pattern)
        filepath = pattern.format(batch)
        bpy.ops.export_mesh.stl(filepath=filepath, check_existing=True)
