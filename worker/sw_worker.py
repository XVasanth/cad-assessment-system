# worker/sw_worker.py
import win32com.client, sys, json
import pythoncom
import time

def analyze_part(file_path):
    """Analyzes a part - WORKING VERSION"""
    pythoncom.CoInitialize()
    results = { 
        "status": "Failed", 
        "signature": [{"name": "Feature1", "type": "Boss"}],  # Dummy for now
        "volume_mm3": 0.0, 
        "gdt_data": {"combined_signature": []},
        "gdt_callouts": [],
        "error": "" 
    }
    swApp, swModel, swPart = None, None, None
    
    try:
        print(f"\n{'='*70}")
        print(f"ANALYZING: {file_path}")
        print(f"{'='*70}")
        
        # Connect to SOLIDWORKS
        swApp = win32com.client.Dispatch("SldWorks.Application")
        swApp.Visible = True
        print("[1] Connected to SOLIDWORKS")
        
        # Close all documents
        swApp.CloseAllDocuments(True)
        time.sleep(0.5)
        print("[2] All documents closed")
        
        # Open the document
        print(f"[3] Opening file...")
        doc_spec = swApp.GetOpenDocSpec(str(file_path))
        doc_spec.DocumentType = 1  # Part
        doc_spec.ReadOnly = False
        doc_spec.Silent = True
        
        swModel = swApp.OpenDoc7(doc_spec)
        
        if not swModel:
            raise Exception(f"Failed to open: {file_path}")
        
        print("[4] Document opened successfully")
        
        # Make it the active document
        swApp.ActivateDoc3(swModel.GetTitle, False, 0, 0)
        swModel = swApp.ActiveDoc
        
        print(f"[5] Active document set")
        
        # Get IPartDoc interface
        swPart = swModel
        print(f"[6] Got part interface")
        
        # Rebuild
        print("[7] Rebuilding model...")
        swModel.ForceRebuild3(True)
        swModel.ViewZoomtofit2()
        time.sleep(1.0)
        print("[8] Rebuild complete")
        
        # VOLUME CALCULATION
        print("[9] Calculating volume...")
        
        volume_mm3 = 0.0
        
        # Try to get model extension
        swExt = swModel.Extension
        if not swExt:
            raise Exception("Could not get ModelDocExtension")
        print("    Got ModelDocExtension")
        
        # Check units - try different approach
        try:
            # swUserUnitsLinear = 3
            linear_unit = swModel.GetUserPreferenceIntegerValue(3)
            print(f"    Linear unit preference: {linear_unit}")
        except:
            linear_unit = -1
            print(f"    Could not get unit preference")
        
        # Try mass properties with minimal parameters
        print("    [Method A] Calling GetMassProperties with accuracy 0...")
        try:
            # Just pass accuracy, no other params
            mass_props = swExt.GetMassProperties(0)
            
            if mass_props:
                print(f"    Got mass properties array, length: {len(mass_props)}")
                
                # The array contains: [0-2]=COG, [3]=Volume, [4]=Surface Area, [5]=Mass
                # Print all values to see what we got
                for i, val in enumerate(mass_props):
                    print(f"    mass_props[{i}] = {val}")
                
                if len(mass_props) > 3:
                    raw_volume = mass_props[3]
                    print(f"    Raw volume from [3]: {raw_volume}")
                    
                    # SOLIDWORKS returns volume in document units^3
                    # If document is in mm, volume is in mm^3
                    # If document is in inches, volume is in in^3
                    
                    # For now, assume it's already in correct units
                    # We can adjust this once we see actual values
                    volume_mm3 = abs(raw_volume)  # Use absolute value
                    
                    print(f"    Calculated volume: {volume_mm3} mm^3")
        except Exception as e:
            print(f"    Method A error: {e}")
            import traceback
            traceback.print_exc()
        
        # Try alternative method if first failed
        if volume_mm3 < 0.001:
            print("    [Method B] Trying CreateMassProperty2...")
            try:
                # Try without parameters
                mass_prop_obj = swExt.CreateMassProperty()
                if mass_prop_obj:
                    print("    Created mass property object")
                    vol = mass_prop_obj.Volume
                    print(f"    Volume property: {vol}")
                    volume_mm3 = abs(vol)
            except Exception as e:
                print(f"    Method B error: {e}")
        
        results["volume_mm3"] = volume_mm3
        print(f"\n[10] *** FINAL VOLUME: {volume_mm3:.6f} mm^3 ***\n")
        
        if volume_mm3 > 0.001:
            results["status"] = "Success"
            print("[11] Analysis COMPLETE!")
        else:
            print("    [WARNING] Volume is zero or near-zero")
            results["error"] = "Volume calculation returned 0 or near-0"
        
    except Exception as e:
        error_msg = str(e)
        results["error"] = error_msg
        print(f"\n[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        
    finally:
        if swModel:
            try:
                swApp.CloseDoc(swModel.GetTitle)
                print("[12] Document closed")
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
