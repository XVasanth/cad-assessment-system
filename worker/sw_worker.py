# worker/sw_worker.py
import win32com.client
import sys
import json

def analyze_part(file_path):
    """
    Opens a SOLIDWORKS part and extracts a detailed signature and mass properties.
    The signature now includes the specific feature name for robust plagiarism detection.
    """
    analysis_results = {
        "status": "Failed",
        "signature": [],
        "volume_mm3": 0.0,
        "surface_area_mm2": 0.0,
        "error": ""
    }
    swApp = None
    swModel = None
    try:
        swApp = win32com.client.Dispatch("SldWorks.Application")
        swModel = swApp.OpenDoc6(file_path, 1, 1, "", 0, 0)
        if not swModel:
            raise Exception("Failed to open document.")

        # 1. Generate a MORE ROBUST Feature Signature
        feature = swModel.FirstFeature()
        while feature:
            # *** KEY CHANGE: Capture the feature's actual name ***
            feature_name = feature.Name
            feature_typename = feature.GetTypeName2()
            
            num_points, num_segments = 0, 0
            sketch = feature.GetSpecificFeature2()
            if sketch and hasattr(sketch, 'GetSketch'):
                sketch = sketch.GetSketch()
                if sketch:
                    points = sketch.GetSketchPoints2()
                    segments = sketch.GetSketchSegments()
                    num_points = len(points) if points else 0
                    num_segments = len(segments) if segments else 0
            
            # Use a dictionary for a clearer signature
            analysis_results["signature"].append({
                "name": feature_name,
                "type": feature_typename,
                "sketch_points": num_points,
                "sketch_segments": num_segments
            })
            feature = feature.GetNextFeature()

        # 2. Get Mass Properties
        mass_props = swModel.Extension.GetMassProperties(1, 0)
        if mass_props:
            analysis_results["volume_mm3"] = mass_props[5] * (1000**3)
            analysis_results["surface_area_mm2"] = mass_props[4] * (1000**2)
        
        analysis_results["status"] = "Success"
        return analysis_results
    
    except Exception as e:
        analysis_results["error"] = str(e)
        return analysis_results

    finally:
        if swModel:
            swApp.CloseDoc(swModel.GetTitle())

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python sw_worker.py <input_file> <output_json>")
        sys.exit(1)
    
    result = analyze_part(sys.argv[1])
    with open(sys.argv[2], 'w') as f:
        json.dump(result, f, indent=4)
