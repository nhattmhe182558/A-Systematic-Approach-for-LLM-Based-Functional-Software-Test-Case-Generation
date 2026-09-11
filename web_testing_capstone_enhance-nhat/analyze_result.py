import os
import json
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

# Load test results
result_folder = "generated_testcase_action_forth_attempt"

# Check if folder exists
if not os.path.exists(result_folder):
    print(f"ERROR: Folder '{result_folder}' not found!")
    print(f"Current directory: {os.getcwd()}")
    exit()

bussiness_process_dict = {}
for business_process in os.listdir(result_folder):
    business_process_path = os.path.join(result_folder, business_process)
    
    # Skip if not a directory
    if not os.path.isdir(business_process_path):
        continue
    
    bussiness_process_dict[business_process] = {}
    
    for tc in os.listdir(business_process_path):
        # Skip non-JSON files
        if not tc.endswith('.json'):
            continue
            
        tc_path = os.path.join(business_process_path, tc)
        try:
            with open(tc_path, "r", encoding="utf-8") as f:
                bussiness_process_dict[business_process][tc] = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse {tc_path}: {e}")
            continue
        except Exception as e:
            print(f"Warning: Error reading {tc_path}: {e}")
            continue

# Analyze statistics
def analyze_test_results(data):
    stats = {
        'overall': {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'valid_actions': 0,
            'invalid_actions': 0,
            'llm_fail': 0,
            'web_fail': 0,
            'expected_true': 0,
            'expected_false': 0
        },
        'by_business_process': defaultdict(lambda: {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'valid_actions': 0,
            'invalid_actions': 0,
            'llm_fail': 0,
            'web_fail': 0
        })
    }
    
    for business_process, test_cases in data.items():
        for tc_id, tc_data in test_cases.items():
            # Check if tc_data is a list (array of test cases)
            if isinstance(tc_data, list):
                test_list = tc_data
            # Or if it has a 'test_cases' key with a list
            elif isinstance(tc_data, dict) and 'test_cases' in tc_data:
                test_list = tc_data['test_cases']
            else:
                continue
                
            for test in test_list:
                eval_data = test.get('evaluation', {})
                test_info = test.get('test_case_info', {})
                
                # Overall stats
                stats['overall']['total'] += 1
                stats['by_business_process'][business_process]['total'] += 1
                
                # Result (pass/fail)
                if eval_data.get('result', False):
                    stats['overall']['passed'] += 1
                    stats['by_business_process'][business_process]['passed'] += 1
                else:
                    stats['overall']['failed'] += 1
                    stats['by_business_process'][business_process]['failed'] += 1
                
                # Valid actions
                if eval_data.get('valid_action', False):
                    stats['overall']['valid_actions'] += 1
                    stats['by_business_process'][business_process]['valid_actions'] += 1
                else:
                    stats['overall']['invalid_actions'] += 1
                    stats['by_business_process'][business_process]['invalid_actions'] += 1
                
                # Failure types
                if eval_data.get('llm_fail', False):
                    stats['overall']['llm_fail'] += 1
                    stats['by_business_process'][business_process]['llm_fail'] += 1
                
                if eval_data.get('web_fail', False):
                    stats['overall']['web_fail'] += 1
                    stats['by_business_process'][business_process]['web_fail'] += 1
                
                # Expected outcome
                if test_info.get('expected_outcome') == "True":
                    stats['overall']['expected_true'] += 1
                else:
                    stats['overall']['expected_false'] += 1
    
    return stats

# Analyze the data
stats = analyze_test_results(bussiness_process_dict)

# Debug: Print structure
print("\n" + "="*80)
print("DEBUG: Data Structure")
print("="*80)
print(f"Number of business processes found: {len(bussiness_process_dict)}")
for bp_name, bp_data in list(bussiness_process_dict.items())[:2]:  # Show first 2
    print(f"\nBusiness Process: {bp_name}")
    print(f"  Number of test case files: {len(bp_data)}")
    for tc_name, tc_data in list(bp_data.items())[:1]:  # Show first file
        print(f"  Sample file: {tc_name}")
        print(f"  Data type: {type(tc_data)}")
        
        if isinstance(tc_data, list):
            print(f"  Format: Direct list of test cases")
            print(f"  Number of test cases: {len(tc_data)}")
            if len(tc_data) > 0:
                print(f"  Sample test case keys: {list(tc_data[0].keys())}")
        elif isinstance(tc_data, dict):
            print(f"  Format: Dictionary")
            print(f"  Keys in JSON: {list(tc_data.keys())}")
            if 'test_cases' in tc_data:
                print(f"  Number of test_cases: {len(tc_data['test_cases'])}")
            else:
                print(f"  WARNING: 'test_cases' key not found!")
print("="*80 + "\n")

# Check if we have any data
if stats['overall']['total'] == 0:
    print("ERROR: No test cases found in the data!")
    print("Please check your folder structure and JSON files.")
    print("\nPossible issues:")
    print("1. JSON files don't have 'test_cases' key")
    print("2. 'test_cases' array is empty")
    print("3. JSON structure is different than expected")
    exit()

