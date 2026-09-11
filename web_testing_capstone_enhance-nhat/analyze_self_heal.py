import os
import json
import matplotlib.pyplot as plt
import numpy as np

# Configuration
result_dict = "generated_testcase_action_forth_attempt"

# Data collection
count_tc_occurred_error = 0
count_tc_occurred_error_but_success = 0
total_testcases = 0
total_passed = 0
total_failed = 0
total_web_fail = 0
total_llm_fail = 0
bp_stats = {}  # Statistics per blueprint

for bp in os.listdir(result_dict):
    bp_path = os.path.join(result_dict, bp)
    if not os.path.isdir(bp_path):
        continue
    
    bp_stats[bp] = {
        'total': 0,
        'errors': 0,
        'healed': 0,
        'passed': 0,
        'failed': 0,
        'web_fail': 0,
        'llm_fail': 0
    }
    
    for us in os.listdir(bp_path):
        us_path = os.path.join(bp_path, us)
        with open(us_path, "r") as f:
            data = json.load(f)

        for testcase in data:
            total_testcases += 1
            bp_stats[bp]['total'] += 1
            
            flag_error = False
            if testcase["test_case_info"]["expected_outcome"] == "True":
                for step in testcase["execute_log"]:
                    if step["error"] is not None:
                        flag_error = True
                        break
                
                if flag_error:
                    count_tc_occurred_error += 1
                    bp_stats[bp]['errors'] += 1
                    
                    if not testcase["evaluation"]["llm_fail"] and testcase["evaluation"]["result"]:
                        count_tc_occurred_error_but_success += 1
                        bp_stats[bp]['healed'] += 1
                
                # Track pass/fail
                if testcase["evaluation"]["result"]:
                    total_passed += 1
                    bp_stats[bp]['passed'] += 1
                else:
                    total_failed += 1
                    bp_stats[bp]['failed'] += 1
                    if testcase["evaluation"]["web_fail"]:
                        total_web_fail += 1
                        bp_stats[bp]['web_fail'] += 1
                    if testcase["evaluation"]["llm_fail"]:
                        total_llm_fail += 1
                        bp_stats[bp]['llm_fail'] += 1

# Print statistics
print("="*60)
print("TEST CASE EXECUTION ANALYSIS")
print("="*60)
print(f"Total test cases analyzed: {total_testcases}")
print(f"Total passed: {total_passed} ({total_passed/total_testcases*100:.1f}%)")
print(f"Total failed: {total_failed} ({total_failed/total_testcases*100:.1f}%)")
print(f"  - Web failures: {total_web_fail} ({total_web_fail/total_testcases*100:.1f}%)")
print(f"  - LLM failures: {total_llm_fail} ({total_llm_fail/total_testcases*100:.1f}%)")
print(f"\nTest cases with errors: {count_tc_occurred_error}")
print(f"Test cases healed after errors: {count_tc_occurred_error_but_success}")
if count_tc_occurred_error > 0:
    healing_rate = count_tc_occurred_error_but_success / count_tc_occurred_error * 100
    print(f"Healing success rate: {healing_rate:.1f}%")
print("="*60)

# Create visualizations
fig = plt.figure(figsize=(16, 10))

# 1. Overall Error and Healing Statistics (Pie Chart)
ax1 = plt.subplot(2, 3, 1)
labels = ['No Errors', 'Errors (Healed)', 'Errors (Not Healed)']
sizes = [
    total_testcases - count_tc_occurred_error,
    count_tc_occurred_error_but_success,
    count_tc_occurred_error - count_tc_occurred_error_but_success
]
colors = ['#2ecc71', '#f39c12', '#e74c3c']
explode = (0, 0.1, 0.1)
ax1.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
        shadow=True, startangle=90)
ax1.set_title('Test Case Error Distribution', fontsize=12, fontweight='bold')

# 2. Pass/Fail Rate with Failure Breakdown (Stacked Bar Chart)
ax2 = plt.subplot(2, 3, 2)
categories = ['Total']
passed = [total_passed]
web_fail = [total_web_fail]
llm_fail = [total_llm_fail]
other_fail = [total_failed - total_web_fail - total_llm_fail]

