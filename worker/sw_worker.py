# worker/sw_worker.py
import win32com.client
import sys
import json

def get_feature_count(swApp, file_path):
    doc_type = 1 if file_path.lower().endswith('.sldprt') else 2
    swModel = swApp.OpenDoc6(file_path, doc_type, 1, "", 0, 0)
    if not swModel:
        return -1
    count = swModel.FeatureManager.GetFeatureCount(False)
    swApp.CloseDoc(swModel.GetTitle())
    return count

def main(master_file_path, student_file_path, output_json_path):
    results = {
        "student_file": student_file_path.split('\\')[-1],
        "master_feature_count": -1,
        "student_feature_count": -1,
        "analysis_status": "Failed",
        "error_message": ""
    }
    try:
        swApp = win32com.client.Dispatch("SldWorks.Application")
        results["master_feature_count"] = get_feature_count(swApp, master_file_path)
        results["student_feature_count"] = get_feature_count(swApp, student_file_path)
        if results["student_feature_count"] == -1:
             raise Exception(f"Failed to open student file.")
        results["analysis_status"] = "Success"
    except Exception as e:
        results["error_message"] = str(e)
    finally:
        with open(output_json_path, 'w') as f:
            json.dump(results, f, indent=4)
        print(f"Results for {results['student_file']} saved to {output_json_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python sw_worker.py <master_file> <student_file> <output_json>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
