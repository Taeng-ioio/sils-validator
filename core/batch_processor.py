import os
import glob
from core.data_loader import ExcelLoader
from core.logic import InspectorLogic

class BatchProcessor:
    def __init__(self):
        self.results = []

    def run_batch(self, folder_path, inspector_logic, progress_callback=None):
        """
        Scans folder for .xlsx/.xls/.csv files.
        Looks up config in the provided inspector_logic (Master Config).
        Runs validation.
        Returns list of results.
        
        progress_callback: function(current, total, filename)
        """
        self.results = []
        
        # Find all excel/csv files recursively
        data_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.xlsx', '.xls', '.csv')):
                    full_path = os.path.join(root, file)
                    data_files.append(full_path)
        
        total_files = len(data_files)
        
        for i, file_path in enumerate(data_files):
            # Use relative path 
            rel_path = os.path.relpath(file_path, folder_path)
            file_stem = os.path.splitext(os.path.basename(file_path))[0]
            
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
            
            # Lookup config in Master
            config_data = inspector_logic.get_config_for_file(file_stem)
            
            if not config_data:
                result_entry["status"] = "NO_CONFIG"
                result_entry["details"] = "Config not found in Master."
            else:
                try:
                    # Create a TEMPORARY logic instance for this check
                    # We can't use the main one because it holds state (rules, metadata) 
                    # that we don't want to mix, although we could reuse it if we are careful.
                    # Better to create a new instance and populate it from the dict.
                    temp_logic = InspectorLogic()
                    temp_logic.load_config_from_dict(config_data)
                    
                    # Extract Metadata
                    result_entry["vehicle"] = temp_logic.metadata.get("vehicle", "")
                    result_entry["sw_ver"] = temp_logic.metadata.get("sw_ver", "")
                    result_entry["test_date"] = temp_logic.metadata.get("test_date", "")
                    
                    cats = temp_logic.metadata.get("categories", [])
                    if isinstance(cats, list):
                        result_entry["categories"] = " | ".join(cats)
                    else:
                        result_entry["categories"] = str(cats)
                        
                    result_entry["tc_number"] = temp_logic.metadata.get("tc_number", "")
                    result_entry["note"] = temp_logic.metadata.get("note", "")
                    
                    # Load Data
                    loader = ExcelLoader()
                    loader.load_file(file_path)
                    
                    # Check Rules
                    check_results = temp_logic.check_rules(loader)
                    
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
