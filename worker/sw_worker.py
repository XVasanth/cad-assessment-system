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
        "geometric_tolerances": []
    }
    
    try:
        swAnnManager = swModel.Extension.GetAnnotationManager()
        if swAnnManager:
            swAnnViews = swAnnManager.GetAnnotationViews()
            if swAnnViews:
                for view in swAnnViews:
                    try:
                        view.Activate()
                        annotations = view.GetAnnotations()
                        if annotations:
                            for swAnn in annotations:
                                ann_type = swAnn.GetType()
                                if ann_type == 30:
                                    try:
                                        full_text = swAnn.GetText(0).replace('\n', ' ').strip()
                                        if full_text:
                                            gdt_data["feature_control_frames"].append(full_text)
                                    except:
                                        pass
                                elif ann_type == 23:
                                    try:
                                        datum_text = swAnn.GetText(0).strip()
                                        if datum_text:
                                            gdt_data["datums"].append(datum_text)
                                    except:
                                        pass
                    except:
                        continue
        
        try:
            dimXpertMgr = swModel.Extension.GetDimXpertManager()
            if dimXpertMgr:
                dimxpert_anns = dimXpertMgr.GetAllDimXpertAnnotations()
                if dimxpert_anns:
                    for ann in dimxpert_anns:
                        try:
                            ann_name = ann.GetName() if hasattr(ann, 'GetName') else str(ann)
                            gdt_data["dimxpert_annotations"].append(ann_name)
                        except:
                            pass
                
                tolerances = dimXpertMgr.GetAllTolerances()
                if tolerances:
                    for tol in tolerances:
                        try:
                            tol_type = tol.GetType() if hasattr(tol, 'GetType') else "unknown"
                            gdt_data["geometric_tolerances"].append(str(tol_type))
                        except:
                            pass
        except Exception as e:
            print(f"DimXpert extraction note: {str(e)}")
        
        try:
            feature = swModel.FirstFeature()
            while feature:
                feat_type = feature.GetTypeName2()
                if "Reference" in feat_type or "Dimension" in feat_type or "Tolerance" in feat_type:
                    try:
                        feat_data = feature.GetSpecificFeature2()
                        if feat_data:
                            gdt_data["geometric_tolerances"].append(f"{feature.Name}:{feat_type}")
                    except:
                        pass
                feature = feature.GetNextFeature()
        except:
            pass
            
    except Exception as e:
        print(f"GD&T extraction error: {str(e)}")
    
    gdt_data["feature_control_frames"] = sorted(list(set(gdt_data["feature_control_frames"])))
    gdt_data["dimxpert_annotations"] = sorted(list(set(gdt_data["dimxpert_annotations"])))
    gdt_data["datums"] = sorted(list(set(gdt_data["datums"])))
    gdt_data["geometric_tolerances"] = sorted(list(set(gdt_data["geometric_tolerances"])))
    
    all_gdt = (gdt_data["feature_control_frames"] + 
               gdt_data["dimxpert_annotations"] + 
               gdt_data["datums"] + 
               gdt_data["geometric_tolerances"])
    gdt_data["combined_signature"] = sorted(list(set(all_gdt)))
    
    return gdt_data

