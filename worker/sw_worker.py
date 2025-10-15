# worker/sw_worker.py
import win32com.client, sys, json
import pythoncom

def get_gdt_data(swModel):
    """Iterates through annotations to extract GD&T Feature Control Frame data."""
    gdt_list = []
    try:
        swAnnManager = swModel.Extension.GetAnnotationManager()
        if not swAnnManager: return gdt_list
        swAnnViews = swAnnManager.GetAnnotationViews()
        if not swAnnViews: return gdt_list

        for view in swAnnViews:
            view.Activate()
            annotations = view.GetAnnotations()
            if annotations:
                for swAnn in annotations:
                    if swAnn.GetType() == 30: # 30 = swFcfAnnotation
                        full_text = swAnn.GetText(0).replace('\n', ' ').strip()
                        if full_text: gdt_list.append(full_text)
        return sorted(list(set(gdt_list)))
    except Exception:
        return []

def analyze_part(file_path):
    """
    Analyzes a part using a robust protocol to ensure accurate measurement.
    """
    pythoncom.CoInitialize()
    results = { "status": "Failed", "signature": [], "volume_mm3": 0.0, "gdt_callouts": [], "error": "" }
    swApp, swModel = None, None
    try:
        swApp = win32com.client.GetActiveObject("SldWorks.Application")
        
        # 1. WIPE THE SLATE
        swApp.CloseAllDocuments(True)
        
        # 2. OPEN THE TARGET DOCUMENT
        opened_doc = swApp.OpenDoc6(file_path, 1, 1, "", 0, 0)
        if not opened_doc: raise Exception(f"Failed to open document: {file_path}")

        # 3. EXPLICITLY GET THE ACTIVE DOCUMENT
        swModel = swApp.ActiveDoc
        if not swModel: raise Exception("Could not get a handle on the active document.")

        # 4. FORCE A FULL REBUILD (CRITICAL STEP)
        swModel.ForceRebuild3(True) # True = rebuild all features
        
        # --- ANALYSIS NOW PROCEEDS ON THE CORRECT, REBUILT MODEL ---

        # 5A. Feature Signature
        feature = swModel.FirstFeature()
        while feature:
            results["signature"].append({"name": feature.Name, "type": feature.GetTypeName2()})
            feature = feature.GetNextFeature()

        # 5B. Mass Properties
        mass_props = swModel.Extension.GetMassProperties(1, 0)
        if mass_props: 
            results["volume_mm3"] = mass_props[5] * (1000**3)
        
        # 5C. GD&T Data
        results["gdt_callouts"] = get_gdt_data(swModel)
        
        results["status"] = "Success"
        
    except Exception as e:
        results["error"] = str(e)
    finally:
        if swModel: swApp.CloseDoc(swModel.GetTitle())
        pythoncom.CoUninitialize()
        
    return results

if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(1)
    result = analyze_part(sys.argv[1])
    with open(sys.argv[2], 'w') as f: json.dump(result, f, indent=4)
