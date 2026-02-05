class RuleType:
    MUST = "Must"
    SHOULD_NOT = "ShouldNot"
    EXIST = "Exist"
    MUST_OR = "Must (OR)"
    MAYBE = "Maybe"

class Rule:
    def __init__(self, start_time, end_time, topic, target_value, rule_type, tolerance=0.0):
        self.start_time = float(start_time)
        self.end_time = float(end_time)
        self.topic = topic
        self.target_value = target_value
        self.rule_type = rule_type
        self.tolerance = float(tolerance)

    def to_dict(self):
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "topic": self.topic,
            "target_value": self.target_value,
            "rule_type": self.rule_type,
            "tolerance": self.tolerance
        }

    @staticmethod
    def from_dict(data):
        return Rule(
            data["start_time"],
            data["end_time"],
            data["topic"],
            data["target_value"],
            data["rule_type"],
            data.get("tolerance", 0.0)
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
        self.master_config_data = {"macros": [], "files": {}}
        self.macros = []

    def get_macros(self):
        return self.macros

    def add_macro(self, name, description, rules):
        macro = {
            "name": name,
            "description": description,
            "rules": [r.to_dict() if hasattr(r, 'to_dict') else r for r in rules]
        }
        self.macros.append(macro)
        # We need the current file stem to save correctly, 
        # but macros are global. We'll trigger a save.
        self._save_master_config()

    def _save_master_config(self):
        if not self.master_config_path:
            return
        import json
        try:
            full_data = {
                "macros": self.macros,
                "files": self.master_config_data.get("files", {})
            }
            with open(self.master_config_path, 'w', encoding='utf-8') as f:
                json.dump(full_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to auto-save master config: {e}")

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
            # Determine a reference topic to gauge data length and indices
            # For MUST_OR, rule.topic is a list
            ref_topic = rule.topic[0] if isinstance(rule.topic, list) else rule.topic
            topic_data = data_loader.get_data_for_topic(ref_topic)
            
            if len(topic_data) == 0:
                results.append({"rule_index": i, "status": "ERROR", "msg": f"Topic '{ref_topic}' not found"})
                continue

            fs = data_loader.time_step
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
            
            elif rule.rule_type == RuleType.MUST_OR:
                # topic and target_value are expected to be lists of equal length
                topics = rule.topic if isinstance(rule.topic, list) else [rule.topic]
                targets = rule.target_value if isinstance(rule.target_value, list) else [rule.target_value]
                
                # Prepare per-topic data and processed targets
                topic_eval_params = []
                for j in range(len(topics)):
                    t_name = topics[j]
                    t_val = targets[j] if j < len(targets) else targets[-1] # Fallback to last target if missing
                    
                    t_data = data_loader.get_data_for_topic(t_name)
                    if len(t_data) == 0:
                        topic_eval_params.append(None)
                        continue
                        
                    processed_t_val = t_val
                    try:
                        if t_data.dtype.kind in 'iuf':
                            processed_t_val = float(t_val)
                    except: pass
                    
                    topic_eval_params.append({
                        "data": t_data,
                        "target": processed_t_val
                    })
                
                mismatch_indices = []
                for frame_offset in range(len(slice_data)):
                    # At each frame, check if ANY (topic[i] == target[i])
                    frame_match = False
                    global_idx = frame_offset + start_idx
                    
                    for params in topic_eval_params:
                        if params:
                            t_data = params["data"]
                            if global_idx < len(t_data) and t_data[global_idx] == params["target"]:
                                frame_match = True
                                break
                    
                    if not frame_match:
                        mismatch_indices.append(global_idx)
                
                if mismatch_indices:
                    status = "FAIL"
                    fail_frames = mismatch_indices

            elif rule.rule_type == RuleType.MAYBE:
                # Same as MUST but allows deviations up to duration 'tolerance'
                # Find segments where val != target
                mismatch_indices = []
                
                # Identify continuous mismatch segments
                current_segment = []
                for idx, val in enumerate(slice_data):
                    if val != target:
                        current_segment.append(idx + start_idx)
                    else:
                        if current_segment:
                            # Check duration of this mismatch segment
                            duration = len(current_segment) * data_loader.time_step
                            if duration > rule.tolerance + 1e-6: # Add small epsilon
                                mismatch_indices.extend(current_segment)
                            current_segment = []
                
                # Check the last segment
                if current_segment:
                    duration = len(current_segment) * data_loader.time_step
                    if duration > rule.tolerance + 1e-6:
                        mismatch_indices.extend(current_segment)
                
                if mismatch_indices:
                    status = "FAIL"
                    fail_frames = mismatch_indices

            if rule.rule_type == RuleType.MUST_OR:
                topic_desc = " | ".join(rule.topic) if isinstance(rule.topic, list) else str(rule.topic)
                val_desc = " | ".join(map(str, rule.target_value)) if isinstance(rule.target_value, list) else str(rule.target_value)
                rule_desc = f"{rule.rule_type} {topic_desc} == {val_desc} ({rule.start_time:.1f}s-{rule.end_time:.1f}s)"
            elif rule.rule_type == RuleType.MAYBE:
                rule_desc = f"{rule.rule_type} {rule.topic} == {rule.target_value} ({rule.start_time:.1f}s-{rule.end_time:.1f}s, tol={rule.tolerance}s)"
            else:
                rule_desc = f"{rule.rule_type} {rule.topic} == {rule.target_value} ({rule.start_time:.1f}s-{rule.end_time:.1f}s)"

            results.append({
                "rule_index": i, 
                "status": status, 
                "fail_frames": fail_frames,
                "rule_desc": rule_desc
            })
            
        return results

    def load_master_config(self, path):
        """Loads the master JSON file containing all configurations."""
        import os
        import json
        if not os.path.exists(path):
            self.master_config_data = {"macros": [], "files": {}}
            self.macros = []
            self.master_config_path = path
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Migration/Structure Check
            if "files" in data and "macros" in data:
                self.master_config_data = data
                self.macros = data["macros"]
            else:
                # Old format migration
                self.master_config_data = {"macros": [], "files": data}
                self.macros = []
            
            self.master_config_path = path
        except Exception as e:
            raise Exception(f"Failed to load master config: {e}")

    def get_config_for_file(self, file_stem):
        """Retrieves config dict for a specific file stem from master data."""
        files_data = self.master_config_data.get("files", {})
        return files_data.get(file_stem, None)

    def update_master_config(self, file_stem):
        """Updates the master data with current rules/metadata for file_stem and saves to disk."""
        if not self.master_config_path:
            raise ValueError("Master config path is not set.")
            
        entry = {
            "metadata": self.metadata,
            "rules": [rule.to_dict() for rule in self.rules]
        }
        
        # Ensure 'files' exists in master_config_data
        if "files" not in self.master_config_data:
            self.master_config_data["files"] = {}
            
        self.master_config_data["files"][file_stem] = entry
        
        # Sync macros before saving
        self.master_config_data["macros"] = self.macros
        
        # Save to disk
        import json
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
