import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath("e:/LGE/excel_inspector"))

from core.data_loader import ExcelLoader
from core.logic import InspectorLogic, Rule, RuleType

def create_dummy_excel(filename):
    # Create a dataframe with 100 rows, 3 topics
    df = pd.DataFrame({
        "TopicA": np.linspace(0, 100, 100), # 0 to 100
        "TopicB": [10] * 100,               # Constant 10
        "TopicC": [0]*50 + [1]*50           # 0 then 1
    })
    df.to_excel(filename, index=False)
    print(f"Created {filename}")

def test_core_logic():
    excel_file = "dumm_test.xlsx"
    create_dummy_excel(excel_file)
    
    loader = ExcelLoader()
    loader.load_file(excel_file)
    print("Excel loaded.")
    
    # Check Time generation
    time_axis = loader.get_time_axis()
    assert len(time_axis) == 100, f"Expected 100 frames, got {len(time_axis)}"
    assert abs(time_axis[1] - 0.033) < 1e-5, "Time step incorrect"
    
    logic = InspectorLogic()
    
    # Rule 1: TopicA must be > -1 (Always pass) 
    # Logic only supports "==" for now explicitly in the code I wrote? 
    # Wait, my logic.py implementation:
    # if rule.rule_type == RuleType.MUST: mismatch_indices = ... if val != target
    # So it is strict Equality.
    
    # Let's test Equality.
    # TopicB is 10.
    r1 = Rule(0.0, 1.0, "TopicB", 10, RuleType.MUST)
    logic.add_rule(r1)
    
    # TopicC should not be 1 in first half
    r2 = Rule(0.0, 1.0, "TopicC", 1, RuleType.SHOULD_NOT) # 0.0 to 1.0s is roughly first 30 frames. Value is 0.
    logic.add_rule(r2)
    
    results = logic.check_rules(loader)
    
    for res in results:
        print(f"Rule {res['rule_index']}: {res['status']}")
        assert res['status'] == 'PASS', f"Rule {res['rule_index']} failed but should satisfy."

    # Test Failure
    # TopicB MUST be 20 (Fail)
    r3 = Rule(0.0, 1.0, "TopicB", 20, RuleType.MUST)
    logic.add_rule(r3)
    
    results = logic.check_rules(loader)
    assert results[2]['status'] == 'FAIL', "Rule 3 shoud fail"
    
    print("Logic verification passed.")
    
    # Clean up
    if os.path.exists(excel_file):
        os.remove(excel_file)

if __name__ == "__main__":
    test_core_logic()
