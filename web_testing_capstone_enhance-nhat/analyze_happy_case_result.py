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

# Analyze statistics for POSITIVE TEST CASES ONLY (expected_outcome = "True")
def analyze_positive_tests(data):
    stats = {
        'overall': {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'valid_actions': 0,
            'invalid_actions': 0,
            'llm_fail': 0,
            'web_fail': 0,
            'both_fail': 0,
            'other_fail': 0
        },
        'by_business_process': defaultdict(lambda: {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'valid_actions': 0,
            'invalid_actions': 0,
            'llm_fail': 0,
            'web_fail': 0,
            'both_fail': 0
        }),
        'by_use_case': defaultdict(lambda: {
            'total': 0,
            'passed': 0,
            'failed': 0
        }),
        'test_details': []
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
                
                # FILTER: Only process positive test cases (expected_outcome = "True")
                if test_info.get('expected_outcome') != "True":
                    continue
                
                # Overall stats
                stats['overall']['total'] += 1
                stats['by_business_process'][business_process]['total'] += 1
                
                # By use case
                use_case = test_info.get('use_case_id', 'Unknown')
                stats['by_use_case'][use_case]['total'] += 1
                
                # Result (pass/fail)
                result = eval_data.get('result', False)
                if result:
                    stats['overall']['passed'] += 1
                    stats['by_business_process'][business_process]['passed'] += 1
                    stats['by_use_case'][use_case]['passed'] += 1
                else:
                    stats['overall']['failed'] += 1
                    stats['by_business_process'][business_process]['failed'] += 1
                    stats['by_use_case'][use_case]['failed'] += 1
                
                # Valid actions
                if eval_data.get('valid_action', False):
                    stats['overall']['valid_actions'] += 1
                    stats['by_business_process'][business_process]['valid_actions'] += 1
                else:
                    stats['overall']['invalid_actions'] += 1
                    stats['by_business_process'][business_process]['invalid_actions'] += 1
                
                # Failure types
                llm_fail = eval_data.get('llm_fail', False)
                web_fail = eval_data.get('web_fail', False)
                
                if llm_fail and web_fail:
                    stats['overall']['both_fail'] += 1
                    stats['by_business_process'][business_process]['both_fail'] += 1
                elif llm_fail:
                    stats['overall']['llm_fail'] += 1
                    stats['by_business_process'][business_process]['llm_fail'] += 1
                elif web_fail:
                    stats['overall']['web_fail'] += 1
                    stats['by_business_process'][business_process]['web_fail'] += 1
                elif not result:  # Failed but not llm or web
                    stats['overall']['other_fail'] += 1
                
                # Store test details
                stats['test_details'].append({
                    'business_process': business_process,
                    'test_case_id': test_info.get('test_case_id'),
                    'use_case_id': use_case,
                    'title': test_info.get('test_case_title'),
                    'result': result,
                    'valid_action': eval_data.get('valid_action', False),
                    'llm_fail': llm_fail,
                    'web_fail': web_fail,
                    'reasoning': eval_data.get('reasoning', '')
                })
    
    return stats

# Analyze the data
stats = analyze_positive_tests(bussiness_process_dict)

# Check if we have any data
if stats['overall']['total'] == 0:
    print("ERROR: No positive test cases (expected_outcome = 'True') found in the data!")
    print("Please check your folder structure and JSON files.")
    exit()

# Create visualizations
fig = plt.figure(figsize=(20, 14))
fig.suptitle('Positive Test Cases Analysis (Expected Outcome = True)', fontsize=22, fontweight='bold', y=0.995)

# 1. Overall Pass/Fail Rate (Pie Chart)
ax1 = plt.subplot(3, 4, 1)
labels = ['Passed', 'Failed']
sizes = [stats['overall']['passed'], stats['overall']['failed']]
colors = ['#10b981', '#ef4444']
explode = (0.05, 0)
ax1.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
        shadow=True, startangle=90)
ax1.set_title('Overall Pass/Fail Rate', fontsize=13, fontweight='bold')

# 2. Valid vs Invalid Actions (Pie Chart)
ax2 = plt.subplot(3, 4, 2)
labels = ['Valid Actions', 'Invalid Actions']
sizes = [stats['overall']['valid_actions'], stats['overall']['invalid_actions']]
colors = ['#3b82f6', '#f59e0b']
explode = (0.05, 0)
ax2.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
        shadow=True, startangle=90)
ax2.set_title('Action Validity', fontsize=13, fontweight='bold')