# Create visualizations
fig = plt.figure(figsize=(20, 12))
fig.suptitle('Autonomous Agent Test Results Analysis', fontsize=20, fontweight='bold')

# 1. Overall Pass/Fail Rate (Pie Chart)
ax1 = plt.subplot(3, 3, 1)
labels = ['Passed', 'Failed']
sizes = [stats['overall']['passed'], stats['overall']['failed']]
colors = ['#10b981', '#ef4444']
explode = (0.05, 0)
ax1.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
        shadow=True, startangle=90)
ax1.set_title('Overall Test Results', fontsize=14, fontweight='bold')

# 2. Valid vs Invalid Actions (Pie Chart)
ax2 = plt.subplot(3, 3, 2)
labels = ['Valid Actions', 'Invalid Actions']
sizes = [stats['overall']['valid_actions'], stats['overall']['invalid_actions']]
colors = ['#3b82f6', '#f59e0b']
explode = (0.05, 0)
ax2.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
        shadow=True, startangle=90)
ax2.set_title('Action Validity', fontsize=14, fontweight='bold')

# 3. Failure Types Distribution (Pie Chart)
ax3 = plt.subplot(3, 3, 3)
labels = ['LLM Failures', 'Web Failures']
sizes = [stats['overall']['llm_fail'], stats['overall']['web_fail']]
colors = ['#ef4444', '#f59e0b', '#8b5cf6']
print(sizes)
ax3.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
        shadow=True, startangle=90)
ax3.set_title('Failure Type Distribution', fontsize=14, fontweight='bold')

# 4. Pass Rate by Business Process (Bar Chart)
ax4 = plt.subplot(3, 3, 4)
bp_names = list(stats['by_business_process'].keys())
pass_rates = [(stats['by_business_process'][bp]['passed'] / 
               stats['by_business_process'][bp]['total'] * 100) 
              for bp in bp_names]
colors_bar = ['#10b981' if rate >= 80 else '#f59e0b' if rate >= 50 else '#ef4444' 
              for rate in pass_rates]
bars = ax4.barh(bp_names, pass_rates, color=colors_bar)
ax4.set_xlabel('Pass Rate (%)', fontweight='bold')
ax4.set_title('Pass Rate by Business Process', fontsize=14, fontweight='bold')
ax4.set_xlim(0, 100)
for i, bar in enumerate(bars):
    width = bar.get_width()
    ax4.text(width + 2, bar.get_y() + bar.get_height()/2, 
             f'{pass_rates[i]:.1f}%', ha='left', va='center', fontweight='bold')

# 5. Total Tests by Business Process (Bar Chart)
ax5 = plt.subplot(3, 3, 5)
test_counts = [stats['by_business_process'][bp]['total'] for bp in bp_names]
bars = ax5.bar(range(len(bp_names)), test_counts, color='#3b82f6')
ax5.set_xlabel('Business Process', fontweight='bold')
ax5.set_ylabel('Number of Tests', fontweight='bold')
ax5.set_title('Total Tests per Business Process', fontsize=14, fontweight='bold')
ax5.set_xticks(range(len(bp_names)))
ax5.set_xticklabels([name[:15] + '...' if len(name) > 15 else name 
                      for name in bp_names], rotation=45, ha='right')
for i, bar in enumerate(bars):
    height = bar.get_height()
    ax5.text(bar.get_x() + bar.get_width()/2, height + 0.5,
             f'{int(height)}', ha='center', va='bottom', fontweight='bold')

# 6. Passed vs Failed by Business Process (Stacked Bar)
ax6 = plt.subplot(3, 3, 6)
passed = [stats['by_business_process'][bp]['passed'] for bp in bp_names]
failed = [stats['by_business_process'][bp]['failed'] for bp in bp_names]
x = np.arange(len(bp_names))
width = 0.6
p1 = ax6.bar(x, passed, width, label='Passed', color='#10b981')
p2 = ax6.bar(x, failed, width, bottom=passed, label='Failed', color='#ef4444')
ax6.set_ylabel('Number of Tests', fontweight='bold')
ax6.set_title('Passed vs Failed Tests', fontsize=14, fontweight='bold')
ax6.set_xticks(x)
ax6.set_xticklabels([name[:15] + '...' if len(name) > 15 else name 
                      for name in bp_names], rotation=45, ha='right')
ax6.legend()

# 7. LLM vs Web Failures Comparison
ax7 = plt.subplot(3, 3, 7)
llm_fails = [stats['by_business_process'][bp]['llm_fail'] for bp in bp_names]
web_fails = [stats['by_business_process'][bp]['web_fail'] for bp in bp_names]
x = np.arange(len(bp_names))
width = 0.35
p1 = ax7.bar(x - width/2, llm_fails, width, label='LLM Failures', color='#ef4444')
p2 = ax7.bar(x + width/2, web_fails, width, label='Web Failures', color='#f59e0b')
ax7.set_ylabel('Number of Failures', fontweight='bold')
ax7.set_title('LLM vs Web Failures', fontsize=14, fontweight='bold')
ax7.set_xticks(x)
ax7.set_xticklabels([name[:15] + '...' if len(name) > 15 else name 
                      for name in bp_names], rotation=45, ha='right')
