# worker/sw_worker.py
import win32com.client
import sys
import json

def generate_signature(file_path):
    """
    Opens a SOLIDWORKS part and generates a detailed feature signature.
    The signature is a list of tuples: (FeatureTypeName, NumSketchPoints, NumSketchSegments).
    """
    signature = []
    swApp = None
    swModel = None
    try:
        swApp = win32com.client.Dispatch("SldWorks.Application")
        swModel = swApp.OpenDoc6(file_path, 1, 1, "", 0, 0)
        if not swModel:
            raise Exception("Failed to open document.")

        feature = swModel.FirstFeature()
        while feature:
            feature_typename = feature.GetTypeName2()
            
            # Get sketch info if the feature has a sketch
            num_points, num_segments = 0, 0
            sketch = feature.GetSpecificFeature2()
            if sketch and hasattr(sketch, 'GetSketch'):
                sketch = sketch.GetSketch()
                if sketch:
                    points = sketch.GetSketchPoints2()
                    segments = sketch.GetSketchSegments()
                    num_points = len(points) if points else 0
                    num_segments = len(segments) if segments else 0
            
            # Add a tuple representing this feature to the signature
            signature.append((feature_typename, num_points, num_segments))
            
            feature = feature.GetNextFeature()

        return {"status": "Success", "signature": signature, "error": ""}
    
    except Exception as e:
        return {"status": "Failed", "signature": [], "error": str(e)}

    finally:
        if swModel:
            swApp.CloseDoc(swModel.GetTitle())

if __name__ == "__main__":
    # Expects 2 arguments: input file path and output json path
    if len(sys.argv) != 3:
        print("Usage: python sw_worker.py <input_file> <output_json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_json = sys.argv[2]
    
    result = generate_signature(input_file)
    
    with open(output_json, 'w') as f:
        json.dump(result, f, indent=4)