# 3. Failure Types Distribution (Pie Chart)
ax3 = plt.subplot(3, 4, 3)
labels = ['LLM Only', 'Web Only', 'Both', 'Other']
sizes = [stats['overall']['llm_fail'], stats['overall']['web_fail'], 
         stats['overall']['both_fail'], stats['overall']['other_fail']]
colors = ['#ef4444', '#f59e0b', '#8b5cf6', '#6b7280']
ax3.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
        shadow=True, startangle=90)
ax3.set_title('Failure Type Distribution', fontsize=13, fontweight='bold')

# 4. Summary Statistics Table
ax4 = plt.subplot(3, 4, 4)
ax4.axis('off')
summary_data = [
    ['Metric', 'Value'],
    ['Total Positive Tests', f"{stats['overall']['total']}"],
    ['Passed', f"{stats['overall']['passed']} ({stats['overall']['passed']/stats['overall']['total']*100:.1f}%)"],
    ['Failed', f"{stats['overall']['failed']} ({stats['overall']['failed']/stats['overall']['total']*100:.1f}%)"],
    ['Valid Actions', f"{stats['overall']['valid_actions']} ({stats['overall']['valid_actions']/stats['overall']['total']*100:.1f}%)"],
    ['LLM Failures', f"{stats['overall']['llm_fail']}"],
    ['Web Failures', f"{stats['overall']['web_fail']}"],
    ['Both Failures', f"{stats['overall']['both_fail']}"],
]
table = ax4.table(cellText=summary_data, cellLoc='left', loc='center',
                  colWidths=[0.55, 0.45])
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 1.8)
for i in range(2):
    table[(0, i)].set_facecolor('#3b82f6')
    table[(0, i)].set_text_props(weight='bold', color='white')
for i in range(1, len(summary_data)):
    for j in range(2):
        if i % 2 == 0:
            table[(i, j)].set_facecolor('#f0f0f0')
ax4.set_title('Summary Statistics', fontsize=13, fontweight='bold', pad=20)

# 5. Pass Rate by Business Process (Horizontal Bar)
ax5 = plt.subplot(3, 4, 5)
bp_names = list(stats['by_business_process'].keys())
pass_rates = [(stats['by_business_process'][bp]['passed'] / 
               stats['by_business_process'][bp]['total'] * 100) 
              for bp in bp_names]
colors_bar = ['#10b981' if rate >= 80 else '#f59e0b' if rate >= 50 else '#ef4444' 
              for rate in pass_rates]
bars = ax5.barh(bp_names, pass_rates, color=colors_bar)
ax5.set_xlabel('Pass Rate (%)', fontweight='bold')
ax5.set_title('Pass Rate by Business Process', fontsize=13, fontweight='bold')
ax5.set_xlim(0, 100)
for i, bar in enumerate(bars):
    width = bar.get_width()
    ax5.text(width + 2, bar.get_y() + bar.get_height()/2, 
             f'{pass_rates[i]:.1f}%', ha='left', va='center', fontweight='bold', fontsize=8)

# 6. Total Tests by Business Process (Bar Chart)
ax6 = plt.subplot(3, 4, 6)
test_counts = [stats['by_business_process'][bp]['total'] for bp in bp_names]
bars = ax6.bar(range(len(bp_names)), test_counts, color='#3b82f6')
ax6.set_xlabel('Business Process', fontweight='bold')
ax6.set_ylabel('Number of Tests', fontweight='bold')
ax6.set_title('Total Positive Tests per Process', fontsize=13, fontweight='bold')
ax6.set_xticks(range(len(bp_names)))
ax6.set_xticklabels([name[:12] + '...' if len(name) > 12 else name 
                      for name in bp_names], rotation=45, ha='right', fontsize=8)
for i, bar in enumerate(bars):
    height = bar.get_height()
    ax6.text(bar.get_x() + bar.get_width()/2, height + 0.5,
             f'{int(height)}', ha='center', va='bottom', fontweight='bold', fontsize=8)

# 7. Passed vs Failed by Business Process (Stacked Bar)
ax7 = plt.subplot(3, 4, 7)
passed = [stats['by_business_process'][bp]['passed'] for bp in bp_names]
failed = [stats['by_business_process'][bp]['failed'] for bp in bp_names]
x = np.arange(len(bp_names))
width = 0.6
p1 = ax7.bar(x, passed, width, label='Passed', color='#10b981')
p2 = ax7.bar(x, failed, width, bottom=passed, label='Failed', color='#ef4444')
ax7.set_ylabel('Number of Tests', fontweight='bold')
ax7.set_title('Passed vs Failed Tests', fontsize=13, fontweight='bold')
ax7.set_xticks(x)
ax7.set_xticklabels([name[:12] + '...' if len(name) > 12 else name 
                      for name in bp_names], rotation=45, ha='right', fontsize=8)
