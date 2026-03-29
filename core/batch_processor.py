import os
from core.data_loader import ExcelLoader
from core.logic import InspectorLogic


class BatchProcessor:
    def __init__(self):
        self.results = []

    def _evaluate_file(self, file_path, inspector_logic, display_name):
        file_stem = os.path.splitext(os.path.basename(file_path))[0]

        result_entry = {
            "file": display_name,
            "status": "UNKNOWN",
            "fail_count": 0,
            "details": "",
            "vehicle": "",
            "sw_ver": "",
            "test_date": "",
            "categories": "",
            "tc_number": "",
            "note": "",
        }

        config_data = inspector_logic.get_config_for_file(file_stem)

        if not config_data:
            result_entry["status"] = "NO_CONFIG"
            result_entry["details"] = "Config not found in Master."
            return result_entry

        try:
            temp_logic = InspectorLogic()
            temp_logic.load_config_from_dict(config_data)

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

            loader = ExcelLoader()
            loader.load_file(file_path)

            check_results = temp_logic.check_rules(loader)
            fail_count = sum(1 for r in check_results if r["status"] == "FAIL")
            result_entry["fail_count"] = fail_count

            if fail_count == 0:
                result_entry["status"] = "PASS"
                result_entry["details"] = "All rules passed."
            else:
                result_entry["status"] = "FAIL"
                failed_rules = [r["rule_desc"] for r in check_results if r["status"] == "FAIL"]
                result_entry["details"] = f"{fail_count} failures: " + ", ".join(failed_rules[:3])
                if len(failed_rules) > 3:
                    result_entry["details"] += "..."
        except Exception as e:
            result_entry["status"] = "ERROR"
            result_entry["details"] = str(e)

        return result_entry

    def run_batch(self, folder_path, inspector_logic, progress_callback=None):
        self.results = []

        data_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith((".xlsx", ".xls", ".csv")):
                    full_path = os.path.join(root, file)
                    data_files.append(full_path)

        total_files = len(data_files)

        for i, file_path in enumerate(data_files):
            rel_path = os.path.relpath(file_path, folder_path)
            result_entry = self._evaluate_file(file_path, inspector_logic, rel_path)
            self.results.append(result_entry)

            if progress_callback:
                progress_callback(i + 1, total_files, result_entry)

        return self.results

    def run_batch_compare(self, folders, inspector_logic, progress_callback=None):
        by_folder = {}
        all_files = set()
        processed_count = 0
        total_files = 0

        scanned = []
        for folder in folders:
            folder_path = folder["path"]
            folder_name = folder["name"]
            file_map = {}
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith((".xlsx", ".xls", ".csv")):
                        full_path = os.path.join(root, file)
                        file_map[file] = full_path
                        all_files.add(file)
            scanned.append((folder_name, file_map))
            total_files += len(file_map)

        for folder_name, file_map in scanned:
            folder_results = {}
            for file_name, file_path in sorted(file_map.items()):
                result_entry = self._evaluate_file(file_path, inspector_logic, file_name)
                folder_results[file_name] = result_entry
                processed_count += 1
                if progress_callback:
                    progress_callback(processed_count, total_files, folder_name, result_entry)
            by_folder[folder_name] = folder_results

        return {
            "by_folder": by_folder,
            "files": sorted(all_files),
            "processed_count": processed_count,
        }
