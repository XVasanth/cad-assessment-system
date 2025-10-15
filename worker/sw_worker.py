# worker/sw_worker.py
import win32com.client, sys, json

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
    """Analyzes a part for features, mass properties, and GD&T."""
    results = { "status": "Failed", "signature": [], "volume_mm3": 0.0, "gdt_callouts": [], "error": "" }
    swApp, swModel = None, None
    try:
        swApp = win32com.client.Dispatch("SldWorks.Application")

        # --- THE FIX: Ensure a clean slate before opening any new file ---
        swApp.CloseAllDocuments(True) # True = Close without asking to save
        
        swModel = swApp.OpenDoc6(file_path, 1, 1, "", 0, 0)
        if not swModel: raise Exception("Failed to open document.")

        # 1. Feature Signature
        feature = swModel.FirstFeature()
        while feature:
            results["signature"].append({"name": feature.Name, "type": feature.GetTypeName2()})
            feature = feature.GetNextFeature()

        # 2. Mass Properties
        mass_props = swModel.Extension.GetMassProperties(1, 0)
        if mass_props: results["volume_mm3"] = mass_props[5] * (1000**3)
        
        # 3. GD&T Data
        results["gdt_callouts"] = get_gdt_data(swModel)
        
        results["status"] = "Success"
        return results
    except Exception as e:
        results["error"] = str(e)
        return results
    finally:
        # The CloseAllDocuments call makes this redundant, but it's good practice
        if swModel: swApp.CloseDoc(swModel.GetTitle())

if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(1)
    result = analyze_part(sys.argv[1])
    with open(sys.argv[2], 'w') as f: json.dump(result, f, indent=4)