ax7.legend(fontsize=8)

# 8. LLM vs Web Failures Comparison
ax8 = plt.subplot(3, 4, 8)
llm_fails = [stats['by_business_process'][bp]['llm_fail'] for bp in bp_names]
web_fails = [stats['by_business_process'][bp]['web_fail'] for bp in bp_names]
both_fails = [stats['by_business_process'][bp]['both_fail'] for bp in bp_names]
x = np.arange(len(bp_names))
width = 0.25
p1 = ax8.bar(x - width, llm_fails, width, label='LLM Only', color='#ef4444')
p2 = ax8.bar(x, web_fails, width, label='Web Only', color='#f59e0b')
p3 = ax8.bar(x + width, both_fails, width, label='Both', color='#8b5cf6')
ax8.set_ylabel('Number of Failures', fontweight='bold')
ax8.set_title('Failure Types by Process', fontsize=13, fontweight='bold')
ax8.set_xticks(x)
ax8.set_xticklabels([name[:12] + '...' if len(name) > 12 else name 
                      for name in bp_names], rotation=45, ha='right', fontsize=8)
ax8.legend(fontsize=7)

# 9. Valid vs Invalid Actions by Business Process
ax9 = plt.subplot(3, 4, 9)
valid = [stats['by_business_process'][bp]['valid_actions'] for bp in bp_names]
invalid = [stats['by_business_process'][bp]['invalid_actions'] for bp in bp_names]
x = np.arange(len(bp_names))
width = 0.35
p1 = ax9.bar(x - width/2, valid, width, label='Valid', color='#3b82f6')
p2 = ax9.bar(x + width/2, invalid, width, label='Invalid', color='#f59e0b')
ax9.set_ylabel('Number of Actions', fontweight='bold')
ax9.set_title('Valid vs Invalid Actions', fontsize=13, fontweight='bold')
ax9.set_xticks(x)
ax9.set_xticklabels([name[:12] + '...' if len(name) > 12 else name 
                      for name in bp_names], rotation=45, ha='right', fontsize=8)
ax9.legend(fontsize=8)

# 10. Pass Rate by Use Case (Top 10)
ax10 = plt.subplot(3, 4, 10)
use_cases = sorted(stats['by_use_case'].items(), 
                   key=lambda x: x[1]['total'], reverse=True)[:10]
uc_names = [uc[0] for uc in use_cases]
uc_pass_rates = [(uc[1]['passed'] / uc[1]['total'] * 100) if uc[1]['total'] > 0 else 0 
                 for uc in use_cases]
colors_uc = ['#10b981' if rate >= 80 else '#f59e0b' if rate >= 50 else '#ef4444' 
             for rate in uc_pass_rates]
bars = ax10.barh(uc_names, uc_pass_rates, color=colors_uc)
ax10.set_xlabel('Pass Rate (%)', fontweight='bold')
ax10.set_title('Pass Rate by Use Case (Top 10)', fontsize=13, fontweight='bold')
ax10.set_xlim(0, 100)
for i, bar in enumerate(bars):
    width = bar.get_width()
    ax10.text(width + 2, bar.get_y() + bar.get_height()/2, 
              f'{uc_pass_rates[i]:.1f}%', ha='left', va='center', fontweight='bold', fontsize=7)

# 11. Tests Count by Use Case (Top 10)
ax11 = plt.subplot(3, 4, 11)
uc_counts = [uc[1]['total'] for uc in use_cases]
bars = ax11.bar(range(len(uc_names)), uc_counts, color='#3b82f6')
ax11.set_xlabel('Use Case', fontweight='bold')
ax11.set_ylabel('Number of Tests', fontweight='bold')
ax11.set_title('Test Count by Use Case (Top 10)', fontsize=13, fontweight='bold')
ax11.set_xticks(range(len(uc_names)))
ax11.set_xticklabels([name[:10] + '...' if len(name) > 10 else name 
                       for name in uc_names], rotation=45, ha='right', fontsize=7)
