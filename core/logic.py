class RuleType:
    MUST = "Must"
    SHOULD_NOT = "ShouldNot"
    EXIST = "Exist"

class Rule:
    def __init__(self, start_time, end_time, topic, target_value, rule_type):
        self.start_time = float(start_time)
        self.end_time = float(end_time)
        self.topic = topic
        self.target_value = target_value
        self.rule_type = rule_type

    def to_dict(self):
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "topic": self.topic,
            "target_value": self.target_value,
            "rule_type": self.rule_type
        }

    @staticmethod
    def from_dict(data):
        return Rule(
            data["start_time"],
            data["end_time"],
            data["topic"],
            data["target_value"],
            data["rule_type"]
        )

class InspectorLogic:
    def __init__(self):
        self.rules = []
        self.metadata = {
            "vehicle": "",
            "sw_ver": "",
            "test_date": "",
            "categories": [],
            "tc_number": "",
            "note": ""
        }
        
        # Centralized Master Config
        self.master_config_path = None
        self.master_config_data = {} # { "filename_stem": { "metadata": {}, "rules": [] } }

    def add_rule(self, rule):
        self.rules.append(rule)

    def remove_rule(self, index):
        if 0 <= index < len(self.rules):
            self.rules.pop(index)

    def update_rule(self, index, **kwargs):
        if 0 <= index < len(self.rules):
            rule = self.rules[index]
            for key, value in kwargs.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)

    def get_rules(self):
        return self.rules

    def check_rules(self, data_loader):
        results = []
        time_axis = data_loader.get_time_axis()
        
        for i, rule in enumerate(self.rules):
            topic_data = data_loader.get_data_for_topic(rule.topic)
            if len(topic_data) == 0:
                results.append({"rule_index": i, "status": "ERROR", "msg": "Topic not found"})
                continue

            fs = 0.033
            start_idx = int(rule.start_time / fs)
            end_idx = int(rule.end_time / fs)
            
            start_idx = max(0, min(start_idx, len(time_axis)-1))
            end_idx = max(0, min(end_idx, len(time_axis)-1))
            
            # If start > end after clamping, might be empty range
            if start_idx > end_idx:
                 slice_data = [] # empty
            else:
                 slice_data = topic_data[start_idx : end_idx+1]
            
            fail_frames = []
            status = "PASS"
            
            target = rule.target_value
            try:
                if len(slice_data) > 0 and slice_data.dtype.kind in 'iuf': 
                    target = float(target)
            except:
                pass

            if rule.rule_type == RuleType.MUST:
                mismatch_indices = [idx + start_idx for idx, val in enumerate(slice_data) if val != target]
                if mismatch_indices:
                    status = "FAIL"
                    fail_frames = mismatch_indices
                    
            elif rule.rule_type == RuleType.SHOULD_NOT:
                match_indices = [idx + start_idx for idx, val in enumerate(slice_data) if val == target]
                if match_indices:
                    status = "FAIL"
                    fail_frames = match_indices

            elif rule.rule_type == RuleType.EXIST:
                # EXIST: At least one value must match target
                found = False
                for val in slice_data:
                    if val == target:
                        found = True
                        break
                
                if not found:
                    status = "FAIL"
                    # For exist, the whole range is a failure really, but we need to return something
                    fail_frames = [start_idx] # Just marking start as fail point
            
            results.append({
                "rule_index": i, 
                "status": status, 
                "fail_frames": fail_frames,
                "rule_desc": f"{rule.rule_type} {rule.topic} == {rule.target_value} ({rule.start_time:.1f}s-{rule.end_time:.1f}s)"
            })
            
        return results

    def load_master_config(self, path):
        """Loads the master JSON file containing all configurations."""
        import os
        import json
        if not os.path.exists(path):
            # If not exists, just init empty and set path
            self.master_config_data = {}
            self.master_config_path = path
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.master_config_data = json.load(f)
            self.master_config_path = path
        except Exception as e:
            raise Exception(f"Failed to load master config: {e}")

    def get_config_for_file(self, file_stem):
        """Retrieves config dict for a specific file stem from master data."""
        return self.master_config_data.get(file_stem, None)

    def update_master_config(self, file_stem):
        """Updates the master data with current rules/metadata for file_stem and saves to disk."""
        import os
        import json
        if not self.master_config_path:
            raise ValueError("Master config path is not set.")
            
        entry = {
            "metadata": self.metadata,
            "rules": [rule.to_dict() for rule in self.rules]
        }
        
        self.master_config_data[file_stem] = entry
        
        # Save to disk
        try:
            with open(self.master_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.master_config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Failed to save master config: {e}")

    def load_config_from_dict(self, data):
        """Loads rules and metadata from a dictionary entry."""
        if not data:
            return

        if isinstance(data, list):
            # Old Format Support (Just list of rules)
            self.rules = [Rule.from_dict(item) for item in data]
            # Reset metadata to defaults
            self.metadata = {
                "vehicle": "", "sw_ver": "", "test_date": "",
                "categories": [], "tc_number": "", "note": ""
            }
        elif isinstance(data, dict):
            # New Format
            self.metadata = data.get("metadata", {})
            # Ensure all keys exist (migration)
            defaults = {
                "vehicle": "", "sw_ver": "", "test_date": "",
                "categories": [], "tc_number": "", "note": ""
            }
            for k, v in defaults.items():
                if k not in self.metadata:
                    self.metadata[k] = v
                    
            rules_data = data.get("rules", [])
            self.rules = [Rule.from_dict(item) for item in rules_data]

    def load_rules_from_json(self, file_path):
        """Legacy: Load from single JSON file."""
        import os
        import json
        if not os.path.exists(file_path):
            return 
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.load_config_from_dict(data)

    def save_rules_to_json(self, file_path):
        """Legacy: Save to single JSON file."""
        import json
        data = {
            "metadata": self.metadata,
            "rules": [rule.to_dict() for rule in self.rules]
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