x_pos = np.arange(len(categories))
width = 0.6

# Create stacked bars
p1 = ax2.bar(x_pos, passed, width, label='Passed', color='#2ecc71', alpha=0.8, edgecolor='black')
p2 = ax2.bar(x_pos, web_fail, width, bottom=passed, label='Web Fail', color='#e67e22', alpha=0.8, edgecolor='black')
p3 = ax2.bar(x_pos, llm_fail, width, bottom=[passed[i] + web_fail[i] for i in range(len(categories))], 
             label='LLM Fail', color='#e74c3c', alpha=0.8, edgecolor='black')
p4 = ax2.bar(x_pos, other_fail, width, 
             bottom=[passed[i] + web_fail[i] + llm_fail[i] for i in range(len(categories))], 
             label='Other Fail', color='#95a5a6', alpha=0.8, edgecolor='black')

ax2.set_ylabel('Number of Test Cases', fontsize=10)
ax2.set_title('Pass/Fail Breakdown', fontsize=12, fontweight='bold')
ax2.set_xticks(x_pos)
ax2.set_xticklabels(categories)
ax2.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=8)
ax2.grid(axis='y', alpha=0.3)

# Add percentage labels
total = total_testcases
for i, (pa, wf, lf, of) in enumerate(zip(passed, web_fail, llm_fail, other_fail)):
    if pa > 0:
        ax2.text(i, pa/2, f'{pa}\n{pa/total*100:.1f}%', ha='center', va='center', fontsize=8, fontweight='bold')
    if wf > 0:
        ax2.text(i, pa + wf/2, f'{wf}\n{wf/total*100:.1f}%', ha='center', va='center', fontsize=8)
    if lf > 0:
        ax2.text(i, pa + wf + lf/2, f'{lf}\n{lf/total*100:.1f}%', ha='center', va='center', fontsize=8)
    if of > 0:
        ax2.text(i, pa + wf + lf + of/2, f'{of}\n{of/total*100:.1f}%', ha='center', va='center', fontsize=8)

# 3. Healing Success Rate (Gauge-style Bar)
ax3 = plt.subplot(2, 3, 3)
if count_tc_occurred_error > 0:
    healing_rate = count_tc_occurred_error_but_success / count_tc_occurred_error * 100
else:
    healing_rate = 0
ax3.barh(['Healing Rate'], [healing_rate], color='#3498db', alpha=0.7, edgecolor='black')
ax3.barh(['Healing Rate'], [100 - healing_rate], left=[healing_rate], 
         color='#ecf0f1', alpha=0.5, edgecolor='black')
ax3.set_xlim(0, 100)
ax3.set_xlabel('Percentage (%)', fontsize=10)
ax3.set_title('Error Healing Success Rate', fontsize=12, fontweight='bold')
ax3.text(healing_rate/2, 0, f'{healing_rate:.1f}%', 
         ha='center', va='center', fontsize=12, fontweight='bold')
ax3.grid(axis='x', alpha=0.3)

# 4. Per-Blueprint Statistics (Stacked Bar with Failure Types)
ax4 = plt.subplot(2, 3, 4)
bp_names = list(bp_stats.keys())
bp_passed = [bp_stats[bp]['passed'] for bp in bp_names]
bp_web_fail = [bp_stats[bp]['web_fail'] for bp in bp_names]
bp_llm_fail = [bp_stats[bp]['llm_fail'] for bp in bp_names]
bp_other_fail = [bp_stats[bp]['failed'] - bp_stats[bp]['web_fail'] - bp_stats[bp]['llm_fail'] for bp in bp_names]

x_pos = np.arange(len(bp_names))
width = 0.6

p1 = ax4.bar(x_pos, bp_passed, width, label='Passed', color='#2ecc71', alpha=0.8)
p2 = ax4.bar(x_pos, bp_web_fail, width, bottom=bp_passed, label='Web Fail', color='#e67e22', alpha=0.8)
p3 = ax4.bar(x_pos, bp_llm_fail, width, 
             bottom=[bp_passed[i] + bp_web_fail[i] for i in range(len(bp_names))], 
             label='LLM Fail', color='#e74c3c', alpha=0.8)
