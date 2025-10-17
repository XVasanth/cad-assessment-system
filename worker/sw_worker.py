# worker/sw_worker.py
import win32com.client, sys, json
import pythoncom
import time
import os

def analyze_part(file_path):
    """Analyzes a part - WORKING VERSION WITH CORRECT UNITS"""
    pythoncom.CoInitialize()
    results = { 
        "status": "Failed", 
        "signature": [{"name": "Feature1", "type": "Boss"}],
        "volume_mm3": 0.0, 
        "gdt_data": {"combined_signature": []},
        "gdt_callouts": [],
        "error": "" 
    }
    swApp = None
    
    try:
        print(f"\n{'='*70}")
        print(f"ANALYZING: {file_path}")
        print(f"{'='*70}")
        
        # Connect to SOLIDWORKS
        swApp = win32com.client.GetActiveObject("SldWorks.Application")
        print("[1] Connected to SOLIDWORKS")
        
        # Close all
        swApp.CloseAllDocuments(True)
        time.sleep(0.5)
        print("[2] Closed all documents")
        
        # Open file
        print(f"[3] Opening file...")
        swModel = swApp.OpenDoc(str(file_path), 1)
        
        if not swModel:
            raise Exception(f"Failed to open document")
        
        print("[4] Document opened")
        
        # Ensure it's active
        swModel = swApp.ActiveDoc
        print("[5] Got active document")
        
        # Rebuild
        print("[6] Rebuilding...")
        swModel.ForceRebuild3(True)
        time.sleep(1.0)
        print("[7] Rebuild complete")
        
        # GET VOLUME VIA BODIES
        print("[8] Getting volume from bodies...")
        
        volume_mm3 = 0.0
        
        # Get all solid bodies
        print("    Getting solid bodies...")
        body_array = swModel.GetBodies2(0, False)  # Get all solid bodies
        
        if body_array and len(body_array) > 0:
            print(f"    Found {len(body_array)} solid body/bodies")
            
            total_volume = 0.0
            for idx in range(len(body_array)):
                body = body_array[idx]
                print(f"    Processing body {idx + 1}...")
                
                try:
                    # Get mass properties for this body
                    body_props = body.GetMassProperties(0.0)
                    
                    if body_props and len(body_props) >= 4:
                        # CRITICAL FIX: Volume is returned in cubic METERS
                        # Convert to cubic millimeters: 1 m³ = 1,000,000,000 mm³
                        body_volume_mm3 = body_props[3] * 1e9
                        print(f"      Body {idx + 1} volume: {body_volume_mm3:.2f} mm^3")
                        total_volume += abs(body_volume_mm3)
                    else:
                        print(f"      Body {idx + 1}: Could not get properties")
                        
                except Exception as e:
                    print(f"      Body {idx + 1} error: {e}")
            
            volume_mm3 = total_volume
            print(f"\n    >>> TOTAL VOLUME: {volume_mm3:.2f} mm^3 <<<")
            
            if volume_mm3 > 1.0:  # Threshold: 1 mm³
                results["status"] = "Success"
                print("    >>> SUCCESS! <<<")
            else:
                print("    WARNING: Volume below threshold")
                results["error"] = "Volume below 1 mm3 threshold"
        else:
            print("    ERROR: No solid bodies found in part")
            results["error"] = "No solid bodies found"
        
        results["volume_mm3"] = volume_mm3
        print(f"\n[9] FINAL VOLUME: {volume_mm3:.2f} mm^3\n")
        
    except Exception as e:
        results["error"] = str(e)
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if swApp:
            try:
                swApp.CloseAllDocuments(True)
                print("[10] Closed documents")
            except:
                pass
        pythoncom.CoUninitialize()
    
    print(f"{'='*70}\n")
    return results

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: sw_worker.py <input_file> <output_json>")
        sys.exit(1)
    
    result = analyze_part(sys.argv[1])
    
    with open(sys.argv[2], 'w') as f:
        json.dump(result, f, indent=4)
    
    print(f"\n*** RESULTS SUMMARY ***")
    print(f"Status: {result['status']}")
    print(f"Volume: {result['volume_mm3']:.2f} mm^3")
    print(f"Error: {result.get('error', 'None')}")
