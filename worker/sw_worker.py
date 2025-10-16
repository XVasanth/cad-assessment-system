# worker/sw_worker.py
import win32com.client, sys, json
import pythoncom
import time

def analyze_part(file_path):
    """Analyzes a part - SIMPLEST POSSIBLE APPROACH"""
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
        
        # Connect to SOLIDWORKS - use GetActiveObject
        swApp = win32com.client.GetActiveObject("SldWorks.Application")
        print("[1] Connected to SOLIDWORKS")
        
        # Close all
        swApp.CloseAllDocuments(True)
        time.sleep(0.5)
        print("[2] Closed all documents")
        
        # Open - SIMPLEST METHOD
        print(f"[3] Opening: {file_path}")
        
        # Use OpenDoc - this was working before!
        swModel = swApp.OpenDoc(str(file_path), 1)
        
        if not swModel:
            raise Exception("Failed to open document")
        
        print("[4] Document opened")
        
        # Get active document (OpenDoc should make it active)
        swModel = swApp.ActiveDoc
        if not swModel:
            raise Exception("No active document")
        
        print("[5] Got active document")
        
        # Rebuild
        print("[6] Rebuilding...")
        swModel.ForceRebuild3(True)
        time.sleep(1)
        print("[7] Rebuild done")
        
        # CALCULATE VOLUME - ABSOLUTE SIMPLEST
        print("[8] Getting mass properties...")
        
        volume_mm3 = 0.0
        
        try:
            # Get the extension
            ext = swModel.Extension
            print("    Got extension")
            
            # Call GetMassProperties with just one parameter
            # 0 = default accuracy
            print("    Calling GetMassProperties(0)...")
            props = ext.GetMassProperties(0)
            
            if props:
                print(f"    SUCCESS! Got array with {len(props)} elements")
                
                # Dump everything
                for i in range(len(props)):
                    print(f"    props[{i}] = {props[i]}")
                
                # Volume is at index 3
                raw_vol = props[3]
                print(f"\n    >>> RAW VOLUME = {raw_vol} <<<")
                
                # Just use it directly for now
                volume_mm3 = abs(raw_vol)
                
                if volume_mm3 > 0.001:
                    print(f"    >>> SUCCESS: {volume_mm3} mm^3 <<<")
                    results["status"] = "Success"
                else:
                    print(f"    Volume is zero or negative: {raw_vol}")
                    
            else:
                print("    GetMassProperties returned None/empty")
                
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        results["volume_mm3"] = volume_mm3
        print(f"\n[9] FINAL VOLUME: {volume_mm3:.6f} mm^3\n")
        
        if volume_mm3 < 0.001:
            results["error"] = "Volume is 0 or near-0"
        
    except Exception as e:
        results["error"] = str(e)
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Close
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
    print(f"Volume: {result['volume_mm3']:.6f} mm^3")
    print(f"Error: {result.get('error', 'None')}")
