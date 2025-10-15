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
        "gdt_callouts": [],
        "error": "" 
    }
    swApp, swModel = None, None
    
    try:
        swApp = win32com.client.GetActiveObject("SldWorks.Application")
        
        print(f"\n{'='*60}")
        print(f"ANALYZING FILE: {file_path}")
        print(f"{'='*60}")
        
        # 1. Close all documents
        swApp.CloseAllDocuments(True)
        
        # 2. Open the target document
        # swOpenDocOptions: 0=silent, 1=read-only
        errors = 0
        warnings = 0
        opened_doc = swApp.OpenDoc6(file_path, 1, 0, "", errors, warnings)
        
        if not opened_doc:
            raise Exception(f"Failed to open document: {file_path}")
        
        print(f"Document opened successfully")
        
        # 3. Get active document handle
        swModel = swApp.ActiveDoc
        if not swModel:
            raise Exception("Could not get active document handle")
        
        # 4. Force rebuild
        print("Forcing rebuild...")
        swModel.ForceRebuild3(True)
        swModel.ViewZoomtofit2()
        print("Rebuild complete")
        
        # 5A. Feature Signature
        print("Extracting feature signature...")
        feature = swModel.FirstFeature()
        feature_count = 0
        while feature:
            results["signature"].append({"name": feature.Name, "type": feature.GetTypeName2()})
            feature = feature.GetNextFeature()
            feature_count += 1
        print(f"Found {feature_count} features")
        
        # 5B. Volume Calculation - FIXED APPROACH
        print("Calculating volume...")
        
        # Get mass properties - returns array with volume at index 3
        # Parameters: (accuracy: 0=default)
        mass_props_array = swModel.Extension.GetMassProperties2(0, None, False)
        
        if mass_props_array and len(mass_props_array) > 3:
            # Index 3 contains the volume in document units CUBED
            raw_volume = mass_props_array[3]
            
            # Get the document's unit system
            # 0=IPS (inches), 1=CGS (cm), 2=MMGS (mm), 3=MKS (meters)
            unit_system = swModel.GetUserPreferenceIntegerValue(3)  # swUnitsLinear
            
            print(f"Raw volume from API: {raw_volume}")
            print(f"Unit system: {unit_system}")
            
            # Convert to cubic millimeters
            if unit_system == 0:  # IPS (cubic inches)
                volume_mm3 = raw_volume * (25.4 ** 3)
                print(f"Converting from cubic inches: {raw_volume} in^3 = {volume_mm3} mm^3")
            elif unit_system == 1:  # CGS (cubic cm)
                volume_mm3 = raw_volume * (10 ** 3)
                print(f"Converting from cubic cm: {raw_volume} cm^3 = {volume_mm3} mm^3")
            elif unit_system == 2:  # MMGS (cubic mm)
                volume_mm3 = raw_volume
                print(f"Already in cubic mm: {volume_mm3} mm^3")
            elif unit_system == 3:  # MKS (cubic meters)
                volume_mm3 = raw_volume * (1000 ** 3)
                print(f"Converting from cubic meters: {raw_volume} m^3 = {volume_mm3} mm^3")
            else:
                volume_mm3 = raw_volume
                print(f"Unknown unit system, using raw value: {volume_mm3}")
            
            results["volume_mm3"] = volume_mm3
            print(f"FINAL VOLUME: {volume_mm3:.2f} mm^3")
        else:
            print("ERROR: Could not get mass properties")
            results["error"] = "Failed to calculate mass properties"
        
        # 5C. GD&T Data
        print("Extracting GD&T data...")
        gdt_data = get_gdt_data(swModel)
        results["gdt_data"] = gdt_data
        results["gdt_callouts"] = gdt_data["combined_signature"]
        
        print(f"GD&T Summary:")
        print(f"  - Feature Control Frames: {len(gdt_data['feature_control_frames'])}")
        print(f"  - DimXpert Annotations: {len(gdt_data['dimxpert_annotations'])}")
        print(f"  - Datums: {len(gdt_data['datums'])}")
        print(f"  - Total GD&T items: {len(gdt_data['combined_signature'])}")
        
        results["status"] = "Success"
        print("Analysis complete successfully!")
        
    except Exception as e:
        error_msg = str(e)
        results["error"] = error_msg
        print(f"ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        
    finally:
        if swModel:
            try:
                swApp.CloseDoc(swModel.GetTitle())
                print("Document closed")
            except:
                pass
        pythoncom.CoUninitialize()
    
    return results

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: sw_worker.py <input_file> <output_json>")
        sys.exit(1)
    
    result = analyze_part(sys.argv[1])
    
    with open(sys.argv[2], 'w') as f:
        json.dump(result, f, indent=4)
    
    print(f"\nResults written to {sys.argv[2]}")
    print(f"Status: {result['status']}")
    print(f"Volume: {result['volume_mm3']:.2f} mm^3")
