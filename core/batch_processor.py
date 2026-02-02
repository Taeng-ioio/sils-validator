import os
import glob
from core.data_loader import ExcelLoader
from core.logic import InspectorLogic

class BatchProcessor:
    def __init__(self):
        self.results = []

    def run_batch(self, folder_path, progress_callback=None):
        """
        Scans folder for .xlsx/.xls files.
        Looks for corresponding .json config.
        Runs validation.
        Returns list of results.
        
        progress_callback: function(current, total, filename)
        """
        self.results = []
        
        # Find all excel files recursively
        excel_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.xlsx', '.xls')):
                    full_path = os.path.join(root, file)
                    excel_files.append(full_path)
        
        total_files = len(excel_files)
        
        for i, excel_path in enumerate(excel_files):
            # Use relative path 
            rel_path = os.path.relpath(excel_path, folder_path)
            json_path = os.path.splitext(excel_path)[0] + ".json"
            
            result_entry = {
                "file": rel_path,
                "status": "UNKNOWN",
                "fail_count": 0,
                "details": "",
                "vehicle": "",
                "sw_ver": "",
                "test_date": "",
                "categories": "",
                "tc_number": "",
                "note": ""
            }
            
            if not os.path.exists(json_path):
                result_entry["status"] = "NO_CONFIG"
                result_entry["details"] = "Config file (.json) not found."
            else:
                try:
                    # Load Logic (Config)
                    logic = InspectorLogic()
                    logic.load_rules_from_json(json_path)
                    
                    # Extract Metadata
                    result_entry["vehicle"] = logic.metadata.get("vehicle", "")
                    result_entry["sw_ver"] = logic.metadata.get("sw_ver", "")
                    result_entry["test_date"] = logic.metadata.get("test_date", "")
                    
                    cats = logic.metadata.get("categories", [])
                    if isinstance(cats, list):
                        result_entry["categories"] = " | ".join(cats)
                    else:
                        result_entry["categories"] = str(cats)
                        
                    result_entry["tc_number"] = logic.metadata.get("tc_number", "")
                    result_entry["note"] = logic.metadata.get("note", "")
                    
                    # Load Data
                    loader = ExcelLoader()
                    loader.load_file(excel_path)
                    
                    # Check Rules
                    check_results = logic.check_rules(loader)
                    
                    fail_count = sum(1 for r in check_results if r['status'] == 'FAIL')
                    
                    result_entry["fail_count"] = fail_count
                    
                    if fail_count == 0:
                        result_entry["status"] = "PASS"
                        result_entry["details"] = "All rules passed."
                    else:
                        result_entry["status"] = "FAIL"
                        # Summarize failures
                        failed_rules = [r['rule_desc'] for r in check_results if r['status'] == 'FAIL']
                        result_entry["details"] = f"{fail_count} failures: " + ", ".join(failed_rules[:3])
                        if len(failed_rules) > 3:
                            result_entry["details"] += "..."
                            
                except Exception as e:
                    result_entry["status"] = "ERROR"
                    result_entry["details"] = str(e)
            
            self.results.append(result_entry)
            
            if progress_callback:
                progress_callback(i + 1, total_files, result_entry)
            
        return self.results
