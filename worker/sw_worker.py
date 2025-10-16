# worker/sw_worker.py
import win32com.client, sys, json
import pythoncom
import time
import os

def analyze_part(file_path):
    """Analyzes a part - ROBUST VERSION"""
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
        
        # Verify file
        print(f"[3] Opening: {file_path}")
        if not os.path.exists(file_path):
            raise Exception(f"File does not exist: {file_path}")
        
        file_size = os.path.getsize(file_path)
        print(f"    File exists, size: {file_size} bytes")
        
        if file_size < 1000:
            raise Exception(f"File too small ({file_size} bytes), likely corrupted")
        
        # Try to open with error handling
        print(f"    Calling OpenDoc...")
        swModel = None
        max_attempts = 2
        
        for attempt in range(max_attempts):
            try:
                swModel = swApp.OpenDoc(str(file_path), 1)
                if swModel:
                    print(f"    OpenDoc succeeded on attempt {attempt + 1}")
                    break
                else:
                    print(f"    OpenDoc returned None on attempt {attempt + 1}")
                    if attempt < max_attempts - 1:
                        time.sleep(1)
            except Exception as e:
                print(f"    OpenDoc exception on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(1)
        
        if not swModel:
            raise Exception(f"Failed to open document after {max_attempts} attempts. "
                          f"File may be corrupted, from incompatible SOLIDWORKS version, or locked by another process.")
        
        print("[4] Document opened successfully")
        
        # Get active document
        swModel = swApp.ActiveDoc
        if not swModel:
            raise Exception("No active document after opening")
        
        print("[5] Got active document")
        
        # Rebuild
        print("[6] Rebuilding...")
        try:
            swModel.ForceRebuild3(True)
            time.sleep(1)
            print("[7] Rebuild complete")
        except Exception as e:
            print(f"    Rebuild warning: {e}")
            print("[7] Continuing despite rebuild issue...")
        
        # CALCULATE VOLUME
        print("[8] Getting mass properties...")
        
        volume_mm3 = 0.0
        
        try:
            # Get the extension
            ext = swModel.Extension
            print("    Got extension")
            
            # GetMassProperties(Accuracy, LowAccuracyAtHighVolumes)
            # Second param should be False, not None
            print("    Calling GetMassProperties(0, False)...")
            props = ext.GetMassProperties(0, False)
            
            if props:
                print(f"    SUCCESS! Got array with {len(props)} elements")
                
                # Dump all values
                for i in range(min(len(props), 10)):  # Show first 10
                    print(f"    props[{i}] = {props[i]}")
                
                # Volume is at index 3
                if len(props) > 3:
                    raw_vol = props[3]
                    print(f"\n    >>> RAW VOLUME = {raw_vol} <<<")
                    
                    volume_mm3 = abs(raw_vol)
                    
                    if volume_mm3 > 0.001:
                        print(f"    >>> SUCCESS: {volume_mm3:.6f} mm^3 <<<")
                        results["status"] = "Success"
                    else:
                        print(f"    WARNING: Volume is zero or very small: {raw_vol}")
                else:
                    print(f"    ERROR: Array too short (len={len(props)})")
                    
            else:
                print("    ERROR: GetMassProperties returned None/empty")
                
        except Exception as e:
            print(f"    ERROR getting mass properties: {e}")
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