def analyze_part(file_path):
    """Analyzes a part using a robust protocol to ensure accurate measurement."""
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
        errors = 0
        warnings = 0
        opened_doc = swApp.OpenDoc6(file_path, 1, 0, "", errors, warnings)
        
        if not opened_doc:
            raise Exception(f"Failed to open: {file_path}")
        
        print("[3] Document opened successfully")
        
        # Get active document
        swModel = swApp.ActiveDoc
        if not swModel:
            raise Exception("Could not get active document")
        
        print(f"[4] Active document: {swModel.GetTitle()}")
        
        # Rebuild
        print("[5] Rebuilding model...")
        swModel.ForceRebuild3(True)
        time.sleep(0.5)  # Give it time to rebuild
        print("[6] Rebuild complete")
        
        # Feature signature
        print("[7] Extracting features...")
        feature = swModel.FirstFeature()
        feature_count = 0
        while feature:
            results["signature"].append({"name": feature.Name, "type": feature.GetTypeName2()})
            feature = feature.GetNextFeature()
            feature_count += 1
        print(f"[8] Found {feature_count} features")
        
        # Volume calculation - TRY MULTIPLE METHODS
        print("[9] Calculating volume using multiple methods...")
        
        volume_mm3 = 0.0
        method_used = "None"
        
        # METHOD 1: GetMassProperties2
        try:
            print("    Trying GetMassProperties2...")
            mass_array = swModel.Extension.GetMassProperties2(0, None, False)
            if mass_array and len(mass_array) > 3:
                raw_vol = mass_array[3]
                unit_sys = swModel.GetUserPreferenceIntegerValue(3)
                
                print(f"    Raw volume: {raw_vol}")
                print(f"    Unit system: {unit_sys} (0=in, 1=cm, 2=mm, 3=m)")
                
                if unit_sys == 0:  # inches
                    volume_mm3 = raw_vol * (25.4 ** 3)
                elif unit_sys == 1:  # cm
                    volume_mm3 = raw_vol * (10 ** 3)
                elif unit_sys == 2:  # mm
                    volume_mm3 = raw_vol
                elif unit_sys == 3:  # meters
                    volume_mm3 = raw_vol * (1000 ** 3)
                else:
                    volume_mm3 = raw_vol
                
                if volume_mm3 > 0:
                    method_used = "GetMassProperties2"
                    print(f"    SUCCESS: Volume = {volume_mm3:.6f} mm^3")
        except Exception as e:
            print(f"    Method 1 failed: {e}")
        
        # METHOD 2: CreateMassProperty (if method 1 failed)
        if volume_mm3 == 0:
            try:
                print("    Trying CreateMassProperty...")
                mass_prop = swModel.Extension.CreateMassProperty()
                if mass_prop:
                    mass_prop.UseSystemUnits = False
                    if mass_prop.Recalculate():
                        raw_vol = mass_prop.Volume
                        unit_sys = swModel.GetUserPreferenceIntegerValue(3)
                        
                        print(f"    Raw volume: {raw_vol}")
                        print(f"    Unit system: {unit_sys}")
                        
                        if unit_sys == 0:
                            volume_mm3 = raw_vol * (25.4 ** 3)
                        elif unit_sys == 1:
                            volume_mm3 = raw_vol * (10 ** 3)
                        elif unit_sys == 2:
                            volume_mm3 = raw_vol
                        elif unit_sys == 3:
                            volume_mm3 = raw_vol * (1000 ** 3)
                        else:
                            volume_mm3 = raw_vol
                        
                        if volume_mm3 > 0:
                            method_used = "CreateMassProperty"
                            print(f"    SUCCESS: Volume = {volume_mm3:.6f} mm^3")
            except Exception as e:
                print(f"    Method 2 failed: {e}")
        
        # METHOD 3: GetMassProperties (legacy, if others failed)
        if volume_mm3 == 0:
            try:
                print("    Trying GetMassProperties (legacy)...")
                mass_array = swModel.Extension.GetMassProperties(1, 0)
                if mass_array and len(mass_array) > 5:
                    raw_vol = mass_array[3]  # Try index 3
                    unit_sys = swModel.GetUserPreferenceIntegerValue(3)
                    
                    print(f"    Raw volume at [3]: {raw_vol}")
                    
                    if unit_sys == 0:
                        volume_mm3 = raw_vol * (25.4 ** 3)
                    elif unit_sys == 1:
                        volume_mm3 = raw_vol * (10 ** 3)
                    elif unit_sys == 2:
                        volume_mm3 = raw_vol
                    elif unit_sys == 3:
                        volume_mm3 = raw_vol * (1000 ** 3)
                    else:
                        volume_mm3 = raw_vol
                    
                    if volume_mm3 > 0:
                        method_used = "GetMassProperties[3]"
                        print(f"    SUCCESS: Volume = {volume_mm3:.6f} mm^3")
            except Exception as e:
                print(f"    Method 3 failed: {e}")
        
        results["volume_mm3"] = volume_mm3
        print(f"[10] FINAL VOLUME: {volume_mm3:.6f} mm^3 (method: {method_used})")
        
        if volume_mm3 == 0:
            print("    WARNING: Volume is ZERO! This is likely incorrect.")
            results["error"] = "Volume calculation returned 0"
        
        # GD&T Data
        print("[11] Extracting GD&T data...")
        gdt_data = get_gdt_data(swModel)
        results["gdt_data"] = gdt_data
        results["gdt_callouts"] = gdt_data["combined_signature"]
        print(f"[12] GD&T items found: {len(gdt_data['combined_signature'])}")
        
        results["status"] = "Success"
        print("[13] Analysis COMPLETE")
        
    except Exception as e:
        error_msg = str(e)
        results["error"] = error_msg
        print(f"\n[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        
    finally:
        if swModel:
            try:
                swApp.CloseDoc(swModel.GetTitle())
                print("[14] Document closed")
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
    print(f"Features: {len(result['signature'])}")
    print(f"GD&T items: {len(result.get('gdt_callouts', []))}")
    print(f"Error: {result.get('error', 'None')}")
    print(f"Output written to: {sys.argv[2]}")
