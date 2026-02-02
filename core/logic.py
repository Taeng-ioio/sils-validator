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

    def save_rules_to_json(self, filepath):
        import json
        
        # New format: { "metadata": {...}, "rules": [...] }
        export_data = {
            "metadata": self.metadata,
            "rules": [r.to_dict() for r in self.rules]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=4)

    def load_rules_from_json(self, filepath):
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if new format or old list format
        if isinstance(data, list):
            # Old format: just a list of rules
            self.rules = [Rule.from_dict(item) for item in data]
            self.metadata = {
                "vehicle": "", "sw_ver": "", "test_date": "",
                "categories": [], "tc_number": "", "note": ""
            }
        elif isinstance(data, dict):
            # New format
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
