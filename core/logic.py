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
            "tolerance": self.tolerance,
        }

    @staticmethod
    def from_dict(data):
        return Rule(
            data["start_time"],
            data["end_time"],
            data["topic"],
            data["target_value"],
            data["rule_type"],
            data.get("tolerance", 0.0),
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
            "note": "",
        }

        self.master_config_path = None
        self.master_config_data = {"macros": [], "files": {}}
        self.macros = []

    def get_macros(self):
        return self.macros

    def add_macro(self, name, description, rules):
        macro = {
            "name": name,
            "description": description,
            "rules": [r.to_dict() if hasattr(r, 'to_dict') else r for r in rules],
        }
        self.macros.append(macro)
        self._save_master_config()

    def _save_master_config(self):
        if not self.master_config_path:
            return

        import json

        full_data = {
            "macros": self.macros,
            "files": self.master_config_data.get("files", {}),
        }
        with open(self.master_config_path, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, indent=4, ensure_ascii=False)

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

    def _build_rule_desc(self, rule):
        if rule.rule_type == RuleType.MUST_OR:
            topic_desc = " | ".join(rule.topic) if isinstance(rule.topic, list) else str(rule.topic)
            val_desc = " | ".join(map(str, rule.target_value)) if isinstance(rule.target_value, list) else str(rule.target_value)
            return f"{rule.rule_type} {topic_desc} == {val_desc} ({rule.start_time:.1f}s-{rule.end_time:.1f}s)"

        if rule.rule_type == RuleType.MAYBE:
            return (
                f"{rule.rule_type} {rule.topic} == {rule.target_value} "
                f"({rule.start_time:.1f}s-{rule.end_time:.1f}s, tol={rule.tolerance}s)"
            )

        return f"{rule.rule_type} {rule.topic} == {rule.target_value} ({rule.start_time:.1f}s-{rule.end_time:.1f}s)"

    def check_rules(self, data_loader):
        results = []
        time_axis = data_loader.get_time_axis()

        if time_axis is None or len(time_axis) == 0:
            return results

        last_index = len(time_axis) - 1
        fs = data_loader.time_step

        for i, rule in enumerate(self.rules):
            rule_desc = self._build_rule_desc(rule)
            ref_topic = rule.topic[0] if isinstance(rule.topic, list) else rule.topic
            topic_data = data_loader.get_data_for_topic(ref_topic)

            if len(topic_data) == 0:
                results.append({
                    "rule_index": i,
                    "status": "ERROR",
                    "fail_frames": [],
                    "rule_desc": rule_desc,
                    "msg": f"Topic '{ref_topic}' not found",
                })
                continue

            raw_start_idx = int(rule.start_time / fs)
            raw_end_idx = int(rule.end_time / fs)

            if raw_end_idx < 0 or raw_start_idx > last_index:
                results.append({
                    "rule_index": i,
                    "status": "SKIP",
                    "fail_frames": [],
                    "rule_desc": rule_desc,
                    "msg": "No actual data exists in the selected time range.",
                })
                continue

            start_idx = max(0, raw_start_idx)
            end_idx = min(raw_end_idx, last_index)

            if start_idx > end_idx:
                results.append({
                    "rule_index": i,
                    "status": "SKIP",
                    "fail_frames": [],
                    "rule_desc": rule_desc,
                    "msg": "No actual data exists in the selected time range.",
                })
                continue

            slice_data = topic_data[start_idx:end_idx + 1]
            fail_frames = []
            status = "PASS"

            target = rule.target_value
            try:
                if len(slice_data) > 0 and slice_data.dtype.kind in 'iuf':
                    target = float(target)
            except Exception:
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
                found = any(val == target for val in slice_data)
                if not found:
                    status = "FAIL"
                    fail_frames = [start_idx]

            elif rule.rule_type == RuleType.MUST_OR:
                topics = rule.topic if isinstance(rule.topic, list) else [rule.topic]
                targets = rule.target_value if isinstance(rule.target_value, list) else [rule.target_value]

                topic_eval_params = []
                for j, t_name in enumerate(topics):
                    t_val = targets[j] if j < len(targets) else targets[-1]
                    t_data = data_loader.get_data_for_topic(t_name)

                    if len(t_data) == 0:
                        topic_eval_params.append(None)
                        continue

                    processed_t_val = t_val
                    try:
                        if t_data.dtype.kind in 'iuf':
                            processed_t_val = float(t_val)
                    except Exception:
                        pass

                    topic_eval_params.append({
                        "data": t_data,
                        "target": processed_t_val,
                    })

                mismatch_indices = []
                for frame_offset in range(len(slice_data)):
                    frame_match = False
                    global_idx = frame_offset + start_idx

                    for params in topic_eval_params:
                        if not params:
                            continue

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
                mismatch_indices = []
                current_segment = []

                for idx, val in enumerate(slice_data):
                    if val != target:
                        current_segment.append(idx + start_idx)
                    else:
                        if current_segment:
                            duration = len(current_segment) * data_loader.time_step
                            if duration > rule.tolerance + 1e-6:
                                mismatch_indices.extend(current_segment)
                            current_segment = []

                if current_segment:
                    duration = len(current_segment) * data_loader.time_step
                    if duration > rule.tolerance + 1e-6:
                        mismatch_indices.extend(current_segment)

                if mismatch_indices:
                    status = "FAIL"
                    fail_frames = mismatch_indices

            results.append({
                "rule_index": i,
                "status": status,
                "fail_frames": fail_frames,
                "rule_desc": rule_desc,
            })

        return results

    def load_master_config(self, path):
        """Load the master JSON file containing all configurations."""
        import json
        import os

        if not os.path.exists(path):
            self.master_config_data = {"macros": [], "files": {}}
            self.macros = []
            self.master_config_path = path
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if "files" in data and "macros" in data:
                self.master_config_data = data
                self.macros = data["macros"]
            else:
                self.master_config_data = {"macros": [], "files": data}
                self.macros = []

            self.master_config_path = path
        except Exception as e:
            raise Exception(f"Failed to load master config: {e}")

    def get_config_for_file(self, file_stem):
        """Retrieve config dict for a specific file stem from master data."""
        files_data = self.master_config_data.get("files", {})
        return files_data.get(file_stem, None)

    def update_master_config(self, file_stem):
        """Update the master data with current rules/metadata for file_stem and save to disk."""
        if not self.master_config_path:
            raise ValueError("Master config path is not set.")

        entry = {
            "metadata": self.metadata,
            "rules": [rule.to_dict() for rule in self.rules],
        }

        if "files" not in self.master_config_data:
            self.master_config_data["files"] = {}

        self.master_config_data["files"][file_stem] = entry
        self.master_config_data["macros"] = self.macros

        import json

        try:
            with open(self.master_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.master_config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Failed to save master config: {e}")

    def load_config_from_dict(self, data):
        """Load rules and metadata from a dictionary entry."""
        if not data:
            return

        import copy

        if isinstance(data, list):
            self.rules = [Rule.from_dict(item) for item in data]
            self.metadata = {
                "vehicle": "",
                "sw_ver": "",
                "test_date": "",
                "categories": [],
                "tc_number": "",
                "note": "",
            }
        elif isinstance(data, dict):
            self.metadata = copy.deepcopy(data.get("metadata", {}))
            defaults = {
                "vehicle": "",
                "sw_ver": "",
                "test_date": "",
                "categories": [],
                "tc_number": "",
                "note": "",
            }
            for k, v in defaults.items():
                if k not in self.metadata:
                    self.metadata[k] = v

            rules_data = data.get("rules", [])
            self.rules = [Rule.from_dict(item) for item in rules_data]

    def load_rules_from_json(self, file_path):
        """Legacy: load from single JSON file."""
        import json
        import os

        if not os.path.exists(file_path):
            return
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.load_config_from_dict(data)

    def save_rules_to_json(self, file_path):
        """Legacy: save to single JSON file."""
        import json

        data = {
            "metadata": self.metadata,
            "rules": [rule.to_dict() for rule in self.rules],
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