p4 = ax4.bar(x_pos, bp_other_fail, width,
             bottom=[bp_passed[i] + bp_web_fail[i] + bp_llm_fail[i] for i in range(len(bp_names))],
             label='Other Fail', color='#95a5a6', alpha=0.8)

ax4.set_xticks(x_pos)
ax4.set_xticklabels(bp_names, rotation=45, ha='right', fontsize=8)
ax4.set_ylabel('Number of Test Cases', fontsize=10)
ax4.set_title('Pass/Fail Breakdown by Blueprint', fontsize=12, fontweight='bold')
ax4.legend(fontsize=8)
ax4.grid(axis='y', alpha=0.3)

# 5. Error and Healing Rates by Blueprint
ax5 = plt.subplot(2, 3, 5)
bp_error_rates = []
bp_healing_rates = []
for bp in bp_names:
    if bp_stats[bp]['total'] > 0:
        error_rate = bp_stats[bp]['errors'] / bp_stats[bp]['total'] * 100
        bp_error_rates.append(error_rate)
    else:
        bp_error_rates.append(0)
    
    if bp_stats[bp]['errors'] > 0:
        healing_rate = bp_stats[bp]['healed'] / bp_stats[bp]['errors'] * 100
        bp_healing_rates.append(healing_rate)
    else:
        bp_healing_rates.append(0)
healing_rate = count_tc_occurred_error_but_success / count_tc_occurred_error * 100
x_pos = np.arange(len(bp_names))
width = 0.35
ax5.bar(x_pos - width/2, bp_error_rates, width, label='Error Rate', 
        color='#e74c3c', alpha=0.7)
ax5.bar(x_pos + width/2, bp_healing_rates, width, label='Healing Rate', 
        color='#f39c12', alpha=0.7)
ax5.set_xticks(x_pos)
ax5.set_xticklabels(bp_names, rotation=45, ha='right', fontsize=8)
ax5.set_ylabel('Percentage (%)', fontsize=10)
ax5.set_title('Error & Healing Rates by Blueprint', fontsize=12, fontweight='bold')
ax5.legend()
ax5.grid(axis='y', alpha=0.3)

# 6. Summary Statistics Table
ax6 = plt.subplot(2, 3, 6)
ax6.axis('tight')
ax6.axis('off')
table_data = [
    ['Metric', 'Value'],
    ['Total Test Cases', f'{total_testcases}'],
    ['Total Passed', f'{total_passed} ({total_passed/total_testcases*100:.1f}%)'],
    ['Total Failed', f'{total_failed} ({total_failed/total_testcases*100:.1f}%)'],
    ['  └─ Web Failures', f'{total_web_fail} ({total_web_fail/total_testcases*100:.1f}%)'],
    ['  └─ LLM Failures', f'{total_llm_fail} ({total_llm_fail/total_testcases*100:.1f}%)'],
    ['Cases with Errors', f'{count_tc_occurred_error}'],
    ['Errors Healed', f'{count_tc_occurred_error_but_success}'],
    ['Healing Rate', f'{healing_rate:.1f}%' if count_tc_occurred_error > 0 else 'N/A'],
]
table = ax6.table(cellText=table_data, cellLoc='left', loc='center',
                  colWidths=[0.6, 0.4])
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 2)
# Style header row
for i in range(2):
    table[(0, i)].set_facecolor('#3498db')
    table[(0, i)].set_text_props(weight='bold', color='white')
# Alternate row colors
for i in range(1, len(table_data)):
    for j in range(2):
        if i % 2 == 0:
            table[(i, j)].set_facecolor('#ecf0f1')
ax6.set_title('Summary Statistics', fontsize=12, fontweight='bold', pad=20)

plt.suptitle('Test Case Execution Analysis Dashboard', 
             fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig('testcase_analysis.png', dpi=300, bbox_inches='tight')
print("\nVisualization saved as 'testcase_analysis.png'")
plt.show()