for i, bar in enumerate(bars):
    height = bar.get_height()
    ax11.text(bar.get_x() + bar.get_width()/2, height + 0.3,
              f'{int(height)}', ha='center', va='bottom', fontweight='bold', fontsize=8)

# 12. Failure Rate Analysis
ax12 = plt.subplot(3, 4, 12)
failure_categories = ['Valid Action\nPassed', 'Valid Action\nFailed', 
                      'Invalid Action\nPassed', 'Invalid Action\nFailed']
va_passed = sum(1 for t in stats['test_details'] if t['valid_action'] and t['result'])
va_failed = sum(1 for t in stats['test_details'] if t['valid_action'] and not t['result'])
ia_passed = sum(1 for t in stats['test_details'] if not t['valid_action'] and t['result'])
ia_failed = sum(1 for t in stats['test_details'] if not t['valid_action'] and not t['result'])
counts = [va_passed, va_failed, ia_passed, ia_failed]
colors_cat = ['#10b981', '#ef4444', '#60a5fa', '#fb923c']
bars = ax12.bar(failure_categories, counts, color=colors_cat)
ax12.set_ylabel('Number of Tests', fontweight='bold')
ax12.set_title('Action Validity vs Result', fontsize=13, fontweight='bold')
ax12.tick_params(axis='x', labelsize=8)
for i, bar in enumerate(bars):
    height = bar.get_height()
    ax12.text(bar.get_x() + bar.get_width()/2, height + 0.5,
              f'{int(height)}', ha='center', va='bottom', fontweight='bold', fontsize=9)

plt.tight_layout(rect=[0, 0.03, 1, 0.98])
plt.savefig('positive_tests_analysis.png', dpi=300, bbox_inches='tight')
plt.show()

# Print detailed statistics
print("\n" + "="*100)
print("POSITIVE TEST CASES ANALYSIS REPORT (Expected Outcome = True)")
print("="*100)
print(f"\nOverall Statistics:")
print(f"  Total Positive Tests: {stats['overall']['total']}")
if stats['overall']['total'] > 0:
    print(f"  Passed: {stats['overall']['passed']} ({stats['overall']['passed']/stats['overall']['total']*100:.1f}%)")
    print(f"  Failed: {stats['overall']['failed']} ({stats['overall']['failed']/stats['overall']['total']*100:.1f}%)")
    print(f"  Valid Actions: {stats['overall']['valid_actions']} ({stats['overall']['valid_actions']/stats['overall']['total']*100:.1f}%)")
    print(f"  Invalid Actions: {stats['overall']['invalid_actions']} ({stats['overall']['invalid_actions']/stats['overall']['total']*100:.1f}%)")
    print(f"  LLM Failures Only: {stats['overall']['llm_fail']}")
    print(f"  Web Failures Only: {stats['overall']['web_fail']}")
    print(f"  Both LLM & Web Failures: {stats['overall']['both_fail']}")
    print(f"  Other Failures: {stats['overall']['other_fail']}")

print(f"\n" + "-"*100)
print("Statistics by Business Process:")
print("-"*100)
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
    print(f"  Both Failures: {bp_stats['both_fail']}")

print(f"\n" + "-"*100)
print("Statistics by Use Case (Top 15):")
print("-"*100)
top_use_cases = sorted(stats['by_use_case'].items(), 
                       key=lambda x: x[1]['total'], reverse=True)[:15]
for uc_name, uc_stats in top_use_cases:
    print(f"\n{uc_name}:")
    print(f"  Total: {uc_stats['total']}")
    if uc_stats['total'] > 0:
        print(f"  Passed: {uc_stats['passed']} ({uc_stats['passed']/uc_stats['total']*100:.1f}%)")
        print(f"  Failed: {uc_stats['failed']} ({uc_stats['failed']/uc_stats['total']*100:.1f}%)")

print("\n" + "="*100)

# Export failed positive tests to CSV for further analysis
import csv
failed_tests = [t for t in stats['test_details'] if not t['result']]
if failed_tests:
    with open('failed_positive_tests.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['business_process', 'test_case_id', 'use_case_id', 
                                                'title', 'valid_action', 'llm_fail', 'web_fail', 'reasoning'])
        writer.writeheader()
        writer.writerows(failed_tests)
    print(f"\n✓ Exported {len(failed_tests)} failed positive test cases to 'failed_positive_tests.csv'")
    
print(f"✓ Analysis complete! Chart saved as 'positive_tests_analysis.png'")
print("="*100 + "\n")