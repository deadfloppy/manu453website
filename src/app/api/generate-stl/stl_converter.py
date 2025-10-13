"""
STL to GLB and USDZ converter
Converts 3D STL files to AR-compatible formats in one pass
"""

import trimesh
import sys
import os
import platform
from pathlib import Path

jobid = sys.argv[1]
stl_path = f"/mnt/volume_nov/with-docker/public{jobid}"
print(f"path: {stl_path}")
def convert_stl_to_glb(stl_path, glb_path):
    """Convert STL to GLB format"""
    try:
        print(f"Loading STL file: {stl_path}")
        mesh = trimesh.load(stl_path)
        
        # Center the mesh
        mesh.vertices -= mesh.centroid
        
        print(f"Converting to GLB: {glb_path}")
        mesh.export(glb_path, file_type='glb')
        
        print(f"[OK] Successfully converted to GLB: {glb_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error converting to GLB: {e}")
        return False

def convert_stl_to_usdz(stl_path, usdz_path):
    """Convert STL to USDZ using USD Python API"""
    try:
        from pxr import Usd, UsdGeom, UsdUtils, Gf, Sdf
        
        print(f"Loading STL for USDZ conversion: {stl_path}")
        
        # Load STL mesh
        mesh = trimesh.load(stl_path)
        if not isinstance(mesh, trimesh.Trimesh):
            raise ValueError("STL file must contain a single mesh")
        
        # Center the mesh
        mesh.vertices -= mesh.centroid
        
        print(f"Creating USD stage for USDZ...")
        
        # Create temporary USD file
        temp_usda = str(Path(usdz_path).with_suffix('.usda'))
        stage = Usd.Stage.CreateNew(temp_usda)
        
        # Set up root prim
        root_prim = stage.DefinePrim("/Model", "Xform")
        stage.SetDefaultPrim(root_prim)
        
        # Define mesh
        mesh_prim = UsdGeom.Mesh.Define(stage, "/Model/Mesh")
        
        # Convert vertices
        points = [Gf.Vec3f(float(v[0]), float(v[1]), float(v[2])) for v in mesh.vertices]
        mesh_prim.CreatePointsAttr(points)
        
        # Set face data
        face_vertex_counts = [3] * len(mesh.faces)
        mesh_prim.CreateFaceVertexCountsAttr(face_vertex_counts)
        
        face_vertex_indices = [int(idx) for face in mesh.faces for idx in face]
        mesh_prim.CreateFaceVertexIndicesAttr(face_vertex_indices)
        
        # Save USD file
        stage.GetRootLayer().Save()
        
        # Package into USDZ
        print(f"Creating USDZ package: {usdz_path}")
        success = UsdUtils.CreateNewUsdzPackage(temp_usda, usdz_path)
        
        # Clean up temporary file
        if os.path.exists(temp_usda):
            os.remove(temp_usda)
        
        if success and os.path.exists(usdz_path):
            print(f"[OK] Successfully converted to USDZ: {usdz_path}")
            return True
        else:
            print(f"[ERROR] Failed to create USDZ package")
            return False
            
    except ImportError as e:
        print(f"[WARNING] USD Python API not available: {e}")
        print("Install with: pip install usd-core")
        print("USDZ conversion skipped - iOS AR Quick Look will not work")
        return False
    except Exception as e:
        print(f"[ERROR] USDZ conversion failed: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_models.py <stl_file_path>")
        print("Example: python convert_models.py /path/to/model.stl")
        sys.exit(1)
    
    stl_path = sys.argv[1]
    
    # Validate input file
    if not os.path.exists(stl_path):
        print(f"[ERROR] STL file not found: {stl_path}")
        sys.exit(1)
    
    if not stl_path.lower().endswith('.stl'):
        print(f"[ERROR] Input file must be an STL file")
        sys.exit(1)
    
    print("="*60)
    print("STL to AR Format Converter")
    print("="*60)
    print(f"Input file: {stl_path}")
    print(f"Platform: {platform.system()}")
    print("-"*60)
    
    # Generate output paths
    base_path = Path(stl_path).with_suffix('')
    glb_path = str(base_path) + '.glb'
    usdz_path = str(base_path) + '.usdz'
    
    success_count = 0
    total_conversions = 2
    
    # Convert to GLB (always works)
    print("\n[1/2] Converting to GLB...")
    if convert_stl_to_glb(stl_path, glb_path):
        success_count += 1
    else:
        print("GLB conversion failed")
    
    # Convert to USDZ (may not work on all platforms)
    print("\n[2/2] Converting to USDZ...")
    if convert_stl_to_usdz(stl_path, usdz_path):
        success_count += 1
    else:
        print("USDZ conversion failed or skipped")
        total_conversions = 1  # Adjust if USDZ not supported
    
    print("="*60)
    print(f"Conversion complete: {success_count}/{total_conversions} formats")
    
    if success_count > 0:
        print("\nGenerated files:")
        if os.path.exists(glb_path):
            print(f"  - GLB (Android AR + viewer): {glb_path}")
        if os.path.exists(usdz_path):
            print(f"  - USDZ (iOS AR Quick Look): {usdz_path}")
    
    print("="*60)
    
    # Exit with success if at least GLB was created
    sys.exit(0 if success_count > 0 else 1)

if __name__ == "__main__":
    main()
