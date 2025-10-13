# worker/sw_worker.py
import win32com.client, sys, json

def analyze_part(file_path):
    analysis_results = { "status": "Failed", "signature": [], "volume_mm3": 0.0, "surface_area_mm2": 0.0, "error": "" }
    swApp, swModel = None, None
    try:
        swApp = win32com.client.Dispatch("SldWorks.Application")
        swModel = swApp.OpenDoc6(file_path, 1, 1, "", 0, 0)
        if not swModel: raise Exception("Failed to open document.")

        feature = swModel.FirstFeature()
        while feature:
            sketch_points, sketch_segments = 0, 0
            sketch = feature.GetSpecificFeature2()
            if sketch and hasattr(sketch, 'GetSketch') and sketch.GetSketch():
                points = sketch.GetSketch().GetSketchPoints2()
                segments = sketch.GetSketch().GetSketchSegments()
                sketch_points = len(points) if points else 0
                sketch_segments = len(segments) if segments else 0
            
            analysis_results["signature"].append({
                "name": feature.Name, "type": feature.GetTypeName2(),
                "sketch_points": sketch_points, "sketch_segments": sketch_segments
            })
            feature = feature.GetNextFeature()

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
        if swModel: swApp.CloseDoc(swModel.GetTitle())

if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(1)
    result = analyze_part(sys.argv[1])
    with open(sys.argv[2], 'w') as f: json.dump(result, f, indent=4)
