# worker/sw_worker.py
import win32com.client, sys, json
import pythoncom

def get_gdt_data(swModel):
    """
    Comprehensive GD&T extraction including DimXpert annotations.
    Returns a dictionary with detailed GD&T information.
    """
    gdt_data = {
        "feature_control_frames": [],
        "dimxpert_annotations": [],
        "datums": [],
        "geometric_tolerances": []
    }
    
    try:
        # Method 1: Traditional Feature Control Frames from Annotations
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
                                
                                # Type 30 = Feature Control Frame
                                if ann_type == 30:
                                    try:
                                        full_text = swAnn.GetText(0).replace('\n', ' ').strip()
                                        if full_text:
                                            gdt_data["feature_control_frames"].append(full_text)
                                    except:
                                        pass
                                
                                # Type 23 = Datum Feature Symbol
                                elif ann_type == 23:
                                    try:
                                        datum_text = swAnn.GetText(0).strip()
                                        if datum_text:
                                            gdt_data["datums"].append(datum_text)
                                    except:
                                        pass
                    except:
                        continue
        
        # Method 2: DimXpert Manager - Captures auto-generated GD&T
        try:
            dimXpertMgr = swModel.Extension.GetDimXpertManager()
            if dimXpertMgr:
                # Get all DimXpert annotations
                dimxpert_anns = dimXpertMgr.GetAllDimXpertAnnotations()
                if dimxpert_anns:
                    for ann in dimxpert_anns:
                        try:
                            # Try to get annotation details
                            ann_name = ann.GetName() if hasattr(ann, 'GetName') else str(ann)
                            gdt_data["dimxpert_annotations"].append(ann_name)
                        except:
                            pass
                
                # Get tolerances directly
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
        
        # Method 3: Feature-level tolerance extraction
        try:
            feature = swModel.FirstFeature()
            while feature:
                # Check if feature has tolerance data
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
    
    # Clean up and deduplicate
    gdt_data["feature_control_frames"] = sorted(list(set(gdt_data["feature_control_frames"])))
    gdt_data["dimxpert_annotations"] = sorted(list(set(gdt_data["dimxpert_annotations"])))
    gdt_data["datums"] = sorted(list(set(gdt_data["datums"])))
    gdt_data["geometric_tolerances"] = sorted(list(set(gdt_data["geometric_tolerances"])))
    
    # Create a combined signature for easy comparison
    all_gdt = (gdt_data["feature_control_frames"] + 
               gdt_data["dimxpert_annotations"] + 
               gdt_data["datums"] + 
               gdt_data["geometric_tolerances"])
    gdt_data["combined_signature"] = sorted(list(set(all_gdt)))
    
    return gdt_data

def analyze_part(file_path):
    """
    Analyzes a part using a robust protocol to ensure accurate measurement.
    """
    pythoncom.CoInitialize()
    results = { 
        "status": "Failed", 
        "signature": [], 
        "volume_mm3": 0.0, 
        "gdt_data": {},
        "gdt_callouts": [],  # Keep for backward compatibility
        "error": "" 
    }
    swApp, swModel = None, None
    try:
        swApp = win32com.client.GetActiveObject("SldWorks.Application")
        
        # 1. WIPE THE SLATE
        swApp.CloseAllDocuments(True)
        
        # 2. OPEN THE TARGET DOCUMENT
        opened_doc = swApp.OpenDoc6(file_path, 1, 0, "", 0, 0)
        if not opened_doc: 
            raise Exception(f"Failed to open document: {file_path}")

        # 3. EXPLICITLY GET THE ACTIVE DOCUMENT
        swModel = swApp.ActiveDoc
        if not swModel: 
            raise Exception("Could not get a handle on the active document.")

        # 4. FORCE A FULL REBUILD (CRITICAL STEP)
        swModel.ForceRebuild3(True)
        swModel.ViewZoomtofit2()
        
        # --- ANALYSIS NOW PROCEEDS ON THE CORRECT, REBUILT MODEL ---

        # 5A. Feature Signature
        feature = swModel.FirstFeature()
        while feature:
            results["signature"].append({"name": feature.Name, "type": feature.GetTypeName2()})
            feature = feature.GetNextFeature()

        # 5B. Mass Properties - FIXED VERSION
        swModel.Extension.SetUserPreferenceInteger(3, 0, 4)  # Set to millimeters
        mass_props = swModel.Extension.CreateMassProperty()
        
        if mass_props:
            mass_props.UseSystemUnits = False
            success = mass_props.Recalculate()
            
            if success:
                volume_cubic_mm = mass_props.Volume
                unit_system = swModel.GetUserPreferenceIntegerValue(3)
                
                if unit_system == 0:  # IPS (inches)
                    volume_cubic_mm = volume_cubic_mm * (25.4 ** 3)
                elif unit_system == 1:  # CGS (cm)
                    volume_cubic_mm = volume_cubic_mm * (10 ** 3)
                elif unit_system == 2:  # MMGS (mm)
                    volume_cubic_mm = volume_cubic_mm
                elif unit_system == 3:  # MKS (meters)
                    volume_cubic_mm = volume_cubic_mm * (1000 ** 3)
                
                results["volume_mm3"] = volume_cubic_mm
                print(f"DEBUG: Volume calculated: {volume_cubic_mm:.2f} mm³")
        
        # 5C. GD&T Data - COMPREHENSIVE EXTRACTION
        gdt_data = get_gdt_data(swModel)
        results["gdt_data"] = gdt_data
        results["gdt_callouts"] = gdt_data["combined_signature"]  # Backward compatibility
        
        print(f"DEBUG: GD&T extracted:")
        print(f"  - Feature Control Frames: {len(gdt_data['feature_control_frames'])}")
        print(f"  - DimXpert Annotations: {len(gdt_data['dimxpert_annotations'])}")
        print(f"  - Datums: {len(gdt_data['datums'])}")
        print(f"  - Total GD&T items: {len(gdt_data['combined_signature'])}")
        
        results["status"] = "Success"
        
    except Exception as e:
        results["error"] = str(e)
        print(f"ERROR: {str(e)}")
    finally:
        if swModel: 
            swApp.CloseDoc(swModel.GetTitle())
        pythoncom.CoUninitialize()
        
    return results

if __name__ == "__main__":
    if len(sys.argv) != 3: 
        print("Usage: sw_worker.py <input_file> <output_json>")
        sys.exit(1)
    result = analyze_part(sys.argv[1])
    with open(sys.argv[2], 'w') as f: 
        json.dump(result, f, indent=4)
    print(f"Analysis complete. Results written to {sys.argv[2]}")