ax7.legend()

# 8. Valid vs Invalid Actions by Business Process
ax8 = plt.subplot(3, 3, 8)
valid = [stats['by_business_process'][bp]['valid_actions'] for bp in bp_names]
invalid = [stats['by_business_process'][bp]['invalid_actions'] for bp in bp_names]
x = np.arange(len(bp_names))
width = 0.35
p1 = ax8.bar(x - width/2, valid, width, label='Valid Actions', color='#3b82f6')
p2 = ax8.bar(x + width/2, invalid, width, label='Invalid Actions', color='#f59e0b')
ax8.set_ylabel('Number of Actions', fontweight='bold')
ax8.set_title('Valid vs Invalid Actions', fontsize=14, fontweight='bold')
ax8.set_xticks(x)
ax8.set_xticklabels([name[:15] + '...' if len(name) > 15 else name 
                      for name in bp_names], rotation=45, ha='right')
ax8.legend()

# 9. Summary Statistics Table
ax9 = plt.subplot(3, 3, 9)
ax9.axis('off')
summary_data = [
    ['Metric', 'Value'],
    ['Total Tests', f"{stats['overall']['total']}"],
    ['Passed Tests', f"{stats['overall']['passed']} ({stats['overall']['passed']/stats['overall']['total']*100:.1f}%)"],
    ['Failed Tests', f"{stats['overall']['failed']} ({stats['overall']['failed']/stats['overall']['total']*100:.1f}%)"],
    ['Valid Actions', f"{stats['overall']['valid_actions']} ({stats['overall']['valid_actions']/stats['overall']['total']*100:.1f}%)"],
    ['Invalid Actions', f"{stats['overall']['invalid_actions']} ({stats['overall']['invalid_actions']/stats['overall']['total']*100:.1f}%)"],
    ['LLM Failures', f"{stats['overall']['llm_fail']}"],
    ['Web Failures', f"{stats['overall']['web_fail']}"],
]
table = ax9.table(cellText=summary_data, cellLoc='left', loc='center',
                  colWidths=[0.5, 0.5])
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2)
# Style header row
for i in range(2):
    table[(0, i)].set_facecolor('#3b82f6')
    table[(0, i)].set_text_props(weight='bold', color='white')
# Alternate row colors
for i in range(1, len(summary_data)):
    for j in range(2):
        if i % 2 == 0:
            table[(i, j)].set_facecolor('#f0f0f0')
ax9.set_title('Summary Statistics', fontsize=14, fontweight='bold', pad=20)

plt.tight_layout(rect=[0, 0.03, 1, 0.96])
plt.savefig('test_analysis_results.png', dpi=300, bbox_inches='tight')
plt.show()

# Print detailed statistics
print("\n" + "="*80)
print("DETAILED TEST ANALYSIS REPORT")
print("="*80)
print(f"\nOverall Statistics:")
print(f"  Total Tests: {stats['overall']['total']}")

if stats['overall']['total'] > 0:
    print(f"  Passed: {stats['overall']['passed']} ({stats['overall']['passed']/stats['overall']['total']*100:.1f}%)")
    print(f"  Failed: {stats['overall']['failed']} ({stats['overall']['failed']/stats['overall']['total']*100:.1f}%)")
    print(f"  Valid Actions: {stats['overall']['valid_actions']} ({stats['overall']['valid_actions']/stats['overall']['total']*100:.1f}%)")
    print(f"  Invalid Actions: {stats['overall']['invalid_actions']} ({stats['overall']['invalid_actions']/stats['overall']['total']*100:.1f}%)")
    print(f"  LLM Failures: {stats['overall']['llm_fail']}")
    print(f"  Web Failures: {stats['overall']['web_fail']}")

    print(f"\n" + "-"*80)
    print("Statistics by Business Process:")
    print("-"*80)
    for bp_name, bp_stats in stats['by_business_process'].items():
        print(f"\n{bp_name}:")
        print(f"  Total: {bp_stats['total']}")
        if bp_stats['total'] > 0:
            print(f"  Passed: {bp_stats['passed']} ({bp_stats['passed']/bp_stats['total']*100:.1f}%)")
            print(f"  Failed: {bp_stats['failed']} ({bp_stats['failed']/bp_stats['total']*100:.1f}%)")
        print(f"  Valid Actions: {bp_stats['valid_actions']}")
        print(f"  Invalid Actions: {bp_stats['invalid_actions']}")
        print(f"  LLM Failures: {bp_stats['llm_fail']}")
        print(f"  Web Failures: {bp_stats['web_fail']}")

print("\n" + "="*80)