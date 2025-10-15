# worker/sw_worker.py
import win32com.client, sys, json
import pythoncom # Import the low-level COM library

def get_gdt_data(swModel):
    # This function is unchanged
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
    # *** NEW: Initialize COM library for this specific process ***
    pythoncom.CoInitialize()
    
    results = { "status": "Failed", "signature": [], "volume_mm3": 0.0, "gdt_callouts": [], "error": "" }
    swApp, swModel = None, None
    try:
        # Use GetActiveObject which is sometimes more reliable for an already running instance
        swApp = win32com.client.GetActiveObject("SldWorks.Application")
        swApp.CloseAllDocuments(True)
        
        swModel = swApp.OpenDoc6(file_path, 1, 1, "", 0, 0)
        if not swModel: raise Exception(f"Failed to open document: {file_path}")

        # Analysis logic is unchanged
        feature = swModel.FirstFeature()
        while feature:
            results["signature"].append({"name": feature.Name, "type": feature.GetTypeName2()})
            feature = feature.GetNextFeature()

        mass_props = swModel.Extension.GetMassProperties(1, 0)
        if mass_props: results["volume_mm3"] = mass_props[5] * (1000**3)
        
        results["gdt_callouts"] = get_gdt_data(swModel)
        results["status"] = "Success"
        
    except Exception as e:
        results["error"] = str(e)
    finally:
        if swModel: swApp.CloseDoc(swModel.GetTitle())
        # *** NEW: Uninitialize COM library to release all resources ***
        pythoncom.CoUninitialize()
        
    return results

if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(1)
    result = analyze_part(sys.argv[1])
    with open(sys.argv[2], 'w') as f: json.dump(result, f, indent=4)
