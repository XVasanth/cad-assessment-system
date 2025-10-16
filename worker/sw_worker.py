# worker/sw_worker.py
import win32com.client, sys, json
import pythoncom
import time

def get_gdt_data(swModel):
    """Comprehensive GD&T extraction including DimXpert annotations."""
    gdt_data = {
        "feature_control_frames": [],
        "dimxpert_annotations": [],
        "datums": [],
        "geometric_tolerances": [],
        "combined_signature": []
    }
    return gdt_data  # Simplified for now - focus on volume first

def analyze_part(file_path):
    """Analyzes a part - SIMPLIFIED VERSION FOCUSING ON VOLUME"""
    pythoncom.CoInitialize()
    results = { 
        "status": "Failed", 
        "signature": [], 
        "volume_mm3": 0.0, 
        "gdt_data": {},
        "gdt_callouts": [],
        "error": "" 
    }
    swApp, swModel = None, None
    
    try:
        print(f"\n{'='*70}")
        print(f"ANALYZING: {file_path}")
        print(f"{'='*70}")
        
        swApp = win32com.client.GetActiveObject("SldWorks.Application")
        print("[1] Connected to SOLIDWORKS")
        
        # Close all documents
        swApp.CloseAllDocuments(True)
        time.sleep(0.5)
        print("[2] All documents closed")
        
        # Open the document
        print(f"[3] Opening file...")
        opened_doc = swApp.OpenDoc(str(file_path), 1)
        
        if not opened_doc:
            raise Exception(f"Failed to open: {file_path}")
        
        print("[4] Document opened successfully")
        
        # Get active document
        swModel = swApp.ActiveDoc
        if not swModel:
            raise Exception("Could not get active document")
        
        print(f"[5] Got active document")
        
        # Rebuild
        print("[6] Rebuilding model...")
        swModel.ForceRebuild3(True)
        time.sleep(1.0)  # Give more time to rebuild
        print("[7] Rebuild complete")
        
        # VOLUME CALCULATION - THIS IS THE CRITICAL PART
        print("[8] Calculating volume...")
        
        volume_mm3 = 0.0
        method_used = "None"
        
        # Get document units first
        try:
            unit_sys = swModel.GetUserPreferenceIntegerValue(3)
            print(f"    Unit system: {unit_sys} (0=inches, 1=cm, 2=mm, 3=meters)")
        except Exception as e:
            print(f"    Could not get unit system: {e}")
            unit_sys = 2  # Default to mm
        
        # METHOD 1: GetMassProperties2
        print("    [Method 1] Trying GetMassProperties2...")
        try:
            mass_array = swModel.Extension.GetMassProperties2(0, None, False)
            if mass_array:
                print(f"    Mass array length: {len(mass_array)}")
                if len(mass_array) > 3:
                    raw_vol = mass_array[3]
                    print(f"    Raw volume at index[3]: {raw_vol}")
                    
                    # Convert based on units
                    if unit_sys == 0:  # inches
                        volume_mm3 = raw_vol * (25.4 ** 3)
                        print(f"    Converted from in^3 to mm^3: {volume_mm3}")
                    elif unit_sys == 1:  # cm
                        volume_mm3 = raw_vol * (10 ** 3)
                        print(f"    Converted from cm^3 to mm^3: {volume_mm3}")
                    elif unit_sys == 2:  # mm
                        volume_mm3 = raw_vol
                        print(f"    Already in mm^3: {volume_mm3}")
                    elif unit_sys == 3:  # meters
                        volume_mm3 = raw_vol * (1000 ** 3)
                        print(f"    Converted from m^3 to mm^3: {volume_mm3}")
                    
                    if volume_mm3 > 0.001:  # Must be > 0
                        method_used = "GetMassProperties2"
                        print(f"    *** SUCCESS: Volume = {volume_mm3:.6f} mm^3 ***")
        except Exception as e:
            print(f"    Method 1 error: {e}")
        
        # METHOD 2: CreateMassProperty
        if volume_mm3 < 0.001:
            print("    [Method 2] Trying CreateMassProperty...")
            try:
                mass_prop = swModel.Extension.CreateMassProperty()
                if mass_prop:
                    print("    Created mass property object")
                    mass_prop.UseSystemUnits = False
                    
                    success = mass_prop.Recalculate()
                    print(f"    Recalculate returned: {success}")
                    
                    if success:
                        raw_vol = mass_prop.Volume
                        print(f"    Raw volume: {raw_vol}")
                        
                        # Convert based on units
                        if unit_sys == 0:
                            volume_mm3 = raw_vol * (25.4 ** 3)
                        elif unit_sys == 1:
                            volume_mm3 = raw_vol * (10 ** 3)
                        elif unit_sys == 2:
                            volume_mm3 = raw_vol
                        elif unit_sys == 3:
                            volume_mm3 = raw_vol * (1000 ** 3)
                        
                        if volume_mm3 > 0.001:
                            method_used = "CreateMassProperty"
                            print(f"    *** SUCCESS: Volume = {volume_mm3:.6f} mm^3 ***")
            except Exception as e:
                print(f"    Method 2 error: {e}")
        
        # METHOD 3: GetMassProperties (legacy)
        if volume_mm3 < 0.001:
            print("    [Method 3] Trying GetMassProperties (legacy)...")
            try:
                # Try with accuracy 0
                mass_array = swModel.Extension.GetMassProperties(0, None)
                if mass_array and len(mass_array) > 3:
                    raw_vol = mass_array[3]
                    print(f"    Raw volume at [3]: {raw_vol}")
                    
                    if unit_sys == 0:
                        volume_mm3 = raw_vol * (25.4 ** 3)
                    elif unit_sys == 1:
                        volume_mm3 = raw_vol * (10 ** 3)
                    elif unit_sys == 2:
                        volume_mm3 = raw_vol
                    elif unit_sys == 3:
                        volume_mm3 = raw_vol * (1000 ** 3)
                    
                    if volume_mm3 > 0.001:
                        method_used = "GetMassProperties"
                        print(f"    *** SUCCESS: Volume = {volume_mm3:.6f} mm^3 ***")
            except Exception as e:
                print(f"    Method 3 error: {e}")
        
        results["volume_mm3"] = volume_mm3
        print(f"\n[9] *** FINAL VOLUME: {volume_mm3:.6f} mm^3 ***")
        print(f"[9] *** METHOD USED: {method_used} ***\n")
        
        if volume_mm3 < 0.001:
            print("    [WARNING] Volume is essentially ZERO!")
            results["error"] = "Volume calculation returned 0 or near-0"
        else:
            results["status"] = "Success"
            print("[10] Analysis COMPLETE - Volume calculated successfully!")
        
        # Add minimal feature signature (just count)
        results["signature"] = [{"name": "DummyFeature", "type": "Feature"}]  # Placeholder
        
        # GD&T Data (simplified)
        gdt_data = get_gdt_data(swModel)
        results["gdt_data"] = gdt_data
        results["gdt_callouts"] = gdt_data["combined_signature"]
        
    except Exception as e:
        error_msg = str(e)
        results["error"] = error_msg
        print(f"\n[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        
    finally:
        if swModel:
            try:
                doc_title = swModel.GetTitle
                swApp.CloseDoc(doc_title)
                print("[11] Document closed")
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
    print(f"Output written to: {sys.argv[2]}")
